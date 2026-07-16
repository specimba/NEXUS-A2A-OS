import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  BoundedCanarySampler,
  CatalogueScheduler,
  ProviderAttemptBudget,
  ProviderAttemptBudgetError,
  ProviderGovernor,
  ProviderOfferAccessBlockedError,
  ProviderOfferCircuitOpenError,
  ProviderCircuitOpenError,
  ProviderRateLimitError,
  classifyOfferAccessFailure,
  classifyRateLimitScope,
  computeOfferFirstByteDeadlineMs,
  parseRetryAfterMs,
  runGovernedAttempts,
  selectNexusResilientOffers,
} from '../src/nexus-runtime-policy.js'

const response = (status, headers = {}) => new Response(
  JSON.stringify({ status }),
  { status, headers: { 'content-type': 'application/json', ...headers } },
)

test('first-byte deadline adapts to exact health evidence inside the route budget', () => {
  const options = { configuredMs: 45_000, remainingMs: 25_000 }
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'mistral', status: 'up', pings: [{ code: '200', ms: 1_200 }],
  }, options), 6_000)
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'nvidia', status: 'up', pings: [{ code: '200', ms: 1_200 }],
  }, options), 12_000)
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'nvidia', status: 'pending', pings: [],
  }, options), 18_000)
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'nvidia', status: 'timeout', pings: [{ code: '000', ms: 18_000 }],
  }, options), 12_000)
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'nvidia', status: 'up', pings: [{ code: '200', ms: 1_200 }],
  }, { ...options, estimatedPromptTokens: 105_000 }), 25_000)
  assert.equal(computeOfferFirstByteDeadlineMs({
    providerKey: 'nvidia', status: 'up', pings: [{ code: '200', ms: 20_000 }],
  }, { configuredMs: 45_000, remainingMs: 7_000 }), 7_000)
})

test('startup and scheduled refresh are catalogue-only and never fan out chat probes', async () => {
  const calls = []
  const scheduler = new CatalogueScheduler({
    providers: ['mistral', 'nvidia'],
    listModels: async provider => calls.push(['GET_MODELS', provider]),
    probeChat: async provider => calls.push(['CHAT', provider]),
  })

  await scheduler.initialize()
  await scheduler.refresh()

  assert.deepEqual(calls, [
    ['GET_MODELS', 'mistral'],
    ['GET_MODELS', 'nvidia'],
    ['GET_MODELS', 'mistral'],
    ['GET_MODELS', 'nvidia'],
  ])
  assert.equal(calls.filter(([kind]) => kind === 'CHAT').length, 0)
})

test('explicit canary is one provider-scoped operation, never a model fanout', async () => {
  const calls = []
  const scheduler = new CatalogueScheduler({
    providers: ['mistral'],
    listModels: async () => {},
    probeChat: async (provider, model) => calls.push([provider, model]),
  })

  await scheduler.canary('mistral', 'labs-leanstral-1-5')
  assert.deepEqual(calls, [['mistral', 'labs-leanstral-1-5']])
})

test('nexus-resilient ranks recent observed fallbacks and preserves the GLM-5.2 primary lock', () => {
  const now = 2_250_000_000_000
  const governor = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
  const rateLimited = {
    providerKey: 'nvidia',
    modelId: 'minimaxai/minimax-m3',
    status: 'up',
    lastModelResponseAt: now - 20,
    pings: [{ code: '200', ms: 350, ts: now - 20 }],
  }
  const accessBlocked = {
    providerKey: 'openrouter',
    modelId: 'healthy-but-held',
    status: 'up',
    lastModelResponseAt: now - 30,
    pings: [{ code: '200', ms: 250, ts: now - 30 }],
  }
  governor.openRateLimit(rateLimited, { scope: 'offer', retryAfterMs: 90_000 })
  governor.recordOfferStatus(accessBlocked, 403)

  const offers = [
    // The normal locked primary has the freshest health evidence, but never
    // enters the opt-in fallback alias.
    {
      providerKey: 'nvidia',
      modelId: 'z-ai/glm-5.2',
      status: 'up',
      lastModelResponseAt: now - 1,
      pings: [{ code: '200', ms: 120, ts: now - 1 }],
    },
    {
      providerKey: 'openai-compatible:ollama-cloud',
      modelId: 'minimax-m3',
      status: 'up',
      lastModelResponseAt: now - 100,
      pings: [{ code: '200', ms: 600, ts: now - 100 }],
    },
    // This second offer is fresher than Mistral but is put behind a distinct
    // provider so the bounded second attempt has a genuine failover path.
    {
      providerKey: 'openai-compatible:ollama-cloud',
      modelId: 'deepseek-v4-flash',
      status: 'up',
      lastModelResponseAt: now - 150,
      pings: [{ code: '200', ms: 200, ts: now - 150 }],
    },
    {
      providerKey: 'openai-compatible:mistral',
      modelId: 'labs-leanstral-1-5-1',
      status: 'up',
      lastModelResponseAt: now - 200,
      pings: [{ code: '200', ms: 900, ts: now - 200 }],
    },
    rateLimited,
    accessBlocked,
    {
      providerKey: 'nvidia',
      modelId: 'retired-410',
      status: 'up',
      httpCode: '410',
      lastModelResponseAt: now - 10,
      pings: [{ code: '200', ms: 90, ts: now - 10 }],
    },
    {
      providerKey: 'opencode',
      modelId: 'stale-healthy',
      status: 'up',
      lastModelResponseAt: now - (48 * 60 * 60 * 1000) - 1,
      pings: [{ code: '200', ms: 100, ts: now - (48 * 60 * 60 * 1000) - 1 }],
    },
    {
      providerKey: 'kilocode',
      modelId: 'catalogue-only',
      status: 'pending',
      pings: [],
    },
  ]

  assert.deepEqual(
    selectNexusResilientOffers(offers, { governor, now }).map(offer => `${offer.providerKey}/${offer.modelId}`),
    [
      'openai-compatible:ollama-cloud/minimax-m3',
      'openai-compatible:mistral/labs-leanstral-1-5-1',
      'openai-compatible:ollama-cloud/deepseek-v4-flash',
    ],
  )
})

