import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { buildModelCardProjection } = require('../../scripts/model_card_projection.js')
const dashboard = require('../../scripts/serve_dashboard_7356.js')
const here = path.dirname(fileURLToPath(import.meta.url))
const repo = path.resolve(here, '..', '..')
const registry = JSON.parse(fs.readFileSync(path.join(repo, 'config', 'models.registry.json'), 'utf8'))
const freshOverlay = path.join(repo, 'tests', 'monitoring', 'fixtures', 'arena_runtime_scores_fresh.json')
const staleSourceOverlay = path.join(repo, 'tests', 'monitoring', 'fixtures', 'arena_runtime_scores_stale_source.json')
const NOW = Date.parse('2026-07-14T12:00:00.000Z')

function project(snapshot) {
  return buildModelCardProjection({
    arenaModels: [
      {
        modelId: 'z-ai/glm-5.2', label: 'GLM 5.2', providerKey: 'nvidia',
        status: 'pending', pings: [], intell: null, isEstimatedScore: true, ctx: '1M',
      },
      {
        modelId: 'minimaxai/minimax-m3', label: 'MiniMax M3', providerKey: 'nvidia',
        status: 'pending', pings: [], intell: null, isEstimatedScore: true, ctx: '1M',
      },
    ],
    v1Models: [{ id: 'z-ai/glm-5.2' }, { id: 'minimaxai/minimax-m3' }],
    providerConfigs: [{ key: 'nvidia', enabled: true, hasKey: true }],
    registry,
    arenaSnapshot: snapshot,
    generatedAt: '2026-07-14T12:00:00.000Z',
  })
}

test('fresh runtime capability evidence overrides static aliases without leaking source payloads', () => {
  const snapshot = dashboard.buildArenaSnapshot(registry, NOW, freshOverlay)
  assert.equal(snapshot.evidence_mode, 'runtime_overlay_with_snapshot_fallback')
  assert.equal(snapshot.runtime_refresh.state, 'absent')
  // The live sidecar is keyed by zai-org/GLM-5.2 while the relay uses the
  // provider alias z-ai/glm-5.2.  Explicit registry-family expansion is the
  // only permitted bridge between the two.
  assert.equal(snapshot.models['z-ai/glm-5.2'].arena_score, 0.91)

  const projection = project(snapshot)
  const glm = projection.models.find((model) => model.model_id === 'z-ai/glm-5.2')
  assert.equal(glm.benchmarks.dimensions.quality, 0.91)
  assert.equal(glm.benchmarks.dimensions.code, 0.89)
  assert.equal(glm.benchmarks.dimensions.reasoning, null)
  assert.equal(glm.benchmarks.dimensions.swe, null)
  assert.equal(glm.benchmarks.as_of, '2026-07-14T12:00:00+00:00')
  assert.equal(JSON.stringify(projection).includes('must-not-leak'), false)

  // A usage-only sidecar entry cannot displace capability-backed snapshot
  // evidence, even when it claims a higher arbitrary score.
  const minimax = projection.models.find((model) => model.model_id === 'minimaxai/minimax-m3')
  assert.equal(minimax.benchmarks.dimensions.quality, 0.6641)
})

test('stale or absent runtime evidence falls back to the checked-in snapshot', () => {
  const staleSourceSnapshot = dashboard.buildArenaSnapshot(registry, NOW, staleSourceOverlay)
  assert.equal(staleSourceSnapshot.models['z-ai/glm-5.2'].arena_score, 0.7161)

  const absentSidecarSnapshot = dashboard.buildArenaSnapshot(
    registry,
    NOW,
    path.join(repo, 'tests', 'monitoring', 'fixtures', 'does-not-exist.json'),
  )
  assert.equal(absentSidecarSnapshot.models['z-ai/glm-5.2'].arena_score, 0.7161)
})

