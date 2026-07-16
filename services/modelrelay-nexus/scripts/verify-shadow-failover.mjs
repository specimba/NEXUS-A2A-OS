import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { once } from 'node:events'
import { mkdtemp, writeFile } from 'node:fs/promises'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'

async function listen(server) {
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  return server.address().port
}

async function closeServer(server) {
  if (!server.listening) return
  server.closeAllConnections?.()
  await new Promise(resolve => server.close(resolve))
}

async function reservePort() {
  const server = createServer()
  const port = await listen(server)
  await closeServer(server)
  return port
}

async function waitForRelay(baseUrl) {
  let lastError = null
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(baseUrl + '/v1/models', {
        signal: AbortSignal.timeout(250),
      })
      if (response.ok) return response.json()
      lastError = new Error('relay readiness returned HTTP ' + response.status)
    } catch (error) {
      lastError = error
    }
    await delay(20)
  }
  throw lastError || new Error('relay did not become ready')
}

async function main() {
  let firstCalls = 0
  let secondCalls = 0
  const first = createServer(request => {
    firstCalls += 1
    request.resume()
    // Intentionally send no headers. The relay must abort only this offer.
  })
  const second = createServer((request, response) => {
    secondCalls += 1
    if (secondCalls > 1) {
      response.writeHead(402, { 'content-type': 'application/json' })
      response.end(JSON.stringify({ error: { message: 'fixture-private-body' } }))
      return
    }
    request.resume()
    response.writeHead(200, { 'content-type': 'application/json' })
    response.end(JSON.stringify({
      id: 'shadow-completion',
      object: 'chat.completion',
      created: Math.floor(Date.now() / 1000),
      model: 'labs-leanstral-1-5-1',
      choices: [{
        index: 0,
        message: { role: 'assistant', content: 'shadow-ok' },
        finish_reason: 'stop',
      }],
      usage: {
        prompt_tokens: 1,
        completion_tokens: 1,
        total_tokens: 2,
      },
    }))
  })

  const firstPort = await listen(first)
  const secondPort = await listen(second)
  const relayPort = await reservePort()
  const root = await mkdtemp(join(tmpdir(), 'nexus-modelrelay-shadow-'))
  const configPath = join(root, 'config.json')
  const token = randomUUID().replaceAll('-', '')
  const firstKey = 'openai-compatible:shadow-first'
  const secondKey = 'openai-compatible:shadow-second'

  await writeFile(configPath, JSON.stringify({
    apiKeys: {
      [firstKey]: token,
      [secondKey]: token,
    },
    providers: {
      [firstKey]: {
        enabled: true,
        name: 'Shadow first-byte timeout',
        baseUrl: 'http://127.0.0.1:' + firstPort + '/v1',
        modelId: 'labs-leanstral-1-5',
        discoverModels: false,
      },
      [secondKey]: {
        enabled: true,
        name: 'Shadow healthy offer',
        baseUrl: 'http://127.0.0.1:' + secondPort + '/v1',
        modelId: 'labs-leanstral-1-5-1',
        discoverModels: false,
      },
    },
    bannedModels: [],
    autoPingEnabled: false,
    autoUpdate: { enabled: false, intervalHours: 24 },
    minSweScore: null,
    excludedProviders: [],
  }, null, 2), 'utf8')

  process.env.MODELRELAY_NEXUS_SAFE_RUNTIME = '1'
  process.env.MODELRELAY_DISABLE_AUTO_UPDATE = '1'
  process.env.MODELRELAY_BIND = '127.0.0.1'
  process.env.MODELRELAY_CONFIG_PATH = configPath
  process.env.MODELRELAY_HEALTH_SAMPLER_PATH = join(root, 'health-sampler.json')
  process.env.MODELRELAY_FIRST_BYTE_TIMEOUT_MS = '50'
  process.env.MODELRELAY_TOTAL_TIMEOUT_MS = '750'

  const [{ loadConfig }, { runServer }] = await Promise.all([
    import('modelrelay/lib/config.js'),
    import('modelrelay/lib/server.js'),
  ])
  await runServer(loadConfig(), relayPort, false, [])

  const relayBase = 'http://127.0.0.1:' + relayPort
  const catalogue = await waitForRelay(relayBase)
  const ids = new Set(catalogue.data.map(row => row.id))
  assert.equal(ids.has('labs-leanstral-1-5-1'), true)
  assert.equal(ids.has(firstKey + '/labs-leanstral-1-5'), true)
  assert.equal(ids.has(secondKey + '/labs-leanstral-1-5-1'), true)

  const started = performance.now()
  const response = await fetch(relayBase + '/v1/chat/completions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'leanstral',
      messages: [{ role: 'user', content: 'reply with shadow-ok' }],
      max_tokens: 1,
    }),
    signal: AbortSignal.timeout(2_000),
  })
  const elapsedMs = Math.round(performance.now() - started)
  const payload = await response.json()

  assert.equal(response.status, 200, JSON.stringify(payload))
  assert.equal(payload.choices?.[0]?.message?.content, 'shadow-ok')
  assert.equal(firstCalls, 1)
  assert.equal(secondCalls, 1)
  assert.equal(elapsedMs < 1_000, true)

  const failedResponse = await fetch(relayBase + '/v1/chat/completions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      // The locked provider-qualified route must not fan out to the first
      // offer when this selected offer returns an access failure.
      model: secondKey + '/labs-leanstral-1-5-1',
      messages: [{ role: 'user', content: 'exercise exact-offer failure receipt' }],
      max_tokens: 1,
    }),
    signal: AbortSignal.timeout(2_000),
  })
  const failedPayload = await failedResponse.json()
  const failedSerialized = JSON.stringify(failedPayload)
  assert.equal(failedResponse.status, 402)
  assert.equal(failedPayload.error?.code, 'NEXUS_PROVIDER_PAYMENT_REQUIRED')
  assert.equal(failedPayload.error?.attempts?.length, 1)
  const receiptByProvider = Object.fromEntries(
    failedPayload.error.attempts.map(attempt => [attempt.provider, attempt]),
  )
  assert.deepEqual(
    new Set(Object.keys(receiptByProvider)),
    new Set([secondKey]),
  )
  assert.equal(receiptByProvider[secondKey].error_code, 'UPSTREAM_HTTP_402')
  assert.doesNotMatch(failedSerialized, /fixture-private-body/)
  assert.equal(firstCalls, 1)
  assert.equal(secondCalls, 2)

  // A payment-required result is an access fact, not an outage. It remains
  // visible in health data and the held exact route is skipped on the next
  // request instead of burning another upstream call.
  const healthResponse = await fetch(relayBase + '/api/models')
  assert.equal(healthResponse.status, 200)
  const health = await healthResponse.json()
  const paymentOffer = health.models.find(model => (
    model.providerKey === secondKey && model.modelId === 'labs-leanstral-1-5-1'
  ))
  assert.equal(paymentOffer?.status, 'payment_required')
  assert.equal(paymentOffer?.accessClass, 'payment_required')
  assert.equal(Number(paymentOffer?.accessUntil) > Date.now(), true)

  const heldResponse = await fetch(relayBase + '/v1/chat/completions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: secondKey + '/labs-leanstral-1-5-1',
      messages: [{ role: 'user', content: 'prove held exact route is not retried' }],
      max_tokens: 1,
    }),
    signal: AbortSignal.timeout(2_000),
  })
  const heldPayload = await heldResponse.json()
  assert.equal(heldResponse.status, 503)
  assert.equal(heldPayload.error?.code, 'NEXUS_NO_ELIGIBLE_PROVIDER_OFFER')
  assert.equal(heldPayload.error?.attempts?.length, 0)
  assert.equal(firstCalls, 1)
  assert.equal(secondCalls, 2)

  await closeServer(first)
  await closeServer(second)
  process.stdout.write(JSON.stringify({
    status: 'SHADOW_FAILOVER_OK',
    relayPort,
    firstCalls,
    secondCalls,
    elapsedMs,
    failureStatus: failedResponse.status,
    failureReceiptCount: failedPayload.error.attempts.length,
  }) + '\n')
}

main()
  .then(() => process.exit(0))
  .catch(error => {
    process.stderr.write('SHADOW_FAILOVER_FAILED: ' + error.message + '\n')
    process.exit(1)
  })
