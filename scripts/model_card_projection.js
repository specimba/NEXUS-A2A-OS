'use strict'

const BENCHMARK_FIELDS = [
  ['quality', 'arena_score'],
  ['code', 'code_score'],
  ['reasoning', 'reasoning_score'],
  ['swe', 'swe_score'],
  ['speed', 'speed_score'],
  ['cost_efficiency', 'cost_efficiency_score'],
]

const HEALTH_FRESHNESS_MS = 35 * 60 * 1000

const HEALTH_ORDER = {
  healthy: 0,
  stale: 1,
  unverified: 2,
  rate_limited: 3,
  auth_required: 4,
  unavailable: 5,
  excluded: 6,
  unknown: 7,
}

function normalizeIdentifier(value) {
  return String(value || '').trim().toLowerCase()
}

function normalizeProviderKey(value) {
  return normalizeIdentifier(value).replace(/^openai-compatible:/, '')
}

function finiteScore(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 && number <= 1 ? number : null
}

function finiteNumber(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function parseContextTokens(value) {
  if (Number.isFinite(Number(value))) return Number(value)
  if (value === null || value === undefined || String(value).trim() === '') return null
  const match = String(value || '').trim().toLowerCase().match(/^(\d+(?:\.\d+)?)\s*([km])?$/)
  if (!match) return null
  const number = Number(match[1])
  if (match[2] === 'm') return Math.round(number * 1_000_000)
  if (match[2] === 'k') return Math.round(number * 1_000)
  return Math.round(number)
}

function buildRegistryIndex(registry) {
  const append = (map, key, model) => {
    if (!key) return
    const entries = map.get(key) || []
    entries.push(model)
    map.set(key, entries)
  }
  const exact = new Map()
  const aliases = new Map()
  for (const model of Array.isArray(registry?.models) ? registry.models : []) {
    const modelId = normalizeIdentifier(model?.id)
    append(exact, modelId, model)
  }
  for (const model of Array.isArray(registry?.models) ? registry.models : []) {
    for (const alias of Array.isArray(model?.aliases) ? model.aliases : []) {
      const key = normalizeIdentifier(alias)
      if (key && !exact.has(key)) append(aliases, key, model)
    }
  }
  return { exact, aliases }
}
function selectRegistryCandidate(candidates, providerKey) {
  if (!Array.isArray(candidates) || candidates.length === 0) return null
  const provider = normalizeProviderKey(providerKey)
  const providerMatch = candidates.find(
    (model) => normalizeProviderKey(model?.provider) === provider,
  )
  if (providerMatch) return providerMatch
  if (candidates.length === 1) return candidates[0]
  return candidates.find((model) => normalizeIdentifier(model?.status) === 'active') || candidates[0]
}


function resolveRegistryModel(row, index) {
  const candidates = [row?.modelId, row?.name, row?.id]
  for (const candidate of candidates) {
    const key = normalizeIdentifier(candidate)
    if (!key) continue
    if (index.exact.has(key)) {
      return selectRegistryCandidate(index.exact.get(key), row?.providerKey || row?.provider)
    }
    if (index.aliases.has(key)) {
      return selectRegistryCandidate(index.aliases.get(key), row?.providerKey || row?.provider)
    }
  }
  return null
}

function buildSnapshotIndex(snapshot) {
  const index = new Map()
  const models = snapshot?.version === 1 && snapshot?.models && typeof snapshot.models === 'object'
    ? snapshot.models
    : {}
  for (const [modelId, entry] of Object.entries(models)) {
    const key = normalizeIdentifier(modelId)
    if (key) index.set(key, entry)
  }
  return index
}

function candidateIdentifiers(row, registryModel) {
  const values = [row?.modelId, row?.id, registryModel?.id]
  if (Array.isArray(registryModel?.aliases)) values.push(...registryModel.aliases)
  if (row?.providerKey && row?.modelId) values.push(`${row.providerKey}/${row.modelId}`)
  return [...new Set(values.map(normalizeIdentifier).filter(Boolean))]
}

function resolveSnapshotEntry(row, registryModel, snapshotIndex) {
  for (const key of candidateIdentifiers(row, registryModel)) {
    if (snapshotIndex.has(key)) return snapshotIndex.get(key)
  }
  return null
}

function snapshotSources(entry) {
  if (Array.isArray(entry?.sources)) return entry.sources.map(String).filter(Boolean)
  if (entry?.sources && typeof entry.sources === 'object') return Object.keys(entry.sources)
  return []
}

function buildBenchmarks(row, registryModel, snapshotEntry, snapshot) {
  const dimensions = Object.fromEntries(BENCHMARK_FIELDS.map(([dimension]) => [dimension, null]))
  const sources = snapshotSources(snapshotEntry)
  const asOf = snapshotEntry?.as_of || snapshotEntry?.updated_at || snapshot?.generated_at || null
  const hasProvenance = sources.length > 0 && typeof asOf === 'string' && asOf.length > 0

  if (snapshotEntry && hasProvenance) {
    for (const [dimension, field] of BENCHMARK_FIELDS) {
      dimensions[dimension] = finiteScore(snapshotEntry[field])
    }
  }

  const coverage = BENCHMARK_FIELDS
    .map(([dimension]) => dimension)
    .filter((dimension) => dimensions[dimension] !== null)
  // A relay catalogue value is a routing/catalogue prior, not benchmark evidence.
  // Preserve only its presence so no consumer can accidentally rank or tier by it.
  const cataloguePriorPresent = row?.isEstimatedScore !== true && finiteScore(row?.intell) !== null
  const status = coverage.length > 0
    ? 'evidence_backed'
    : (cataloguePriorPresent ? 'catalogue_only' : 'no_data')

  return {
    status,
    dimensions,
    coverage,
    confidence: coverage.length > 0 ? String(snapshotEntry?.confidence || 'unknown') : 'no_data',
    sources: coverage.length > 0 ? sources : [],
    as_of: coverage.length > 0 ? asOf : null,
    evidence_origin: coverage.length > 0
      ? String(snapshotEntry?.evidence_origin || snapshot?.evidence_mode || 'snapshot_fallback')
      : 'none',
    catalogue_score: null,
    catalogue_score_label: null,
    catalogue_prior_present: cataloguePriorPresent,
    matched_registry_id: registryModel?.id || null,
  }
}

function buildHealth(row, nowMs = Date.now()) {
  const rawStatus = normalizeIdentifier(row?.status) || 'pending'
  const pings = Array.isArray(row?.pings) ? row.pings : []
  const pingRecords = pings
    .map((ping) => ({
      code: finiteNumber(ping?.code),
      latency: finiteNumber(ping?.ms),
      timestamp: finiteNumber(ping?.ts),
    }))
    .filter((ping) => ping.code !== null || ping.latency !== null || ping.timestamp !== null)
  const recentPing = [...pingRecords]
    .filter((ping) => ping.timestamp !== null)
    .sort((a, b) => b.timestamp - a.timestamp)[0] || null
  const latestCode = recentPing?.code
  const toTimestampMs = (value) => {
    const number = finiteNumber(value)
    if (number === null || number <= 0) return null
    return number < 1_000_000_000_000 ? number * 1_000 : number
  }
  const observationTimes = [
    toTimestampMs(row?.lastPingAt),
    toTimestampMs(row?.lastModelResponseAt),
    toTimestampMs(recentPing?.timestamp),
  ].filter((value) => value !== null)
  const timestampMs = observationTimes.length ? Math.max(...observationTimes) : null
  const observed = pingRecords.length > 0 || timestampMs !== null
  const ageMs = timestampMs === null ? null : Math.max(0, nowMs - timestampMs)
  const fresh = observed && ageMs !== null && ageMs <= HEALTH_FRESHNESS_MS
  const latestPingAtMs = toTimestampMs(recentPing?.timestamp)
  const lastModelResponseAtMs = toTimestampMs(row?.lastModelResponseAt)
  const latestPingFailed = latestCode !== undefined
    && latestCode !== null
    && latestPingAtMs !== null
    && fresh
    && (lastModelResponseAtMs === null || latestPingAtMs >= lastModelResponseAtMs)
    && !(latestCode >= 200 && latestCode < 300)
  const rateLimited = row?.isRateLimited === true
    || rawStatus === '429'
    || rawStatus === 'rate_limited'
    || (latestPingFailed && latestCode === 429)
  let state = 'unknown'
  if (rateLimited) state = 'rate_limited'
  else if (latestPingFailed && (latestCode === 401 || latestCode === 403)) state = 'auth_required'
  // A fresh failed canary is newer evidence than a stale raw `up` flag.  Keep
  // the failed offer out of healthy/top-route selection until a later 2xx
  // model response proves recovery.
  else if (latestPingFailed) state = 'unavailable'
  else if (rawStatus === 'up') state = fresh ? 'healthy' : (observed ? 'stale' : 'unverified')
  else if (rawStatus === 'pending' || (!observed && rawStatus === 'unknown')) state = 'unverified'
  else if (rawStatus === 'noauth' || rawStatus === 'unauthorized' || rawStatus === '401' || rawStatus === '403' || latestCode === 401 || latestCode === 403) state = 'auth_required'
  else if (rawStatus === 'down' || rawStatus === 'timeout' || rawStatus === 'error') state = 'unavailable'
  else if (rawStatus === 'banned' || rawStatus === 'disabled' || rawStatus === 'excluded') state = 'excluded'

  const successfulLatencies = pingRecords
    .filter((ping) => ping.latency !== null && (ping.code === null || (ping.code >= 200 && ping.code < 300)))
    .map((ping) => ping.latency)
  const derivedLatency = successfulLatencies.length
    ? successfulLatencies.reduce((sum, value) => sum + value, 0) / successfulLatencies.length
    : null
  return {
    state,
    raw_status: rawStatus,
    observed,
    fresh,
    latency_ms: finiteNumber(row?.avg) ?? derivedLatency,
    uptime_percent: finiteNumber(row?.uptime),
    verdict: row?.verdict || null,
    last_checked_at: timestampMs && timestampMs > 0 ? new Date(timestampMs).toISOString() : null,
    age_seconds: ageMs === null ? null : Math.floor(ageMs / 1_000),
    freshness_window_seconds: HEALTH_FRESHNESS_MS / 1_000,
    is_rate_limited: rateLimited,
    latest_http_code: latestCode ?? null,
  }
}

function boundedRuntimeRefresh(value) {
  const allowedStates = new Set(['succeeded', 'failed', 'absent', 'invalid'])
  const allowedStages = new Set(['succeeded', 'failed', 'skipped', 'unknown'])
  const raw = value && typeof value === 'object' ? value : {}
  const stage = (name) => allowedStages.has(raw?.stages?.[name]) ? raw.stages[name] : 'unknown'
  const age = finiteNumber(raw.age_seconds)
  return {
    state: allowedStates.has(raw.state) ? raw.state : 'absent',
    fresh: raw.fresh === true,
    generated_at: typeof raw.generated_at === 'string' ? raw.generated_at.slice(0, 64) : null,
    age_seconds: age !== null && age >= 0 ? Math.floor(age) : null,
    offline: raw.offline === true,
    stages: {
      catalog: stage('catalog'),
      evidence_ingest: stage('evidence_ingest'),
      client_manifest_sync: stage('client_manifest_sync'),
    },
    evidence_sidecar_accepted: raw.evidence_sidecar_accepted === true,
    candidate_delta_available: raw.candidate_delta_available === true,
  }
}

function buildRouteIndex(v1Models) {
  const routes = new Map()
  for (const model of Array.isArray(v1Models) ? v1Models : []) {
    const routeId = String(model?.id || '').trim()
    if (!routeId || routeId === 'auto-fastest') continue
    routes.set(normalizeIdentifier(routeId), routeId)
  }
  return routes
}
function summarizeRelayRoutes(v1Models) {
  const all = new Set()
  const automatic = new Set()
  for (const model of Array.isArray(v1Models) ? v1Models : []) {
    const routeId = String(model?.id || '').trim()
    if (!routeId) continue
    const normalized = normalizeIdentifier(routeId)
    all.add(normalized)
    if (normalized === 'auto-fastest') automatic.add(normalized)
  }
  return { all: all.size, automatic: automatic.size }
}

function resolveRouteId(row, registryModel, routes) {
  for (const candidate of candidateIdentifiers(row, registryModel)) {
    if (routes.has(candidate)) return routes.get(candidate)
  }
  return null
}

function compareCards(a, b) {
  const aRoute = a.routing.cli_visible ? 0 : 1
  const bRoute = b.routing.cli_visible ? 0 : 1
  if (aRoute !== bRoute) return aRoute - bRoute
  const health = (HEALTH_ORDER[a.health.state] ?? 99) - (HEALTH_ORDER[b.health.state] ?? 99)
  if (health !== 0) return health
  const aEvidence = a.benchmarks.status === 'evidence_backed' ? 0 : 1
  const bEvidence = b.benchmarks.status === 'evidence_backed' ? 0 : 1
  if (aEvidence !== bEvidence) return aEvidence - bEvidence
  const quality = (b.benchmarks.dimensions.quality ?? -1) - (a.benchmarks.dimensions.quality ?? -1)
  if (quality !== 0) return quality
  const policy = (b.policy_prior.registry_tier ?? -1) - (a.policy_prior.registry_tier ?? -1)
  if (policy !== 0) return policy
  return a.label.localeCompare(b.label)
}

function buildModelCardProjection({
  arenaModels = [],
  v1Models = [],
  providerConfigs = [],
  registry = {},
  arenaSnapshot = {},
  generatedAt = new Date().toISOString(),
} = {}) {
  const registryIndex = buildRegistryIndex(registry)
  const snapshotIndex = buildSnapshotIndex(arenaSnapshot)
  const routes = buildRouteIndex(v1Models)

  const relayRoutes = summarizeRelayRoutes(v1Models)
  const generatedAtMs = Date.parse(generatedAt)
  const projectionNowMs = Number.isFinite(generatedAtMs) ? generatedAtMs : Date.now()
  const models = (Array.isArray(arenaModels) ? arenaModels : []).map((row) => {
    const registryModel = resolveRegistryModel(row, registryIndex)
    const health = buildHealth(row, projectionNowMs)
    const routeId = resolveRouteId(row, registryModel, routes)
    const benchmarks = buildBenchmarks(
      row,
      registryModel,
      resolveSnapshotEntry(row, registryModel, snapshotIndex),
      arenaSnapshot,
    )
    const excluded = ['banned', 'disabled', 'excluded'].includes(health.raw_status)
    return {
      model_id: String(row?.modelId || row?.id || ''),
      label: String(row?.label || row?.modelId || row?.id || 'Unknown model'),
      provider_key: String(row?.providerKey || row?.provider || 'unknown'),
      catalogue: {
        state: 'listed',
        offer_index: finiteNumber(row?.idx),
        discovered: true,
      },
      routing: {
        cli_visible: routeId !== null,
        cli_route_id: routeId,
        eligible: !excluded,
        state: excluded ? 'excluded' : (routeId ? 'cli_visible' : 'offer_only'),
      },
      health,
      benchmarks,
      policy_prior: {
        registry_tier: finiteNumber(registryModel?.tier),
        label: registryModel?.tier == null ? 'none' : 'registry_policy_tier',
      },
      registry: {
        registered: registryModel !== null,
        id: registryModel?.id || null,
        provider: registryModel?.provider || null,
        status: registryModel?.status || null,
        context_tokens: finiteNumber(registryModel?.context) ?? parseContextTokens(row?.ctx),
        max_output_tokens: finiteNumber(registryModel?.maxOutput),
        free: typeof registryModel?.free === 'boolean' ? registryModel.free : null,
        capabilities: registryModel?.capabilities || {},
        roles: Array.isArray(registryModel?.roles) ? registryModel.roles : [],
        lanes: Array.isArray(registryModel?.lanes) ? registryModel.lanes : [],
      },
      runtime: {
        context: row?.ctx || null,
        last_error: row?.lastError || null,
        http_code: row?.httpCode ?? null,
      },
    }
  }).sort(compareCards)

  const configs = Array.isArray(providerConfigs) ? providerConfigs : []
  const summary = {
    catalogue_offers: models.length,
    cli_model_ids: routes.size,
    relay_route_ids: relayRoutes.all,
    automatic_route_ids: relayRoutes.automatic,
    cli_visible_offers: models.filter((model) => model.routing.cli_visible).length,
    observed_healthy: models.filter((model) => model.health.state === 'healthy').length,
    observed_stale: models.filter((model) => model.health.state === 'stale').length,
    health_unverified: models.filter((model) => model.health.state === 'unverified').length,
    unavailable: models.filter((model) => model.health.state === 'unavailable').length,
    rate_limited: models.filter((model) => model.health.state === 'rate_limited').length,
    evidence_backed_offers: models.filter((model) => model.benchmarks.status === 'evidence_backed').length,
    configured_providers: configs.filter((provider) => provider?.enabled !== false).length,
    authenticated_providers: configs.filter((provider) => provider?.enabled !== false && provider?.hasKey === true).length,
  }

  return {
    schema_version: 1,
    generated_at: generatedAt,
    health_contract: {
      freshness_window_seconds: HEALTH_FRESHNESS_MS / 1_000,
      stale_is_not_healthy: true,
    },
    benchmark_contract: {
      dimensions: BENCHMARK_FIELDS.map(([dimension]) => dimension),
      no_data: 'null',
      policy_prior_is_not_benchmark: true,
      catalogue_prior_excluded_from_scores: true,
      evidence_mode: String(arenaSnapshot?.evidence_mode || 'snapshot_fallback'),
      runtime_refresh: boundedRuntimeRefresh(arenaSnapshot?.runtime_refresh),
    },
    summary,
    models,
  }
}

module.exports = {
  BENCHMARK_FIELDS,
  buildHealth,
  buildModelCardProjection,
  normalizeIdentifier,
}