test('nexus-resilient fails closed when evidence is beyond its warm window or the live governor is absent', () => {
  const now = 2_251_000_000_000
  const governor = new ProviderGovernor({ now: () => now })
  const staleOnly = [{
    providerKey: 'openai-compatible:mistral',
    modelId: 'labs-leanstral-1-5-1',
    status: 'up',
    lastModelResponseAt: now - (48 * 60 * 60 * 1000) - 1,
    pings: [{ code: '200', ms: 800, ts: now - (48 * 60 * 60 * 1000) - 1 }],
  }]

  assert.deepEqual(selectNexusResilientOffers(staleOnly, { governor, now }), [])
  assert.deepEqual(selectNexusResilientOffers([{
    providerKey: 'openai-compatible:mistral',
    modelId: 'labs-leanstral-1-5-1',
    status: 'up',
    lastModelResponseAt: now,
    pings: [{ code: '200', ms: 800, ts: now }],
  }], { now }), [])
})

test('nexus-resilient uses bounded warm evidence and refuses an undersized route for a long Hermes context', () => {
  const now = 2_251_500_000_000
  const governor = new ProviderGovernor({ now: () => now })
  const freshSmall = {
    providerKey: 'codestral',
    modelId: 'codestral-latest',
    status: 'up',
    ctx: '32k',
    lastModelResponseAt: now - 500,
    pings: [{ code: '200', ms: 450, ts: now - 500 }],
  }
  const warmLarge = {
    providerKey: 'opencode',
    modelId: 'nemotron-3-ultra-free',
    status: 'up',
    ctx: '1M',
    lastModelResponseAt: now - (3 * 60 * 60 * 1000),
    pings: [{ code: '200', ms: 1_900, ts: now - (3 * 60 * 60 * 1000) }],
  }
  const warmTooSmall = {
    providerKey: 'openrouter',
    modelId: 'small-context-free',
    status: 'up',
    ctx: '64k',
    lastModelResponseAt: now - (2 * 60 * 60 * 1000),
    pings: [{ code: '200', ms: 900, ts: now - (2 * 60 * 60 * 1000) }],
  }

  assert.deepEqual(
    selectNexusResilientOffers([freshSmall, warmLarge, warmTooSmall], {
      governor,
      now,
      estimatedPromptTokens: 105_000,
    }).map(offer => `${offer.providerKey}/${offer.modelId}`),
    ['opencode/nemotron-3-ultra-free'],
  )
})

test('nexus-resilient uses router quality only after fresh health admits an offer', () => {
  const now = 2_251_750_000_000
  const governor = new ProviderGovernor({ now: () => now })
  const offers = [
    {
      providerKey: 'openai-compatible:mistral',
      modelId: 'fresh-code-endpoint',
      status: 'up',
      intell: null,
      lastModelResponseAt: now - 10,
      pings: [{ code: '200', ms: 250, ts: now - 10 }],
    },
    {
      providerKey: 'opencode',
      modelId: 'fresh-frontier-route',
      status: 'up',
      intell: 0.79,
      lastModelResponseAt: now - 1_000,
      pings: [{ code: '200', ms: 1_200, ts: now - 1_000 }],
    },
  ]

  assert.deepEqual(
    selectNexusResilientOffers(offers, { governor, now }).map(offer => `${offer.providerKey}/${offer.modelId}`),
    ['opencode/fresh-frontier-route', 'openai-compatible:mistral/fresh-code-endpoint'],
  )
})

