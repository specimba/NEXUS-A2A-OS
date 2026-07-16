import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import { verifyRuntime } from '../src/verify-runtime.mjs'
import { NEXUS_RESILIENT_MODEL_ID, projectRoutableModelIds } from '../src/nexus-runtime-policy.js'
import {
  canonicalizeModelId,
  getPreferredModelContext,
  getPreferredModelLabel,
  resolveAliasedModelId,
  sources,
} from '../node_modules/modelrelay/sources.js'
import {
  mergeConfiguredAndDiscoveredModels,
  nexusUnavailableRouteError,
  toOpenAICompatibleDiscoveredModelMeta,
} from '../node_modules/modelrelay/lib/server.js'
import {
  buildModelGroups,
  createOfferScopedAbortSignal,
  filterModelsByRequested,
  getVerdict,
  rankModelsForRouting,
  sanitizeProxyAttempts,
} from '../node_modules/modelrelay/lib/utils.js'


const here = dirname(fileURLToPath(import.meta.url))
const serviceRoot = resolve(here, '..')
const repoRoot = resolve(serviceRoot, '..', '..')

async function registry() {
  return JSON.parse(await readFile(resolve(repoRoot, 'config/models.registry.json'), 'utf8'))
}

test('runtime verification proves exact upstream version, integrity, and patch markers', async () => {
  const report = await verifyRuntime({ serviceRoot })
  assert.equal(report.ok, true)
  assert.equal(report.version, '1.18.0')
  assert.equal(report.patchMarkers.safeRuntime, true)
  assert.equal(report.patchMarkers.configPath, true)
  assert.equal(report.patchMarkers.nullUnknownScore, true)
  assert.equal(report.patchMarkers.unscoredStatic, true)
  assert.equal(report.patchMarkers.twoCallBudget, true)
  assert.equal(report.patchMarkers.scoped429, true)
  assert.equal(report.patchMarkers.entitlementAware, true)
  assert.equal(report.patchMarkers.entitlementVerdicts, true)
  assert.equal(report.patchMarkers.nvidiaPacing, true)
  assert.equal(report.patchMarkers.nvidiaCooldown, true)
  assert.equal(report.patchMarkers.nvidiaDegradedFunction, true)
  assert.equal(report.patchMarkers.actionableNimUnavailable, true)
  assert.equal(report.patchMarkers.leanstralAlias, true)
  assert.equal(report.patchMarkers.glm52Context, true)
  assert.equal(report.patchMarkers.canonicalDedup, true)
  assert.equal(report.patchMarkers.providerQualifiedRoutes, true)
  assert.equal(report.patchMarkers.logicalOfferGroups, true)
  assert.equal(report.patchMarkers.offerScopedAbort, true)
  assert.equal(report.patchMarkers.structuredRouteReceipt, true)
  assert.equal(report.patchMarkers.immediateTimeoutQuarantine, true)
  assert.equal(report.patchMarkers.boundedCanarySampler, true)
  assert.equal(report.patchMarkers.healthSamplerEndpoint, true)
  assert.equal(report.patchMarkers.terminalCanaryExclusion, true)
  assert.equal(report.patchMarkers.providerAwareManualPing, true)
  assert.equal(report.patchMarkers.truthfulDashboardHealth, true)
  assert.equal(report.patchMarkers.providerQualifiedDashboardRows, true)
  assert.equal(report.patchMarkers.persistentHealthObservations, true)
  assert.equal(report.patchMarkers.healthHydration, true)
  assert.equal(report.patchMarkers.persistentCooldownRestore, true)
  assert.equal(report.patchMarkers.resilientAlias, true)
})

test('7350 control center labels routing metadata honestly and links the evidence arena', async () => {
  const dashboard = await readFile(
    join(serviceRoot, 'node_modules', 'modelrelay', 'public', 'index.html'),
    'utf8',
  )
  assert.match(dashboard, /Evidence Arena/)
  assert.match(dashboard, /Best Available Route/)
  assert.match(dashboard, /127\.0\.0\.1:7356\/dashboard\.html/)
  assert.match(dashboard, /Route score/)
  assert.match(dashboard, /not benchmark evidence/i)
  assert.doesNotMatch(dashboard, /id="th-intell">SWE%/)
})

