import assert from 'node:assert/strict'
import test from 'node:test'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { buildModelCardProjection } = require('../../scripts/model_card_projection.js')

const registry = {
  providers: {
    nvidia: { status: 'active' },
    mistral: { status: 'active' },
  },
  models: [
    {
      id: 'z-ai/glm-5.2',
      provider: 'nvidia',
      aliases: ['glm-5.2'],
      context: 1_048_576,
      maxOutput: 8_192,
      tier: 96,
      free: true,
      capabilities: { tools: true, thinking: true },
      roles: ['frontier', 'code'],
      lanes: ['core', 'teacher'],
      status: 'active',
    },
    {
      id: 'labs-leanstral-1-5-1',
      provider: 'mistral',
      aliases: ['leanstral'],
      context: 262_144,
      maxOutput: null,
      tier: null,
      free: true,
      capabilities: { tools: true, thinking: true },
      roles: ['code'],
      lanes: ['specialist'],
      status: 'active',
    },
  ],
}

const snapshot = {
  version: 1,
  generated_at: '2026-07-10T19:05:47.706961+00:00',
  models: {
    'z-ai/glm-5.2': {
      arena_score: 0.7161,
      code_score: 0.684,
      confidence: 'high',
      sources: ['aa_coding', 'aa_intelligence_index', 'lmarena_code_elo', 'lmarena_elo'],
      as_of: '2026-07-08T00:00:00+00:00',
    },
  },
}

test('projection separates CLI visibility, observed health, and benchmark evidence', () => {
  const projection = buildModelCardProjection({
    arenaModels: [
      {
        modelId: 'z-ai/glm-5.2', label: 'GLM-5.2', providerKey: 'nvidia',
        status: 'pending', pings: [], lastPingAt: 0, intell: null, isEstimatedScore: true,
      },
      {
        modelId: 'labs-leanstral-1-5-1', label: 'Leanstral 1.5',
        providerKey: 'openai-compatible:mistral', status: 'up',
        pings: [{ code: '200', ms: 4853, ts: 1783817360727 }],
        lastPingAt: 0, avg: null, intell: null, isEstimatedScore: true,
      },
    ],
    v1Models: [
      { id: 'auto-fastest' },
      { id: 'z-ai/glm-5.2' },
      { id: 'labs-leanstral-1-5-1' },
    ],
    providerConfigs: [
      { key: 'nvidia', enabled: true, hasKey: true },
      { key: 'openai-compatible:mistral', enabled: true, hasKey: true },
    ],
    registry,
    arenaSnapshot: snapshot,
    generatedAt: '2026-07-12T01:00:00.000Z',
  })

  assert.deepEqual(projection.summary, {
    catalogue_offers: 2,
    relay_route_ids: 3,
    automatic_route_ids: 1,
    cli_model_ids: 2,
    cli_visible_offers: 2,
    observed_healthy: 1,
    observed_stale: 0,
    health_unverified: 1,
    unavailable: 0,
    rate_limited: 0,
    evidence_backed_offers: 1,
    configured_providers: 2,
    authenticated_providers: 2,
  })

  const glm = projection.models.find((model) => model.model_id === 'z-ai/glm-5.2')
  assert.equal(glm.health.state, 'unverified')
  assert.equal(glm.health.observed, false)
  assert.equal(glm.routing.cli_visible, true)
  assert.equal(glm.routing.cli_route_id, 'z-ai/glm-5.2')
  assert.equal(glm.benchmarks.status, 'evidence_backed')
  assert.equal(glm.benchmarks.dimensions.quality, 0.7161)
  assert.equal(glm.benchmarks.dimensions.code, 0.684)
  assert.equal(glm.benchmarks.dimensions.swe, null)
  assert.deepEqual(glm.benchmarks.coverage, ['quality', 'code'])
  assert.equal(glm.policy_prior.registry_tier, 96)

  const leanstral = projection.models.find((model) => model.model_id === 'labs-leanstral-1-5-1')
  assert.equal(leanstral.health.state, 'healthy')
  assert.equal(leanstral.health.observed, true)
  assert.equal(leanstral.health.fresh, true)
  assert.equal(leanstral.health.age_seconds, 639)
  assert.equal(leanstral.benchmarks.status, 'no_data')
  assert.equal(leanstral.benchmarks.dimensions.quality, null)
  assert.equal(leanstral.health.latency_ms, 4853)
  assert.equal(leanstral.health.last_checked_at, '2026-07-12T00:49:20.727Z')
  assert.equal(leanstral.policy_prior.registry_tier, null)
  assert.equal(leanstral.registry.max_output_tokens, null)
  assert.equal(leanstral.benchmarks.catalogue_score, null)
})