test('nexus-resilient uses the latest exact observation instead of an older failed ping', () => {
  const now = 2_252_000_000_000
  const governor = new ProviderGovernor({ now: () => now })
  const recovered = {
    providerKey: 'opencode',
    modelId: 'recovered-route',
    status: 'up',
    lastModelResponseAt: now - 50,
    pings: [{ code: '429', ms: 100, ts: now - 100 }],
    httpCode: null,
    lastError: null,
  }
  const recentlyFailed = {
    providerKey: 'kilocode',
    modelId: 'newer-failure',
    status: 'up',
    lastModelResponseAt: now - 100,
    pings: [{ code: '429', ms: 100, ts: now - 50 }],
    httpCode: null,
    lastError: null,
  }

  assert.deepEqual(
    selectNexusResilientOffers([recovered, recentlyFailed], { governor, now }),
    [recovered],
  )
})

test('bounded canary sampler spaces probes, rotates providers, and prioritizes frontier candidates', () => {
  let now = 1_800_000_000_000
  const sampler = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })
  const offers = [
    { providerKey: 'nvidia', modelId: 'glm-5.2', intell: 0.95, status: 'pending' },
    { providerKey: 'nvidia', modelId: 'minimax-m3', intell: 0.90, status: 'pending' },
    { providerKey: 'mistral', modelId: 'leanstral', intell: 0.80, status: 'pending' },
  ]

  assert.equal(sampler.claim(offers)?.modelId, 'glm-5.2')
  assert.equal(sampler.claim(offers), null)
  now += 60_000
  assert.equal(sampler.claim(offers)?.providerKey, 'mistral')
  assert.equal(sampler.cooldownFor('nvidia'), 60 * 60 * 1000)
})

test('bounded canary sampler refreshes aging proven fallbacks without starving discovery or the 24/hour budget', () => {
  let now = 1_850_000_000_000
  const sampler = new BoundedCanarySampler({
    now: () => now,
    globalLimit: 24,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })
  const deepseek = {
    providerKey: 'opencode',
    modelId: 'deepseek-v4-flash-free',
    intell: 0.79,
    status: 'up',
    lastModelResponseAt: now - (20 * 60 * 1000),
    pings: [{ code: '200', ms: 900, ts: now - (20 * 60 * 1000) }],
  }
  const hy3 = {
    providerKey: 'kilocode',
    modelId: 'hy3-free',
    intell: 0.78,
    status: 'up',
    lastModelResponseAt: now - (18 * 60 * 1000),
    pings: [{ code: '200', ms: 950, ts: now - (18 * 60 * 1000) }],
  }
  const unverifiedDiscovery = {
    providerKey: 'openrouter',
    modelId: 'newly-discovered-route',
    intell: 0.99,
    status: 'pending',
  }
  const lockedPrimary = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    intell: 0.99,
    status: 'up',
    lastModelResponseAt: now - (20 * 60 * 1000),
    pings: [{ code: '200', ms: 900, ts: now - (20 * 60 * 1000) }],
  }
  const offers = [deepseek, hy3, unverifiedDiscovery, lockedPrimary]

  // The exact 2xx fallback is due for a refresh, so it beats catalogue-only
  // discovery. GLM-5.2 remains outside this fallback-refresh lane.
  assert.equal(sampler.claim(offers, { source: 'scheduled' })?.modelId, 'deepseek-v4-flash-free')
  assert.equal(sampler.snapshot().resilientRefreshSelectionsInWindow, 1)

  // A successful canary makes DeepSeek fresh again. The next bounded slot is
  // deliberately reserved for normal provider discovery rather than a second
  // resilient refresh.
  deepseek.lastModelResponseAt = now
  deepseek.pings.push({ code: '200', ms: 850, ts: now })
  now += 60_000
  assert.equal(sampler.claim(offers, { source: 'scheduled' })?.modelId, 'newly-discovered-route')

  // The following slot may refresh the next known-good fallback. No extra
  // calls were added: three reservations still leave 21 of the 24 slots.
  now += 60_000
  assert.equal(sampler.claim(offers, { source: 'scheduled' })?.modelId, 'hy3-free')
  assert.equal(sampler.snapshot().resilientRefreshSelectionsInWindow, 2)
  assert.equal(sampler.snapshot().remainingInWindow, 21)
})

test('resilient refresh priority never bypasses the existing provider cooldown', () => {
  const now = 1_860_000_000_000
  const sampler = new BoundedCanarySampler({
    now: () => now,
    globalLimit: 24,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 5 * 60 * 1000,
    state: { providerLastAt: { opencode: now - 1 } },
  })
  const dueFallback = {
    providerKey: 'opencode',
    modelId: 'deepseek-v4-flash-free',
    intell: 0.79,
    status: 'up',
    lastModelResponseAt: now - (20 * 60 * 1000),
    pings: [{ code: '200', ms: 900, ts: now - (20 * 60 * 1000) }],
  }
  const routineDiscovery = {
    providerKey: 'openrouter',
    modelId: 'newly-discovered-route',
    status: 'pending',
  }

  assert.equal(
    sampler.claim([dueFallback, routineDiscovery], { source: 'scheduled' })?.modelId,
    'newly-discovered-route',
  )
})