test('all 7350 launchers use the repo-owned verified runtime', async () => {
  const launcherPaths = [
    'scripts/start_node_relay.ps1',
    'scripts/start_nexus_services.ps1',
    'scripts/revive_relay_ports.ps1',
    'scripts/start_nexus_gateway.ps1',
  ]
  for (const path of launcherPaths) {
    const body = await readFile(join(repoRoot, path), 'utf8')
    assert.match(body, /modelrelay_runtime\.ps1/i, path)
    assert.doesNotMatch(body, /APPDATA[^\r\n]*node_modules[^\r\n]*modelrelay/i, path)
  }
})

test('PowerShell helper enforces the governed runtime contract', async () => {
  const body = await readFile(join(repoRoot, 'scripts/modelrelay_runtime.ps1'), 'utf8')
  assert.match(body, /services[\\/]modelrelay-nexus/i)
  assert.match(body, /127\.0\.0\.1/)
  assert.match(body, /MODELRELAY_NEXUS_SAFE_RUNTIME/)
  assert.match(body, /MODELRELAY_DISABLE_AUTO_UPDATE/)
  assert.match(body, /MODELRELAY_HEALTH_SAMPLER_PATH/)
  assert.match(body, /MODELRELAY_ROUTE_FIRST_BYTE_BUDGET_MS/)
  assert.match(body, /RouteFirstByteBudgetMs = 25000/)
  assert.match(body, /logs[\\/]modelrelay_health_sampler\.json/i)
  assert.doesNotMatch(body, /npm install -g/i)
})

test('controlled 7350 reload preserves the relay boundary and verifies new health semantics', async () => {
  const body = await readFile(join(repoRoot, 'scripts', 'restart_modelrelay_7350.ps1'), 'utf8')
  assert.match(body, /\$port = 7350/)
  assert.match(body, /Test-GovernedRelayContract/)
  assert.match(body, /modelrelay_runtime\.ps1/)
  assert.match(body, /activePersistedAccessBlocks/)
  assert.match(body, /terminalCanaryExclusions/)
  assert.match(body, /0\.0\.0\.0/)
  assert.doesNotMatch(body, /7352/)
})

test('Leanstral aliases collapse to the dated canonical route with registry metadata', async () => {
  const data = await registry()
  const model = data.models.find(row => (
    row.provider === 'mistral' && row.id === 'labs-leanstral-1-5-1'
  ))

  assert.ok(model)
  assert.equal(model.context, 262_144)
  assert.equal(resolveAliasedModelId('labs-leanstral-1-5'), model.id)
  assert.equal(resolveAliasedModelId('leanstral'), model.id)
  assert.equal(canonicalizeModelId('labs-leanstral-1-5').base, model.id)
  assert.equal(getPreferredModelLabel('labs-leanstral-1-5'), 'Leanstral 1.5')
  assert.equal(getPreferredModelContext('labs-leanstral-1-5'), '256k')
})

test('configured and discovered Leanstral aliases produce one routable offer', () => {
  const configured = {
    modelId: 'labs-leanstral-1-5',
    label: 'Leanstral 1.5',
    ctx: '256k',
  }
  const discovered = [{
    modelId: 'labs-leanstral-1-5-1',
    label: 'Leanstral 1.5',
    ctx: '256k',
  }]

  assert.deepEqual(
    mergeConfiguredAndDiscoveredModels(configured, discovered),
    discovered,
  )
})

test('canonical context overrides provider-stale GLM-5.2 metadata', () => {
  const nvidiaGlm = sources.nvidia.models.find(([modelId]) => modelId === 'z-ai/glm-5.2')
  assert.equal(nvidiaGlm?.[2], '1M')
  assert.equal(getPreferredModelContext('z-ai/glm-5.2', '200k'), '1M')
  assert.equal(getPreferredModelContext('zai-org/GLM-5.2', '203k'), '1M')
  assert.equal(getPreferredModelContext('glm-5.2', '128k'), '1M')

  const discovered = toOpenAICompatibleDiscoveredModelMeta(
    { id: 'zai-org/GLM-5.2', context_length: 202_752 },
    'openai-compatible:baseten',
  )
  assert.equal(discovered.ctx, '1M')
})

test('v1 projection emits each normalized model id once', () => {
  const rows = [
    {
      modelId: 'openai/gpt-oss-120b',
      label: 'GPT OSS 120B',
      providerKey: 'nvidia',
    },
    {
      modelId: 'gpt-oss-120b',
      label: 'gpt-oss-120b',
      providerKey: 'openai-compatible:example',
    },
  ]
  const groups = buildModelGroups(rows, canonicalizeModelId)
  assert.equal(groups.length, 1)
  assert.equal(groups[0].id, 'gpt-oss-120b')
  assert.equal(groups[0].models.length, 2)
})