test('expired successful observations are stale rather than healthy', () => {
  const checkedAt = Date.parse('2026-07-12T00:00:00.000Z')
  const projection = buildModelCardProjection({
    arenaModels: [{
      modelId: 'stale-model',
      label: 'Stale Model',
      providerKey: 'nvidia',
      status: 'up',
      pings: [{ code: '200', ms: 75, ts: checkedAt }],
    }],
    v1Models: [{ id: 'stale-model' }],
    providerConfigs: [{ key: 'nvidia', enabled: true, hasKey: true }],
    registry: { providers: {}, models: [] },
    arenaSnapshot: { version: 1, models: {} },
    generatedAt: '2026-07-12T00:36:00.000Z',
  })

  assert.equal(projection.summary.observed_healthy, 0)
  assert.equal(projection.summary.observed_stale, 1)
  assert.equal(projection.models[0].health.state, 'stale')
  assert.equal(projection.models[0].health.fresh, false)
  assert.equal(projection.models[0].health.age_seconds, 2160)
})

test('a fresh failed alias cannot remain healthy or outrank an observed route', () => {
  const checkedAt = Date.parse('2026-07-12T00:00:00.000Z')
  const projection = buildModelCardProjection({
    arenaModels: [
      {
        modelId: 'z-ai/glm-5.2', label: 'GLM 5.2', providerKey: 'nvidia',
        status: 'up', pings: [{ code: '200', ms: 80, ts: checkedAt }],
      },
      {
        modelId: 'z-ai/glm5', label: 'Retired GLM 5', providerKey: 'nvidia',
        status: 'up', pings: [{ code: '410', ms: 40, ts: checkedAt + 1_000 }],
      },
    ],
    v1Models: [{ id: 'z-ai/glm-5.2' }, { id: 'z-ai/glm5' }],
    providerConfigs: [{ key: 'nvidia', enabled: true, hasKey: true }],
    registry: {
      providers: { nvidia: { status: 'active' } },
      models: [
        { id: 'z-ai/glm-5.2', provider: 'nvidia', status: 'active', tier: 80 },
        { id: 'z-ai/glm5', provider: 'nvidia', status: 'active', tier: 99 },
      ],
    },
    arenaSnapshot: {
      version: 1,
      models: {
        'z-ai/glm-5.2': {
          arena_score: 0.60, sources: ['test'], as_of: '2026-07-11T00:00:00Z',
        },
        'z-ai/glm5': {
          arena_score: 0.99, sources: ['test'], as_of: '2026-07-11T00:00:00Z',
        },
      },
    },
    generatedAt: '2026-07-12T00:01:00.000Z',
  })

  const retired = projection.models.find((model) => model.model_id === 'z-ai/glm5')
  assert.equal(retired.health.observed, true)
  assert.equal(retired.health.fresh, true)
  assert.equal(retired.health.state, 'unavailable')
  assert.equal(retired.policy_prior.registry_tier, 99)
  assert.equal(retired.benchmarks.dimensions.quality, 0.99)
  assert.deepEqual(projection.models.map((model) => model.model_id), [
    'z-ai/glm-5.2', 'z-ai/glm5',
  ])
})

test('projection never turns a synthetic catalogue default into benchmark evidence', () => {
  const projection = buildModelCardProjection({
    arenaModels: [{
      modelId: 'new-frontier-model', label: 'New Frontier', providerKey: 'nvidia',
      status: 'pending', pings: [], intell: 0.45, isEstimatedScore: true,
    }],
    v1Models: [{ id: 'new-frontier-model' }],
    providerConfigs: [{ key: 'nvidia', enabled: true, hasKey: true }],
    registry: { providers: {}, models: [] },
    arenaSnapshot: { version: 1, models: {} },
  })

  const card = projection.models[0]
  assert.equal(card.benchmarks.status, 'no_data')
  assert.equal(card.benchmarks.catalogue_score, null)
  assert.equal(card.benchmarks.catalogue_prior_present, false)
  assert.ok(Object.values(card.benchmarks.dimensions).every((value) => value === null))
})