test('bounded canary sampler persists its six-per-hour ceiling across restarts', () => {
  let now = 1_900_000_000_000
  const offers = Array.from({ length: 7 }, (_, index) => ({
    providerKey: 'provider-' + index,
    modelId: 'model-' + index,
    intell: 0.9 - (index / 100),
    status: 'pending',
  }))
  const sampler = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })

  for (let index = 0; index < 6; index += 1) {
    assert.ok(sampler.claim(offers))
    now += 60_000
  }
  assert.equal(sampler.claim(offers), null)
  assert.equal(sampler.snapshot().remainingInWindow, 0)

  const restored = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
    state: sampler.exportState(),
  })
  assert.equal(restored.claim(offers), null)
  now += 60 * 60 * 1000
  assert.ok(restored.claim(offers))
})

test('bounded canary sampler skips governed, disabled, and rate-blocked offers', () => {
  let now = 2_000_000_000_000
  const governor = new ProviderGovernor({ now: () => now })
  const blocked = { providerKey: 'nvidia', modelId: 'glm-5.2', status: 'pending' }
  const disabled = { providerKey: 'mistral', modelId: 'leanstral', status: 'disabled' }
  const available = { providerKey: 'opencode', modelId: 'nemotron-free', status: 'pending' }
  governor.openRateLimit(blocked, { retryAfterMs: 120_000 })

  const sampler = new BoundedCanarySampler({ now: () => now })
  assert.equal(sampler.claim([blocked, disabled, available], { governor })?.modelId, 'nemotron-free')
  sampler.record(available, { outcome: 'rate_limited', status: 429, retryAfterMs: 120_000 })
  now += 10 * 60 * 1000
  assert.equal(sampler.claim([available], { governor }), null)
})

test('bounded canary sampler skips a persisted NVIDIA 410 route without hiding GLM 5.2', () => {
  const now = 2_050_000_000_000
  const retired = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm5',
    status: 'down',
    httpCode: '410',
    intell: 0.99,
  }
  const canonical = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    status: 'pending',
    intell: 0.1,
  }
  const sampler = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })

  assert.equal(sampler.claim([retired, canonical])?.modelId, 'z-ai/glm-5.2')

  const persisted = new BoundedCanarySampler({
    now: () => now,
    state: {
      observations: {
        '["nvidia","z-ai/glm5"]': {
          providerKey: 'nvidia',
          modelId: 'z-ai/glm5',
          status: 'down',
          httpCode: '410',
          lastPingAt: now - 1,
          pings: [{ code: '410', ms: 369, ts: now - 1 }],
          observedAt: now - 1,
        },
      },
    },
  })
  const hydratedOffers = [
    { providerKey: 'nvidia', modelId: 'z-ai/glm5', status: 'pending', intell: 0.99 },
    { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', status: 'pending', intell: 0.1 },
  ]
  persisted.hydrate(hydratedOffers)

  assert.equal(hydratedOffers[0].httpCode, '410')
  assert.equal(persisted.snapshot().terminalCanaryExclusions, 1)
  assert.equal(persisted.claim(hydratedOffers)?.modelId, 'z-ai/glm-5.2')
})

test('bounded canary sampler does not repeatedly spend a slot on a deterministic incompatible route', () => {
  const now = 2_075_000_000_000
  const incompatible = {
    providerKey: 'nvidia',
    modelId: 'retired-or-invalid-route',
    status: 'down',
    httpCode: '400',
    intell: 0.99,
  }
  const canonical = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    status: 'pending',
    intell: 0.1,
  }
  const sampler = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })

  assert.equal(sampler.claim([incompatible, canonical])?.modelId, 'z-ai/glm-5.2')
})

test('bounded canary sampler rechecks NVIDIA degraded-function evidence without treating it as terminal incompatibility', () => {
  const now = 2_076_000_000_000
  const degraded = {
    providerKey: 'nvidia',
    modelId: 'minimaxai/minimax-m3',
    status: 'down',
    httpCode: '400',
    intell: 0.99,
    lastError: {
      code: '400',
      message: 'NVIDIA NIM reports this model function is currently degraded.',
    },
  }
  const sampler = new BoundedCanarySampler({
    now: () => now,
    minSpacingMs: 60_000,
    defaultProviderCooldownMs: 60_000,
  })

  assert.equal(sampler.claim([degraded])?.modelId, 'minimaxai/minimax-m3')
})