test('ambiguous model groups expose deterministic provider-qualified routes', () => {
  const projection = projectRoutableModelIds([
    {
      id: 'glm-5.2',
      label: 'GLM 5.2',
      models: [
        { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2' },
        { providerKey: 'openai-compatible:ollama-cloud', modelId: 'glm-5.2' },
        { providerKey: 'openai-compatible:baseten', modelId: 'zai-org/GLM-5.2' },
      ],
    },
  ])

  assert.deepEqual(
    projection.map(row => row.id),
    [
      'glm-5.2',
      'nvidia/z-ai/glm-5.2',
      'openai-compatible:baseten/zai-org/glm-5.2',
      'openai-compatible:ollama-cloud/glm-5.2',
    ],
  )
  assert.equal(new Set(projection.map(row => row.id)).size, projection.length)
  assert.equal(projection[1].providerQualified, true)
})

test('the protected NVIDIA GLM lock remains addressable when it is a singleton offer', () => {
  const projection = projectRoutableModelIds([
    {
      id: 'glm-5.2',
      label: 'GLM 5.2',
      models: [
        { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2' },
      ],
    },
  ])

  assert.deepEqual(
    projection.map(row => row.id),
    ['glm-5.2', 'nvidia/z-ai/glm-5.2'],
  )
  assert.equal(projection[1].providerQualified, true)
})

test('exact provider-offer failures retain typed terminal receipts', () => {
  const cases = [
    ['UPSTREAM_HTTP_402', 402, 'NEXUS_PROVIDER_PAYMENT_REQUIRED'],
    ['UPSTREAM_HTTP_403', 403, 'NEXUS_PROVIDER_ACCESS_DENIED'],
    ['UPSTREAM_HTTP_429', 429, 'NEXUS_PROVIDER_OFFER_RATE_LIMITED'],
  ]
  for (const [errorCode, status, code] of cases) {
    const result = nexusUnavailableRouteError([{ errorCode }], { exactOfferRequested: true })
    assert.equal(result.status, status)
    assert.equal(result.code, code)
  }
  const noOffer = nexusUnavailableRouteError([], { exactOfferRequested: true })
  assert.equal(noOffer.status, 503)
  assert.equal(noOffer.code, 'NEXUS_NO_ELIGIBLE_PROVIDER_OFFER')
})

test('shadow v1 catalogue wires provider-qualified routes through the runtime policy', async () => {
  const body = await readFile(
    join(serviceRoot, 'node_modules', 'modelrelay', 'lib', 'server.js'),
    'utf8',
  )

  assert.match(body, /projectRoutableModelIds\(groups\)/)
  assert.match(body, /providerQualified \? 'relay-offer' : 'relay'/)
})

test('v1 catalogue advertises the explicit context-aware warm-evidence nexus-resilient alias', async () => {
  const body = await readFile(
    join(serviceRoot, 'node_modules', 'modelrelay', 'lib', 'server.js'),
    'utf8',
  )

  assert.equal(NEXUS_RESILIENT_MODEL_ID, 'nexus-resilient')
  assert.match(body, /NEXUS_RESILIENT_ALIAS/)
  assert.match(body, /id: NEXUS_RESILIENT_MODEL_ID/)
  assert.match(body, /isNexusResilientModelId\(payload\.model\)/)
  assert.match(body, /const estimatedPromptTokens = estimateNexusPromptTokens\(payload\)/)
  assert.match(body, /selectNexusResilientOffers\(results, \{\s+governor: nexusGovernor,\s+estimatedPromptTokens,\s+outputReserveTokens,/s)
  assert.match(body, /estimatedPromptTokens,\s+\}\)/s)
  assert.match(body, /if \(resilientAliasRequested\) \{\s+return eligible\.find/s)
  assert.match(body, /!resilientAliasRequested && requestedModels\.length === 0/)
  assert.doesNotMatch(body, /nexus-resilient[^\n]{0,160}auto-fastest/i)
})


test('a bare canonical ID selects the full logical group while qualified routes remain exact', () => {
  const offers = [
    { providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', label: 'GLM 5.2' },
    { providerKey: 'openai-compatible:ollama-cloud', modelId: 'glm-5.2', label: 'GLM 5.2' },
    { providerKey: 'openai-compatible:baseten', modelId: 'zai-org/GLM-5.2', label: 'GLM 5.2' },
  ]

  assert.deepEqual(
    filterModelsByRequested(offers, 'glm-5.2', canonicalizeModelId),
    offers,
  )
  assert.deepEqual(
    filterModelsByRequested(offers, 'nvidia/z-ai/glm-5.2', canonicalizeModelId),
    [offers[0]],
  )
  assert.deepEqual(
    filterModelsByRequested(offers, 'openai-compatible:ollama-cloud/glm-5.2', canonicalizeModelId),
    [offers[1]],
  )
  assert.deepEqual(
    filterModelsByRequested(offers, 'openai-compatible:baseten/zai-org/glm-5.2', canonicalizeModelId),
    [offers[2]],
  )
})

test('observed-healthy offers outrank unverified catalogue offers before QoS', () => {
  const offers = [
    {
      providerKey: 'nvidia', modelId: 'z-ai/glm-5.2', label: 'GLM 5.2',
      status: 'up', intell: 0.78, pings: [{ code: '200', ms: 1_800 }],
    },
    {
      providerKey: 'openai-compatible:ollama-cloud', modelId: 'glm-5.2', label: 'GLM 5.2',
      status: 'pending', intell: 0.99, pings: [],
    },
    {
      providerKey: 'openai-compatible:baseten', modelId: 'zai-org/GLM-5.2', label: 'GLM 5.2',
      status: 'access_denied', intell: 1, pings: [],
    },
  ]

  assert.deepEqual(
    rankModelsForRouting(offers).map(row => `${row.providerKey}/${row.modelId}`),
    [
      'nvidia/z-ai/glm-5.2',
      'openai-compatible:ollama-cloud/glm-5.2',
      'openai-compatible:baseten/zai-org/GLM-5.2',
    ],
  )
})

test('offer-scoped first-byte abort never poisons the request controller', async () => {
  const request = new AbortController()
  const offer = createOfferScopedAbortSignal(request.signal, 10)

  await delay(20)
  assert.equal(offer.signal.aborted, true)
  assert.equal(offer.signal.reason?.code, 'NEXUS_FIRST_BYTE_TIMEOUT')
  assert.equal(request.signal.aborted, false)
  offer.cleanup()

  const requestFailure = Object.assign(new Error('request total deadline'), {
    name: 'TimeoutError',
    code: 'NEXUS_TOTAL_TIMEOUT',
  })
  const linked = createOfferScopedAbortSignal(request.signal, 5_000)
  request.abort(requestFailure)
  assert.equal(linked.signal.aborted, true)
  assert.equal(linked.signal.reason, requestFailure)
  linked.cleanup()
})

test('proxy attempt receipts preserve route evidence without leaking upstream bodies', () => {
  const attempts = sanitizeProxyAttempts([
    {
      index: 1,
      provider: 'nvidia',
      model: 'z-ai/glm-5.2',
      status: 'ERR',
      duration: 45_012.7,
      firstByteDeadlineMs: 25_000,
      retryable: true,
      errorCode: 'NEXUS_FIRST_BYTE_TIMEOUT',
      error: 'secret-token=must-not-leak',
    },
    {
      index: 2,
      provider: 'openai-compatible:baseten',
      model: 'zai-org/GLM-5.2',
      status: '402',
      duration: 912,
      retryable: true,
      error: '{"api_key":"must-not-leak"}',
    },
  ])

  assert.equal(attempts.length, 2)
  assert.equal(attempts[0].duration_ms, 45_013)
  assert.equal(attempts[0].first_byte_deadline_ms, 25_000)
  assert.equal(attempts[0].error_code, 'NEXUS_FIRST_BYTE_TIMEOUT')
  assert.equal(attempts[1].status, '402')
  assert.doesNotMatch(JSON.stringify(attempts), /must-not-leak|secret-token|api_key/)
})

test('dashboard keeps authentication, subscription, and access-denied health distinct', async () => {
  const publicDashboard = await readFile(
    join(serviceRoot, 'node_modules', 'modelrelay', 'public', 'index.html'),
    'utf8',
  )
  assert.match(publicDashboard, /AUTH REQUIRED/)
  assert.match(publicDashboard, /SUBSCRIPTION REQUIRED/)
  assert.match(publicDashboard, /ACCESS DENIED/)
  assert.match(publicDashboard, /formatAccessRetry/)
})

test('API verdicts keep access failures distinct from pending and generic downtime', () => {
  const base = { pings: [], httpCode: null }
  assert.equal(getVerdict({ ...base, status: 'auth_required' }), 'Auth Required')
  assert.equal(getVerdict({ ...base, status: 'payment_required' }), 'Subscription Required')
  assert.equal(getVerdict({ ...base, status: 'access_denied' }), 'Access Denied')
})