test('projection records catalogue prior presence without exposing a numeric score', () => {
  const projection = buildModelCardProjection({
    arenaModels: [{
      modelId: 'legacy-catalogue-model', label: 'Legacy Catalogue Model', providerKey: 'legacy',
      status: 'pending', pings: [], intell: 0.91, isEstimatedScore: false,
    }],
    v1Models: [{ id: 'legacy-catalogue-model' }],
    providerConfigs: [{ key: 'legacy', enabled: true, hasKey: true }],
    registry: { providers: {}, models: [] },
    arenaSnapshot: { version: 1, models: {} },
  })

  const card = projection.models[0]
  assert.equal(card.benchmarks.status, 'catalogue_only')
  assert.equal(card.benchmarks.catalogue_prior_present, true)
  assert.equal(card.benchmarks.catalogue_score, null)
  assert.equal(card.benchmarks.catalogue_score_label, null)
  assert.ok(Object.values(card.benchmarks.dimensions).every((value) => value === null))
  assert.equal(projection.benchmark_contract.catalogue_prior_excluded_from_scores, true)
})

test('pending offers sort ahead of unavailable offers without claiming they are healthy', () => {
  const projection = buildModelCardProjection({
    arenaModels: [
      { modelId: 'offline', label: 'Offline', providerKey: 'nvidia', status: 'down', pings: [] },
      { modelId: 'pending', label: 'Pending', providerKey: 'nvidia', status: 'pending', pings: [] },
      { modelId: 'healthy', label: 'Healthy', providerKey: 'nvidia', status: 'up', pings: [{ code: '200', ms: 50, ts: Date.now() }] },
    ],
    v1Models: [{ id: 'offline' }, { id: 'pending' }, { id: 'healthy' }],
    providerConfigs: [{ key: 'nvidia', enabled: true, hasKey: true }],
    registry: { providers: {}, models: [] },
    arenaSnapshot: { version: 1, models: {} },
  })

  assert.deepEqual(projection.models.map((model) => model.health.state), [
    'healthy', 'unverified', 'unavailable',
  ])
})

test('registry matching is provider-aware for duplicate model IDs', () => {
  const duplicateRegistry = {
    models: [
      {
        id: 'zai-org/glm-5.2',
        provider: 'baseten',
        status: 'suspended',
        tier: 92,
        free: false,
      },
      {
        id: 'zai-org/glm-5.2',
        provider: 'siliconflow',
        status: 'active',
        tier: 95,
        free: true,
      },
      {
        id: 'zai-org/glm-5.2',
        provider: 'nvidia',
        status: 'active',
        tier: 96,
        free: true,
      },
    ],
  }
  const projection = buildModelCardProjection({
    arenaModels: [
      {
        modelId: 'zai-org/glm-5.2', label: 'GLM via Baseten',
        providerKey: 'baseten', status: 'pending', intell: null,
      },
      {
        modelId: 'zai-org/glm-5.2', label: 'GLM via NVIDIA',
        providerKey: 'nvidia', status: 'pending', intell: null,
      },
    ],
    v1Models: [{ id: 'zai-org/glm-5.2' }],
    providerConfigs: [],
    registry: duplicateRegistry,
    arenaSnapshot: { version: 1, models: {} },
  })

  const baseten = projection.models.find((model) => model.provider_key === 'baseten')
  const nvidia = projection.models.find((model) => model.provider_key === 'nvidia')
  assert.equal(baseten.registry.provider, 'baseten')
  assert.equal(baseten.registry.status, 'suspended')
  assert.equal(baseten.registry.free, false)
  assert.equal(nvidia.registry.provider, 'nvidia')
  assert.equal(nvidia.policy_prior.registry_tier, 96)
})