test('bounded canary sampler persists exact provider-model observations and hydrates only older rows', () => {
  const now = 2_100_000_000_000
  const sampler = new BoundedCanarySampler({ now: () => now })
  sampler.observe(
    { providerKey: 'nvidia', modelId: 'shared-id' },
    {
      status: 'up',
      lastPingAt: now,
      lastModelResponseAt: now,
      pings: [{ code: '200', ms: 900, ts: now }],
      lastError: null,
      cooldownUntil: now + 120_000,
    },
  )
  sampler.observe(
    { providerKey: 'mistral', modelId: 'shared-id' },
    {
      status: 'down',
      lastPingAt: now - 100,
      pings: [{ code: '503', ms: 1200, ts: now - 100 }],
      httpCode: 503,
      lastError: { code: 503, message: 'unavailable', updatedAt: now - 100 },
    },
  )

  const restored = new BoundedCanarySampler({ now: () => now, state: sampler.exportState() })
  const rows = [
    { providerKey: 'nvidia', modelId: 'shared-id', status: 'pending', pings: [] },
    { providerKey: 'mistral', modelId: 'shared-id', status: 'pending', pings: [] },
    {
      providerKey: 'other',
      modelId: 'fresh-local',
      status: 'up',
      lastPingAt: now + 100,
      pings: [{ code: '200', ms: 100, ts: now + 100 }],
    },
  ]
  restored.observe(
    { providerKey: 'other', modelId: 'fresh-local' },
    { status: 'down', lastPingAt: now, pings: [{ code: '500', ms: 500, ts: now }] },
  )
  restored.hydrate(rows)

  assert.equal(rows[0].status, 'up')
  assert.equal(rows[0].pings[0].ms, 900)
  assert.equal(rows[1].status, 'down')
  assert.equal(rows[1].httpCode, '503')
  assert.equal(rows[2].status, 'up')
  assert.equal(rows[2].pings[0].ms, 100)
  const governor = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
  restored.restoreCooldowns(governor, rows)
  assert.equal(governor.isOfferAvailable(rows[0]), false)
  assert.equal(restored.snapshot().persistedObservations, 3)
  assert.equal(restored.snapshot().activePersistedCooldowns, 1)
})

test('Mistral and NVIDIA serialize work while default providers allow two', async () => {
  const governor = new ProviderGovernor({ defaultConcurrency: 2, providerPacingMs: { nvidia: 0 } })

  for (const provider of ['mistral', 'nvidia', 'other']) {
    let active = 0
    let maximum = 0
    const jobs = Array.from({ length: 6 }, () => governor.run(provider, async () => {
      active += 1
      maximum = Math.max(maximum, active)
      await new Promise(resolve => setTimeout(resolve, 8))
      active -= 1
      return response(200)
    }))
    await Promise.all(jobs)
    assert.equal(maximum, provider === 'other' ? 2 : 1, provider)
  }
})

test('429 cools only the affected offer, keeps provider siblings available, and caps at two attempts', async () => {
  let now = 1_000
  const governor = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
  const seen = []
  const offers = [
    { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2' },
    { providerKey: 'nvidia', modelId: 'minimaxai/minimax-m3' },
    { providerKey: 'mistral', modelId: 'mistral-medium-3-5' },
  ]

  const result = await runGovernedAttempts({
    offers,
    governor,
    attempt: async offer => {
      seen.push(`${offer.providerKey}/${offer.modelId}`)
      return offer.modelId === 'z-ai/glm-5.2'
        ? response(429, { 'retry-after': '120' })
        : response(200)
    },
  })

  assert.equal(result.response.status, 200)
  assert.deepEqual(seen, [
    'nvidia/z-ai/glm-5.2',
    'nvidia/minimaxai/minimax-m3',
  ])
  assert.equal(result.attempts.length, 2)
  assert.equal(governor.providerState('nvidia'), 'CLOSED')
  assert.equal(governor.circuitRemainingMs('nvidia'), 0)
  assert.equal(governor.rateLimitRemainingMs(offers[0]), 120_000)
  assert.equal(governor.rateLimitRemainingMs(offers[1]), 0)
  await assert.rejects(
    governor.run('nvidia', async () => response(200), { offer: offers[0] }),
    ProviderRateLimitError,
  )
  now += 120_001
  assert.equal(governor.rateLimitRemainingMs(offers[0]), 0)
})

test('401, 402, and 403 create bounded stable-route access holds without poisoning sibling offers', async () => {
  for (const [status, expectedClass] of [[401, 'auth_required'], [402, 'payment_required'], [403, 'access_denied']]) {
    let now = 1_100_000
    const governor = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
    const failedWithResolvedCredentials = {
      providerKey: 'nvidia',
      modelId: 'z-ai/glm-5.2',
      offerId: 'nvidia/z-ai/glm-5.2',
      accountKey: 'account-fingerprint-a',
      connectionKey: 'connection-fingerprint-a',
    }
    const routeSelectionOffer = {
      providerKey: 'nvidia',
      modelId: 'z-ai/glm-5.2',
      offerId: 'nvidia/z-ai/glm-5.2',
    }
    const sibling = {
      providerKey: 'nvidia',
      modelId: 'minimaxai/minimax-m3',
      offerId: 'nvidia/minimaxai/minimax-m3',
    }

    assert.equal(classifyOfferAccessFailure(status), expectedClass)
    governor.recordOfferStatus(failedWithResolvedCredentials, status)
    const access = governor.offerAccessStatus(routeSelectionOffer)
    assert.equal(access.accessClass, expectedClass)
    assert.equal(access.remainingMs, 15 * 60 * 1000)
    assert.equal(governor.isOfferAvailable(routeSelectionOffer), false)
    assert.equal(governor.isOfferAvailable(sibling), true)
    await assert.rejects(
      governor.run('nvidia', async () => response(200), { offer: routeSelectionOffer }),
      ProviderOfferAccessBlockedError,
    )

    now += (15 * 60 * 1000) + 1
    assert.equal(governor.isOfferAvailable(routeSelectionOffer), true)
    governor.recordOfferStatus(routeSelectionOffer, 200)
    assert.equal(governor.offerAccessStatus(routeSelectionOffer).accessClass, null)
  }
})

test('offer circuits use the same provider-qualified identity during selection and failure recording', () => {
  let now = 1_150_000
  const governor = new ProviderGovernor({ now: () => now })
  const failedWithResolvedCredentials = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    offerId: 'nvidia/z-ai/glm-5.2',
    accountKey: 'account-fingerprint-a',
    connectionKey: 'connection-fingerprint-a',
  }
  const routeSelectionOffer = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    offerId: 'nvidia/z-ai/glm-5.2',
  }

  governor.recordOfferStatus(failedWithResolvedCredentials, 404)
  assert.equal(governor.isOfferAvailable(routeSelectionOffer), false)
  now += 60_001
  assert.equal(governor.isOfferAvailable(routeSelectionOffer), true)
})