test('runtime evidence reaches an exact free-route sibling but not a different release variant', () => {
  const stateDir = fs.mkdtempSync(path.join(process.env.TEMP || process.env.TMP || repo, 'nexus-arena-free-route-'))
  const overlayPath = path.join(stateDir, 'scores.json')
  try {
    fs.writeFileSync(overlayPath, JSON.stringify({
      version: 1,
      generated_at: '2026-07-14T12:00:00.000Z',
      models: {
        'vendor/deepseek-v4-flash': {
          arena_score: 0.91,
          confidence: 'medium',
          no_data: false,
          sources: {
            lmarena_elo: {
              normalized: 0.91,
              trust_tier: 'tier1',
              fetched_at: '2026-07-14T12:00:00.000Z',
              stale: false,
            },
          },
        },
      },
    }), 'utf8')
    const snapshot = dashboard.buildArenaSnapshot({
      models: [
        { id: 'vendor/deepseek-v4-flash', aliases: [] },
        { id: 'deepseek-v4-flash-free', aliases: [] },
        { id: 'deepseek-v4-flash-thinking', aliases: [] },
      ],
    }, NOW, overlayPath)

    assert.equal(snapshot.models['deepseek-v4-flash-free'].arena_score, 0.91)
    assert.equal(snapshot.models['deepseek-v4-flash-thinking'], undefined)
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true })
  }
})

test('frontier discovery status stays candidate-only and strips arbitrary source metadata', () => {
  const stateDir = fs.mkdtempSync(path.join(process.env.TEMP || process.env.TMP || repo, 'nexus-frontier-status-'))
  const candidatePath = path.join(stateDir, 'latest_candidates.json')
  try {
    fs.writeFileSync(candidatePath, JSON.stringify([
      {
        provider: 'nvidia',
        model_id: 'z-ai/glm-5.2',
        reason: 'baseline_established:missing',
        source_metadata: { raw_error: 'must-not-leak', api_key: 'must-not-leak' },
      },
      {
        provider: 'openrouter',
        model_id: 'example/frontier-free',
        reason: 'new_model',
      },
    ]), 'utf8')
    const now = Date.now()
    fs.utimesSync(candidatePath, now / 1000, now / 1000)
    const status = dashboard.readFrontierIntelligenceStatus(candidatePath, now)
    assert.equal(status.state, 'fresh')
    assert.equal(status.candidate_count, 2)
    assert.equal(status.baseline_established_count, 1)
    assert.deepEqual(status.providers, [
      { provider: 'nvidia', candidate_count: 1 },
      { provider: 'openrouter', candidate_count: 1 },
    ])
    assert.deepEqual(status.policy, {
      candidate_only: true,
      automatic_registration: false,
      automatic_routing: false,
      automatic_probing: false,
    })
    assert.equal(JSON.stringify(status).includes('must-not-leak'), false)
    assert.equal(JSON.stringify(status).includes('source_metadata'), false)
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true })
  }
})

test('runtime refresh status is bounded before it reaches the evidence contract', () => {
  const stateDir = fs.mkdtempSync(path.join(process.env.TEMP || process.env.TMP || repo, 'nexus-frontier-refresh-'))
  const overlayPath = path.join(stateDir, 'scores.json')
  const statusPath = path.join(stateDir, 'frontier_intelligence_status.json')
  try {
    fs.writeFileSync(statusPath, JSON.stringify({
      version: 1,
      generated_at: '2026-07-14T11:55:00.000Z',
      state: 'failed',
      offline: false,
      stages: { catalog: 'succeeded', evidence_ingest: 'failed', client_manifest_sync: 'skipped' },
      evidence_sidecar_accepted: false,
      candidate_delta_available: true,
      raw_error: 'must-not-leak',
    }), 'utf8')
    const status = dashboard.readRuntimeRefreshStatus(statusPath, NOW)
    assert.equal(status.state, 'failed')
    assert.equal(status.fresh, true)
    assert.equal(status.stages.evidence_ingest, 'failed')
    assert.equal(status.candidate_delta_available, true)
    assert.equal(JSON.stringify(status).includes('must-not-leak'), false)
    assert.equal(dashboard.runtimeStateRoot.endsWith(path.join('logs', 'runtime-state')), true)
    assert.equal(overlayPath.endsWith('scores.json'), true)
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true })
  }
})