test('access holds persist across relay restart and expire back to an unverified offer', () => {
  let now = 1_200_000
  const offer = {
    providerKey: 'openai-compatible:baseten',
    modelId: 'zai-org/GLM-5.2',
    offerId: 'openai-compatible:baseten/zai-org/glm-5.2',
  }
  const sourceGovernor = new ProviderGovernor({ now: () => now })
  sourceGovernor.recordOfferStatus({ ...offer, accountKey: 'account-a' }, 402)
  const access = sourceGovernor.offerAccessStatus(offer)
  const sampler = new BoundedCanarySampler({ now: () => now })
  sampler.observe(offer, {
    status: 'payment_required',
    httpCode: '402',
    lastPingAt: now,
    pings: [{ code: '402', ms: 120, ts: now }],
    lastError: { code: '402', message: 'payment required', updatedAt: now },
    accessClass: access.accessClass,
    accessUntil: access.until,
  })

  const restored = new BoundedCanarySampler({ now: () => now, state: sampler.exportState() })
  const rows = [{ ...offer, status: 'pending', pings: [] }]
  const restoredGovernor = new ProviderGovernor({ now: () => now })
  restored.hydrate(rows)
  restored.restoreCooldowns(restoredGovernor, rows)
  assert.equal(rows[0].status, 'payment_required')
  assert.equal(rows[0].accessClass, 'payment_required')
  assert.equal(restored.snapshot().activePersistedAccessBlocks, 1)
  assert.equal(restoredGovernor.isOfferAvailable(rows[0]), false)
  assert.equal(restored.claim(rows, { governor: restoredGovernor }), null)

  now += (15 * 60 * 1000) + 1
  const expiredRows = [{ ...offer, status: 'pending', pings: [] }]
  restored.hydrate(expiredRows)
  const expiredGovernor = new ProviderGovernor({ now: () => now })
  restored.restoreCooldowns(expiredGovernor, expiredRows)
  assert.equal(expiredRows[0].status, 'pending')
  assert.equal(expiredRows[0].accessClass, null)
  assert.equal(restored.snapshot().activePersistedAccessBlocks, 0)
  assert.equal(expiredGovernor.isOfferAvailable(expiredRows[0]), true)
})

test('rate-limit scope classification isolates account, connection, model, and exact offers', () => {
  let now = 5_000
  const governor = new ProviderGovernor({ now: () => now })
  const base = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    accountKey: 'account-fingerprint-a',
    connectionKey: 'connection-fingerprint-a',
    offerId: 'nim-glm-primary',
  }
  const sameAccount = { ...base, modelId: 'minimaxai/minimax-m3', offerId: 'nim-m3-primary' }
  const otherAccount = { ...base, accountKey: 'account-fingerprint-b' }

  assert.equal(classifyRateLimitScope(new Headers({ 'x-ratelimit-scope': 'account' }), base), 'account')
  assert.equal(classifyRateLimitScope(new Headers({ 'x-ratelimit-scope': 'connection' }), base), 'connection')
  assert.equal(classifyRateLimitScope(new Headers({ 'x-ratelimit-scope': 'model' }), base), 'model')
  assert.equal(classifyRateLimitScope(new Headers({ 'x-ratelimit-scope': 'provider' }), base), 'offer')

  governor.openRateLimit(base, { scope: 'account', retryAfterMs: 90_000 })
  assert.equal(governor.isOfferAvailable(base), false)
  assert.equal(governor.isOfferAvailable(sameAccount), false)
  assert.equal(governor.isOfferAvailable(otherAccount), true)
  assert.equal(governor.isAvailable('nvidia'), true)

  now += 90_001
  governor.openRateLimit(base, { scope: 'connection', retryAfterMs: 90_000 })
  assert.equal(governor.isOfferAvailable(otherAccount), false)
  assert.equal(governor.isOfferAvailable({ ...otherAccount, connectionKey: 'connection-fingerprint-b' }), true)

  now += 90_001
  governor.openRateLimit(base, { scope: 'model', retryAfterMs: 90_000 })
  assert.equal(governor.isOfferAvailable(otherAccount), false)
  assert.equal(governor.isOfferAvailable({ ...otherAccount, modelId: 'minimaxai/minimax-m3' }), true)

  now += 90_001
  governor.openRateLimit(base, { scope: 'offer', retryAfterMs: 90_000 })
  assert.equal(governor.isOfferAvailable(base), false)
  assert.equal(governor.isOfferAvailable(otherAccount), true)
})

test('NVIDIA 429 cooldown has a 75 second floor and honors longer Retry-After', () => {
  let now = 10_000
  const governor = new ProviderGovernor({ now: () => now })
  const short = { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', accountKey: 'a' }
  const long = { providerKey: 'nvidia', modelId: 'minimaxai/minimax-m3', accountKey: 'a' }

  governor.openRateLimit(short, { retryAfterMs: 10_000 })
  governor.openRateLimit(long, { retryAfterMs: 120_000 })
  assert.equal(governor.rateLimitRemainingMs(short), 75_000)
  assert.equal(governor.rateLimitRemainingMs(long), 120_000)

  now += 75_001
  assert.equal(governor.isOfferAvailable(short), true)
  assert.equal(governor.isOfferAvailable(long), false)
})

test('provider transient 5xx failures degrade then open while success closes the circuit', () => {
  let now = 20_000
  const governor = new ProviderGovernor({ now: () => now, providerOpenMs: 30_000 })

  governor.recordStatus('nvidia', 503)
  assert.equal(governor.providerState('nvidia'), 'DEGRADED')
  assert.equal(governor.isAvailable('nvidia'), true)

  governor.recordStatus('nvidia', 502)
  assert.equal(governor.providerState('nvidia'), 'OPEN')
  assert.equal(governor.isAvailable('nvidia'), false)
  assert.equal(governor.circuitRemainingMs('nvidia'), 30_000)

  now += 30_001
  assert.equal(governor.providerState('nvidia'), 'DEGRADED')
  assert.equal(governor.isAvailable('nvidia'), true)
  governor.recordStatus('nvidia', 200)
  assert.equal(governor.providerState('nvidia'), 'CLOSED')
})

test('provider timeouts degrade then open without treating caller abort as provider failure', async () => {
  let now = 30_000
  const governor = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
  const timeout = () => Object.assign(new Error('timed out'), {
    name: 'TimeoutError',
    code: 'NEXUS_FIRST_BYTE_TIMEOUT',
  })

  await assert.rejects(governor.run('nvidia', async () => { throw timeout() }), /timed out/)
  assert.equal(governor.providerState('nvidia'), 'DEGRADED')
  await assert.rejects(governor.run('nvidia', async () => { throw timeout() }), /timed out/)
  assert.equal(governor.providerState('nvidia'), 'OPEN')
  await assert.rejects(governor.run('nvidia', async () => response(200)), ProviderCircuitOpenError)

  const other = new ProviderGovernor({ now: () => now })
  await assert.rejects(
    other.run('nvidia', async () => { throw new DOMException('caller left', 'AbortError') }),
    error => error?.name === 'AbortError',
  )
  assert.equal(other.providerState('nvidia'), 'CLOSED')

  const scoped = new ProviderGovernor({ now: () => now, providerPacingMs: { nvidia: 0 } })
  const offer = {
    providerKey: 'nvidia',
    modelId: 'z-ai/glm-5.2',
    offerId: 'nim-glm-primary',
  }
  await assert.rejects(
    scoped.run('nvidia', async () => { throw timeout() }, { offer }),
    /timed out/,
  )
  assert.equal(scoped.providerState('nvidia'), 'CLOSED')
  assert.equal(scoped.offerState(offer), 'OPEN')
  assert.equal(scoped.isOfferAvailable(offer), false)
  await assert.rejects(
    scoped.run('nvidia', async () => response(200), { offer }),
    ProviderOfferCircuitOpenError,
  )
})

test('NVIDIA starts are paced at 7.5 seconds with an injected fake clock', async () => {
  let now = 0
  const sleeps = []
  const starts = []
  const governor = new ProviderGovernor({
    now: () => now,
    sleep: async ms => {
      sleeps.push(ms)
      now += ms
    },
  })

  for (let index = 0; index < 3; index += 1) {
    await governor.run('nvidia', async () => {
      starts.push(now)
      return response(200)
    })
  }
  assert.deepEqual(starts, [0, 7_500, 15_000])
  assert.deepEqual(sleeps, [7_500, 7_500])

  await governor.run('mistral', async () => starts.push(now))
  assert.equal(now, 15_000)
})

test('provider attempt budget counts actual calls including in-attempt auth fallback', async () => {
  const budget = new ProviderAttemptBudget(2)
  const calls = []

  await budget.run(async () => calls.push('anonymous'))
  await budget.run(async () => calls.push('bearer-fallback'))

  assert.deepEqual(calls, ['anonymous', 'bearer-fallback'])
  assert.equal(budget.used, 2)
  assert.equal(budget.remaining, 0)
  await assert.rejects(
    budget.run(async () => calls.push('forbidden-third-call')),
    ProviderAttemptBudgetError,
  )
  assert.equal(calls.length, 2)
})

test('offer-specific 401, 402, 403, and 404 fail over while request-invalid 400 stays terminal', async () => {
  for (const status of [401, 402, 403, 404]) {
    const seen = []
    const result = await runGovernedAttempts({
      offers: [
        { providerKey: 'nvidia', modelId: 'first' },
        { providerKey: 'mistral', modelId: 'second' },
      ],
      governor: new ProviderGovernor({ providerPacingMs: { nvidia: 0 } }),
      attempt: async offer => {
        seen.push(offer.modelId)
        return offer.modelId === 'first' ? response(status) : response(200)
      },
    })
    assert.equal(result.response.status, 200)
    assert.deepEqual(seen, ['first', 'second'])
    assert.equal(result.attempts.length, 2)
  }

  const seen = []
  const result = await runGovernedAttempts({
    offers: [
      { providerKey: 'nvidia', modelId: 'first' },
      { providerKey: 'mistral', modelId: 'second' },
    ],
    governor: new ProviderGovernor({ providerPacingMs: { nvidia: 0 } }),
    attempt: async offer => {
      seen.push(offer.modelId)
      return response(400)
    },
  })
  assert.equal(result.response.status, 400)
  assert.deepEqual(seen, ['first'])
})

test('distinct offers with the same provider and model remain independently routable', async () => {
  const seen = []
  const result = await runGovernedAttempts({
    offers: [
      { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', offerId: 'account-a' },
      { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', offerId: 'account-b' },
    ],
    governor: new ProviderGovernor({ providerPacingMs: { nvidia: 0 } }),
    attempt: async offer => {
      seen.push(offer.offerId)
      return response(offer.offerId === 'account-a' ? 503 : 200)
    },
  })
  assert.equal(result.response.status, 200)
  assert.deepEqual(seen, ['account-a', 'account-b'])
})

test('caller cancellation aborts queued or active work without a retry', async () => {
  const controller = new AbortController()
  let calls = 0
  const pending = runGovernedAttempts({
    offers: [
      { providerKey: 'nvidia', modelId: 'first' },
      { providerKey: 'mistral', modelId: 'second' },
    ],
    governor: new ProviderGovernor(),
    signal: controller.signal,
    deadlines: { firstByteMs: 5_000, totalMs: 10_000 },
    attempt: async (_offer, { signal }) => {
      calls += 1
      await new Promise((resolve, reject) => {
        signal.addEventListener('abort', () => reject(signal.reason), { once: true })
      })
    },
  })
  setTimeout(() => controller.abort(new DOMException('client disconnected', 'AbortError')), 10)

  await assert.rejects(pending, error => error?.name === 'AbortError')
  assert.equal(calls, 1)
})

test('first-byte deadline aborts only the offer and retries one distinct offer', async () => {
  let calls = 0
  const result = await runGovernedAttempts({
    offers: [
      { providerKey: 'nvidia', modelId: 'first' },
      { providerKey: 'mistral', modelId: 'second' },
    ],
    governor: new ProviderGovernor({ providerPacingMs: { nvidia: 0 } }),
    deadlines: { firstByteMs: 15, totalMs: 100 },
    attempt: async (offer, { signal }) => {
      calls += 1
      if (offer.modelId === 'first') {
        await new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => reject(signal.reason), { once: true })
        })
      }
      return response(200)
    },
  })
  assert.equal(result.response.status, 200)
  assert.equal(calls, 2)
  assert.equal(result.attempts[0].error, 'NEXUS_FIRST_BYTE_TIMEOUT')
  assert.equal(result.attempts[1].status, 200)
})

test('Retry-After supports delta seconds and HTTP dates with safe bounds', () => {
  const now = Date.parse('2026-07-11T00:00:00Z')
  assert.equal(parseRetryAfterMs('120', now), 120_000)
  assert.equal(parseRetryAfterMs('Fri, 11 Jul 2026 00:02:00 GMT', now), 120_000)
  assert.equal(parseRetryAfterMs(null, now), 60_000)
  assert.equal(parseRetryAfterMs('-20', now), 1_000)
})
