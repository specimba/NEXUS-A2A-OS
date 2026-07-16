'use strict'

let projection = {
  summary: {},
  models: [],
  benchmark_contract: { policy_prior_is_not_benchmark: true },
}
let allModels = []
let sortMode = 'recommended'
let frontierIntelligence = null
let clientManifest = null

// The primary is intentionally a client preference, not an availability
// declaration. It mirrors the locked exact GLM route excluded from the
// `nexus-resilient` fallback policy.
const NEXUS_LOCKED_PRIMARY = Object.freeze({
  routeId: 'glm-5.2',
  providerKey: 'nvidia',
  modelId: 'z-ai/glm-5.2',
})

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

async function fetchAll() {
  const loading = document.getElementById('tableLoading')
  if (loading) {
    loading.style.display = 'block'
    loading.textContent = 'Loading canonical model cards...'
  }
  try {
    const [response, frontierResponse, manifestResponse] = await Promise.all([
      fetch('/api/model-cards'),
      fetch('/api/frontier-intelligence').catch(() => null),
      fetch('/api/client-manifest').catch(() => null),
    ])
    if (!response.ok) throw new Error(`Model-card API returned HTTP ${response.status}`)
    projection = await response.json()
    frontierIntelligence = frontierResponse?.ok ? await frontierResponse.json() : null
    clientManifest = manifestResponse?.ok ? await manifestResponse.json() : null
    allModels = Array.isArray(projection.models) ? projection.models : []
    updateFrontierIntelligenceStatus()
    renderEvidenceRuntimeStatus()
    renderFrontierReviewQueue()
    updateKPIs()
    renderRoutePosture()
    populateFilters()
    renderMatrix()
    renderTable()
    // The dashboard can be embedded in a partially mounted operator surface.
    // A missing cosmetic timestamp must never discard a valid projection.
    setText('lastUpdate', new Date().toLocaleTimeString())
  } catch (error) {
    allModels = []
    clientManifest = null
    const tbody = document.getElementById('modelTbody')
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="10" class="empty-state">Projection unavailable: ${esc(error.message)}</td></tr>`
    }
    const summary = document.getElementById('tableSummary')
    if (summary) summary.textContent = 'The 7350 relay or canonical model-card projection is unavailable.'
  } finally {
    if (loading) loading.style.display = 'none'
  }
}

function benchmarkValue(model, dimension) {
  const value = model?.benchmarks?.dimensions?.[dimension]
  return Number.isFinite(value) ? Number(value) : null
}

function hasBenchmarkEvidence(model) {
  return model?.benchmarks?.status === 'evidence_backed'
    && Array.isArray(model?.benchmarks?.coverage)
    && model.benchmarks.coverage.length > 0
}

function getQualityTier(value) {
  if (value >= 0.85) return 'frontier'
  if (value >= 0.75) return 'strong'
  if (value >= 0.60) return 'capable'
  return 'basic'
}

function formatBenchmark(model, dimension) {
  const value = benchmarkValue(model, dimension)
  if (value !== null) {
    const cls = dimension === 'quality' ? getQualityTier(value) : 'capable'
    return `<span class="intell-score ${cls}">${(value * 100).toFixed(1)}%</span>`
  }
  if (dimension === 'quality') {
    const catalogueOnly = model?.benchmarks?.status === 'catalogue_only'
    const title = catalogueOnly
      ? 'A catalogue prior exists but is excluded from benchmark scores and ranking'
      : 'No current compatible benchmark evidence'
    const label = catalogueOnly
      ? '<span class="intell-estimated" title="Catalogue presence only; never a benchmark score">CATALOGUE ONLY</span>'
      : ''
    return `<span class="intell-unscored" title="${title}">UNSCORED</span>${label}`
  }
  return '<span style="color:var(--text-dim)">--</span>'
}

function formatEvidence(model) {
  const benchmarks = model?.benchmarks || {}
  if (benchmarks.status === 'evidence_backed') {
    const sources = Array.isArray(benchmarks.sources) ? benchmarks.sources : []
    const asOf = benchmarks.as_of ? String(benchmarks.as_of).slice(0, 10) : 'date unknown'
    const coverage = Array.isArray(benchmarks.coverage) ? benchmarks.coverage.join(', ') : ''
    const live = benchmarks.evidence_origin === 'runtime_overlay'
    const origin = live ? 'LIVE' : 'SNAPSHOT'
    const title = `${live ? 'Fresh runtime evidence sidecar' : 'Checked-in snapshot fallback'} · Coverage: ${coverage}`
    return `<span class="score-evidence verified" title="${esc(title)}">${esc(sources.slice(0, 3).join(', '))} · ${esc(asOf)} · ${origin}</span>`
  }
  if (benchmarks.status === 'catalogue_only') {
    return '<span class="score-evidence" title="A static catalogue value exists but has no source/date metadata">Catalogue only</span>'
  }
  return '<span class="score-evidence none">No benchmark evidence</span>'
}

function formatSecondaryBenchmarks(model) {
  const dimensions = ['reasoning', 'speed', 'cost_efficiency']
  const labels = { reasoning: 'Reason', speed: 'Speed', cost_efficiency: 'Cost' }
  return dimensions.map((dimension) => {
    const value = benchmarkValue(model, dimension)
    return `${labels[dimension]} ${value === null ? '--' : `${(value * 100).toFixed(1)}%`}`
  }).join(' · ')
}

function formatHealth(model) {
  const health = model?.health || {}
  const state = health.state || 'unknown'
  const config = {
    healthy: ['OBSERVED HEALTHY', 'healthy'],
    stale: ['STALE OBSERVATION', 'stale'],
    unverified: ['UNVERIFIED', 'unverified'],
    rate_limited: ['RATE LIMITED', 'rate_limited'],
    auth_required: ['AUTH REQUIRED', 'auth_required'],
    unavailable: ['UNAVAILABLE', 'unavailable'],
    excluded: ['EXCLUDED', 'excluded'],
    unknown: ['UNKNOWN', 'unknown'],
  }[state] || ['UNKNOWN', 'unknown']
  const latency = Number.isFinite(health.latency_ms) ? `${Math.round(health.latency_ms)}ms` : '--'
  const checked = health.last_checked_at ? String(health.last_checked_at).slice(0, 19).replace('T', ' ') : 'not probed'
  const seconds = Number.isFinite(health.age_seconds) ? Math.max(0, health.age_seconds) : null
  const age = seconds === null ? null
    : (seconds < 60 ? `${seconds}s`
      : (seconds < 3600 ? `${Math.floor(seconds / 60)}m` : `${(seconds / 3600).toFixed(1)}h`))
  const http = Number.isFinite(health.latest_http_code) ? ` · HTTP ${health.latest_http_code}` : ''
  return `<span class="status-pill ${config[1]}">${config[0]}</span><div class="metric-detail">${latency} · ${esc(checked)}${age ? ` · age ${age}` : ''}${http}</div>`
}

function formatRoute(model) {
  if (model?.routing?.cli_visible) {
    return `<span class="route-pill cli">CLI MODEL ID</span><div class="metric-detail">${esc(model.routing.cli_route_id)}</div>`
  }
  if (model?.routing?.state === 'excluded') return '<span class="route-pill excluded">EXCLUDED</span>'
  return '<span class="route-pill offer">OFFER ONLY</span>'
}

function formatContext(model) {
  const value = model?.registry?.context_tokens
  if (!Number.isFinite(value)) return model?.runtime?.context ? esc(model.runtime.context) : '--'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value % 1_000_000 ? 1 : 0)}M`
  if (value >= 1_000) return `${Math.round(value / 1_000)}k`
  return String(value)
}

function updateFrontierIntelligenceStatus() {
  const element = document.getElementById('frontierIntelligenceStatus')
  if (!element) return
  const status = frontierIntelligence
  if (!status) {
    element.textContent = 'Frontier discovery status unavailable until the controlled 7356 dashboard reload publishes its candidate-only endpoint.'
    return
  }
  const providers = Array.isArray(status.providers)
    ? status.providers.map((item) => `${item.provider} (${item.candidate_count})`).join(', ')
    : ''
  const policy = 'candidate-only; no automatic registration, routing, or probing.'
  if (status.state === 'fresh') {
    const coldStart = Number(status.baseline_established_count || 0)
    const baselineNote = coldStart ? ` ${coldStart} came from a newly established baseline.` : ''
    element.textContent = `Frontier discovery: ${status.candidate_count || 0} fresh candidate(s)${providers ? ` from ${providers}` : ''}; ${policy}${baselineNote}`
    return
  }
  if (status.state === 'stale') {
    element.textContent = `Frontier discovery: ${status.candidate_count || 0} stale candidate(s); rerun the bounded daily evidence job before review. ${policy}`
    return
  }
  if (status.state === 'absent') {
    element.textContent = `Frontier discovery has not produced a candidate delta yet. ${policy}`
    return
  }
  element.textContent = `Frontier discovery input was rejected as malformed or oversized. ${policy}`
}

function runtimeRefreshSummary() {
  const refresh = projection?.benchmark_contract?.runtime_refresh || {}
  const checked = refresh.generated_at ? String(refresh.generated_at).slice(0, 19).replace('T', ' ') : 'not recorded'
  const age = Number.isFinite(refresh.age_seconds)
    ? (refresh.age_seconds < 3600 ? `${Math.floor(refresh.age_seconds / 60)}m old` : `${(refresh.age_seconds / 3600).toFixed(1)}h old`)
    : null
  if (projection?.benchmark_contract?.evidence_mode === 'runtime_overlay_with_snapshot_fallback') {
    return `Live capability evidence sidecar accepted${checked !== 'not recorded' ? ` · ${checked}` : ''}${age ? ` · ${age}` : ''}.`
  }
  if (refresh.state === 'failed') {
    return `Runtime evidence refresh failed${checked !== 'not recorded' ? ` · ${checked}` : ''}${age ? ` · ${age}` : ''}; the last valid snapshot remains in force. No score was fabricated.`
  }
  if (refresh.state === 'succeeded') {
    return `Runtime refresh completed without an accepted capability overlay${checked !== 'not recorded' ? ` · ${checked}` : ''}; snapshot evidence remains in force.`
  }
  if (refresh.state === 'invalid') return 'Runtime evidence status was rejected as malformed; snapshot evidence remains in force.'
  return 'No fresh runtime capability sidecar is available; snapshot evidence remains in force.'
}

function renderEvidenceRuntimeStatus() {
  const element = document.getElementById('evidenceRuntimeStatus')
  if (element) element.textContent = runtimeRefreshSummary()
}

function renderFrontierReviewQueue() {
  const element = document.getElementById('frontierReviewQueue')
  if (!element) return
  element.replaceChildren()

  const queue = frontierIntelligence?.review_queue
  const items = Array.isArray(queue?.items) ? queue.items : []
  if (!frontierIntelligence || !items.length) {
    element.textContent = 'Operator review queue: no candidate is ready for review.'
    return
  }

  const heading = document.createElement('div')
  heading.style.color = 'var(--text-muted)'
  heading.textContent = `Operator review queue: ${queue.total_candidates || items.length} candidate(s), all awaiting explicit review. This panel cannot promote, route, or probe.`
  element.appendChild(heading)

  const list = document.createElement('ol')
  list.style.margin = '6px 0 0 18px'
  list.style.display = 'grid'
  list.style.gap = '4px'
  for (const candidate of items.slice(0, 8)) {
    const entry = document.createElement('li')
    const model = document.createElement('code')
    model.textContent = `${candidate.provider}/${candidate.model_id}`
    const state = document.createElement('span')
    state.style.marginLeft = '6px'
    state.textContent = `${candidate.discovery_class || 'catalogue_delta'} · ${candidate.review_state || 'awaiting_operator_review'} · ${candidate.evidence_state || 'catalogue_delta_only'}`
    entry.append(model, state)
    list.appendChild(entry)
  }
  element.appendChild(list)

  const tail = document.createElement('div')
  tail.style.marginTop = '5px'
  tail.textContent = queue.truncated
    ? `Showing the first ${items.length} bounded queue entries; no automatic action is available.`
    : 'Review gate: confirm entitlement and endpoint, run one explicit bounded probe, then attach benchmark evidence or retain UNSCORED.'
  element.appendChild(tail)
}

function routeCandidateRank(model) {
  const healthRank = 8 - (HEALTH_ORDER[model?.health?.state] ?? 8)
  const evidenceRank = hasBenchmarkEvidence(model) ? 1 : 0
  const quality = benchmarkValue(model, 'quality') ?? -1
  const context = Number.isFinite(model?.registry?.context_tokens) ? model.registry.context_tokens : 0
  return [healthRank, evidenceRank, quality, context]
}

function isBetterRouteCandidate(candidate, current) {
  const left = routeCandidateRank(candidate)
  const right = routeCandidateRank(current)
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] > right[index]
  }
  return String(candidate?.provider_key || '').localeCompare(String(current?.provider_key || '')) < 0
}

function canonicalCliRoutes() {
  const routes = new Map()
  for (const model of allModels) {
    if (!model?.routing?.cli_visible || model?.routing?.eligible === false) continue
    const routeId = String(model?.routing?.cli_route_id || '').trim()
    if (!routeId) continue
    const current = routes.get(routeId)
    if (!current || isBetterRouteCandidate(model, current)) routes.set(routeId, model)
  }
  return [...routes.values()].sort((left, right) => {
    const leftRank = routeCandidateRank(left)
    const rightRank = routeCandidateRank(right)
    for (let index = 0; index < leftRank.length; index += 1) {
      if (leftRank[index] !== rightRank[index]) return rightRank[index] - leftRank[index]
    }
    return left.label.localeCompare(right.label)
  })
}

function selectedPresentationMode() {
  const select = document.getElementById('presentationMode')
  return select?.value === 'offers' ? 'offers' : 'canonical'
}

function presentationModels() {
  return selectedPresentationMode() === 'offers' ? allModels : canonicalCliRoutes()
}

function primaryLockedRoute() {
  const candidates = allModels.filter((model) => model?.routing?.cli_route_id === NEXUS_LOCKED_PRIMARY.routeId)
  return candidates.find((model) => model.model_id === NEXUS_LOCKED_PRIMARY.modelId && model.provider_key === NEXUS_LOCKED_PRIMARY.providerKey)
    || candidates.find((model) => model.provider_key === NEXUS_LOCKED_PRIMARY.providerKey)
    || null
}

function freshLiveLead() {
  return canonicalCliRoutes()
    .filter((model) => model.health?.state === 'healthy')
    .sort((left, right) => {
      const leftLatency = Number.isFinite(left?.health?.latency_ms) ? left.health.latency_ms : Number.POSITIVE_INFINITY
      const rightLatency = Number.isFinite(right?.health?.latency_ms) ? right.health.latency_ms : Number.POSITIVE_INFINITY
      return leftLatency - rightLatency || left.label.localeCompare(right.label)
    })[0] || null
}

function evidenceQualityLeader() {
  return canonicalCliRoutes()
    .filter(hasBenchmarkEvidence)
    .filter((model) => benchmarkValue(model, 'quality') !== null)
    .sort((left, right) => {
      const qualityDelta = benchmarkValue(right, 'quality') - benchmarkValue(left, 'quality')
      if (qualityDelta) return qualityDelta
      return (benchmarkValue(right, 'code') ?? -1) - (benchmarkValue(left, 'code') ?? -1)
        || left.label.localeCompare(right.label)
    })[0] || null
}

function formatObservationDetail(model) {
  if (!model) return 'No route record is present in the current projection.'
  const health = model.health || {}
  const state = health.state || 'unverified'
  const parts = [model.provider_key || 'relay', state]
  if (Number.isFinite(health.latency_ms)) parts.push(`${Math.round(health.latency_ms)}ms`)
  if (Number.isFinite(health.latest_http_code)) parts.push(`HTTP ${health.latest_http_code}`)
  if (Number.isFinite(health.age_seconds)) {
    const seconds = Math.max(0, health.age_seconds)
    parts.push(seconds < 3600 ? `${Math.floor(seconds / 60)}m observed` : `${(seconds / 3600).toFixed(1)}h observed`)
  }
  return parts.join(' · ')
}

function manifestRecommendationCard() {
  const recommendation = clientManifest?.recommendation
  if (!recommendation?.id) return null
  const card = canonicalCliRoutes().find((model) => (
    model?.routing?.cli_route_id === recommendation.id
      && model?.provider_key === recommendation.provider
  )) || canonicalCliRoutes().find((model) => model?.routing?.cli_route_id === recommendation.id)
  return { recommendation, card }
}

function setText(id, value) {
  const element = document.getElementById(id)
  if (element) element.textContent = value
}

function renderRoutePosture() {
  const primary = primaryLockedRoute()
  setText('primaryRoute', primary ? `${primary.label} · ${primary.provider_key}` : 'No primary record')
  setText(
    'primaryRouteDetail',
    primary
      ? `${formatObservationDetail(primary)}. Locked client preference; not a health or fallback claim.`
      : 'The pinned GLM 5.2 route is absent from this projection; its configuration cannot be inferred here.',
  )

  const manifest = manifestRecommendationCard()
  const fallback = freshLiveLead()
  const live = manifest?.card || fallback
  setText('freshLiveLead', live ? live.label : 'No fresh route')
  if (manifest?.card) {
    const basis = Array.isArray(clientManifest?.contract?.selection_order)
      ? clientManifest.contract.selection_order.join(' → ')
      : 'manifest policy'
    setText(
      'freshLiveLeadDetail',
      `${formatObservationDetail(live)}. Client-manifest recommendation: ${basis}; not benchmark proof.`,
    )
  } else if (live) {
    setText(
      'freshLiveLeadDetail',
      `${formatObservationDetail(live)}. Manifest recommendation unavailable; lowest observed latency among fresh routes, not quality proof.`,
    )
  } else {
    setText('freshLiveLeadDetail', 'No current healthy canonical route is observed. Catalogue entries are not substituted.')
  }

  const quality = evidenceQualityLeader()
  setText('evidenceQualityLead', quality ? quality.label : 'No evidence-backed route')
  if (quality) {
    const score = benchmarkValue(quality, 'quality')
    const asOf = quality.benchmarks?.as_of ? String(quality.benchmarks.as_of).slice(0, 10) : 'date unknown'
    setText(
      'evidenceQualityLeadDetail',
      `${(score * 100).toFixed(1)}% quality · ${formatObservationDetail(quality)} · evidence ${asOf}. Quality does not prove availability.`,
    )
  } else {
    setText('evidenceQualityLeadDetail', 'No compatible quality benchmark is attached to a canonical route.')
  }
}

function updateKPIs() {
  const summary = projection.summary || {}
  const canonicalRoutes = canonicalCliRoutes()
  setText('kpiCliRoutes', canonicalRoutes.length || '--')
  setText('kpiRelayRoutes', summary.relay_route_ids ?? summary.cli_model_ids ?? '--')
  setText('kpiAutomaticRoutes', summary.automatic_route_ids ?? '--')
  setText('kpiOffers', summary.catalogue_offers ?? '--')
  setText('kpiHealthy', summary.observed_healthy ?? '--')
  setText('kpiUnverified', summary.health_unverified ?? '--')
  setText('kpiStale', summary.observed_stale ?? '--')
  setText('kpiEvidence', summary.evidence_backed_offers ?? '--')
  setText('kpiProviders', summary.configured_providers ?? '--')
  setText('kpiAuthProviders', summary.authenticated_providers ?? '--')

  const latencies = canonicalRoutes
    .filter((model) => model.health?.state === 'healthy')
    .map((model) => model.health?.latency_ms)
    .filter(Number.isFinite)
    .sort((a, b) => a - b)
  const median = latencies.length ? latencies[Math.floor(latencies.length / 2)] : null
  setText('kpiLatency', median === null ? '--' : `${Math.round(median)}ms`)
}

function renderMatrix() {
  const plot = document.getElementById('matrixPlot')
  const tooltip = document.getElementById('matrixTooltip')
  if (!plot || !tooltip) return
  plot.querySelectorAll('.matrix-model-dot').forEach((dot) => dot.remove())
  const displayModels = canonicalCliRoutes()
    .filter(hasBenchmarkEvidence)
    .filter((model) => benchmarkValue(model, 'quality') !== null)
    .slice(0, 80)
  const healthY = {
    healthy: 8,
    unverified: 48,
    stale: 28,
    rate_limited: 64,
    auth_required: 72,
    unavailable: 86,
    excluded: 94,
    unknown: 76,
  }

  displayModels.forEach((model) => {
    const dot = document.createElement('div')
    dot.className = `matrix-model-dot ${model.health.state || 'unknown'}`
    dot.style.left = `${5 + (benchmarkValue(model, 'quality') * 90)}%`
    dot.style.top = `${healthY[model.health.state] ?? 76}%`
    const context = model.registry?.context_tokens || 0
    const size = Math.max(8, Math.min(20, 8 + Math.log10(Math.max(context, 1)) * 2))
    dot.style.width = `${size}px`
    dot.style.height = `${size}px`
    dot.addEventListener('mouseenter', () => {
      tooltip.style.display = 'block'
      tooltip.innerHTML = `
        <strong>${esc(model.label)}</strong><br>
        Quality: ${formatBenchmark(model, 'quality')}<br>
        Code: ${formatBenchmark(model, 'code')} · SWE: ${formatBenchmark(model, 'swe')}<br>
        Health: ${esc(model.health.state)}<br>
        Route: ${esc(model.routing.cli_route_id || 'offer only')}<br>
        Provider: ${esc(model.provider_key)}
      `
    })
    dot.addEventListener('mousemove', (event) => {
      const rect = plot.getBoundingClientRect()
      tooltip.style.left = `${event.clientX - rect.left + 12}px`
      tooltip.style.top = `${event.clientY - rect.top - 12}px`
    })
    dot.addEventListener('mouseleave', () => { tooltip.style.display = 'none' })
    plot.appendChild(dot)
  })
}

function compareNullableDescending(a, b) {
  if (a === null && b === null) return 0
  if (a === null) return 1
  if (b === null) return -1
  return b - a
}

function getSortedModels(sourceModels = presentationModels()) {
  const models = [...sourceModels]
  if (sortMode === 'recommended') {
    return models.sort((left, right) => {
      const leftRank = routeCandidateRank(left)
      const rightRank = routeCandidateRank(right)
      for (let index = 0; index < leftRank.length; index += 1) {
        if (leftRank[index] !== rightRank[index]) return rightRank[index] - leftRank[index]
      }
      return left.label.localeCompare(right.label)
    })
  }
  return models.sort((a, b) => {
    if (['quality', 'code', 'swe', 'reasoning', 'speed', 'cost_efficiency'].includes(sortMode)) {
      return compareNullableDescending(benchmarkValue(a, sortMode), benchmarkValue(b, sortMode))
        || a.label.localeCompare(b.label)
    }
    if (sortMode === 'policy') {
      return compareNullableDescending(a.policy_prior?.registry_tier ?? null, b.policy_prior?.registry_tier ?? null)
        || a.label.localeCompare(b.label)
    }
    if (sortMode === 'health') {
      return (HEALTH_ORDER[a.health?.state] ?? 99) - (HEALTH_ORDER[b.health?.state] ?? 99)
        || a.label.localeCompare(b.label)
    }
    if (sortMode === 'latency') {
      return compareNullableDescending(
        Number.isFinite(a.health?.latency_ms) ? -a.health.latency_ms : null,
        Number.isFinite(b.health?.latency_ms) ? -b.health.latency_ms : null,
      ) || a.label.localeCompare(b.label)
    }
    if (sortMode === 'context') {
      return compareNullableDescending(a.registry?.context_tokens ?? null, b.registry?.context_tokens ?? null)
        || a.label.localeCompare(b.label)
    }
    if (sortMode === 'provider') return a.provider_key.localeCompare(b.provider_key) || a.label.localeCompare(b.label)
    return a.label.localeCompare(b.label)
  })
}

function renderTable() {
  const search = (document.getElementById('searchInput')?.value || '').toLowerCase()
  const provider = document.getElementById('providerFilter')?.value || ''
  const health = document.getElementById('statusFilter')?.value || ''
  const evidence = document.getElementById('evidenceFilter')?.value || ''
  const route = document.getElementById('routeFilter')?.value || ''
  const sortSelect = document.getElementById('sortMode')
  if (sortSelect) sortMode = sortSelect.value || 'recommended'

  const presentationMode = selectedPresentationMode()
  let filtered = getSortedModels()
  if (search) {
    filtered = filtered.filter((model) => [
      model.label,
      model.model_id,
      model.provider_key,
      model.routing?.cli_route_id,
      ...(model.registry?.roles || []),
      ...(model.registry?.lanes || []),
    ].some((value) => String(value || '').toLowerCase().includes(search)))
  }
  if (provider) filtered = filtered.filter((model) => model.provider_key === provider)
  if (health) filtered = filtered.filter((model) => model.health?.state === health)
  if (evidence) filtered = filtered.filter((model) => model.benchmarks?.status === evidence)
  if (route) filtered = filtered.filter((model) => model.routing?.state === route)

  const summary = projection.summary || {}
  const canonicalRoutes = canonicalCliRoutes()
  const evidenceMode = runtimeRefreshSummary()
  const viewTotal = presentationMode === 'canonical' ? canonicalRoutes.length : (summary.catalogue_offers ?? allModels.length)
  const viewLabel = presentationMode === 'canonical' ? 'canonical client routes' : 'provider offers'
  const variants = presentationMode === 'canonical'
    ? ` ${summary.catalogue_offers ?? allModels.length} provider offers remain available in Provider offers view.`
    : ` ${canonicalRoutes.length} canonical client routes are available in Canonical CLI routes view.`
  setText('tableSummary', `Showing ${filtered.length} of ${viewTotal} ${viewLabel} · ${summary.observed_healthy ?? 0} fresh · ${summary.observed_stale ?? 0} stale · ${summary.health_unverified ?? 0} unverified.${variants} Evidence: ${evidenceMode}`)

  const liveLead = freshLiveLead()
  const tbody = document.getElementById('modelTbody')
  if (!tbody) return
  tbody.innerHTML = filtered.map((model) => {
    const isFreshLead = liveLead && model.model_id === liveLead.model_id && model.provider_key === liveLead.provider_key
    const rawError = model.runtime?.last_error
    const errorText = typeof rawError === 'string'
      ? rawError
      : (rawError?.code || rawError?.message || '')
    const error = errorText
      ? `<span style="color:var(--danger);font-size:0.72rem">${esc(String(errorText).slice(0, 45))}</span>`
      : '--'
    const tier = Number.isFinite(model.policy_prior?.registry_tier)
      ? `<span class="policy-pill" title="Registry routing policy prior; not benchmark evidence">Policy ${model.policy_prior.registry_tier}</span>`
      : ''
    return `<tr>
      <td>${formatBenchmark(model, 'quality')}</td>
      <td>${formatBenchmark(model, 'code')}</td>
      <td>${formatBenchmark(model, 'swe')}</td>
      <td>${formatEvidence(model)}<div class="metric-detail">${formatSecondaryBenchmarks(model)}</div></td>
      <td>
        <div style="font-weight:600">${esc(model.label)}${isFreshLead ? '<span class="best-badge">Fresh latency lead</span>' : ''}${tier}</div>
        <div class="metric-detail mono">${esc(model.model_id)}</div>
      </td>
      <td>${formatRoute(model)}</td>
      <td>${formatHealth(model)}</td>
      <td>${formatContext(model)}</td>
      <td><span class="provider-tag">${esc(model.provider_key)}</span></td>
      <td>${error}</td>
    </tr>`
  }).join('')
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No model cards match the selected filters.</td></tr>'
  }
}

function populateFilters() {
  const providers = [...new Set(allModels.map((model) => model.provider_key))].sort()
  const options = providers.map((provider) => `<option value="${esc(provider)}">${esc(provider)}</option>`).join('')
  const select = document.getElementById('providerFilter')
  if (!select) return
  const selected = select.value
  select.innerHTML = '<option value="">All Providers</option>' + options
  if (providers.includes(selected)) select.value = selected
}

function setSort(mode) {
  sortMode = mode
  const select = document.getElementById('sortMode')
  if (select) select.value = mode
  renderTable()
}

function esc(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

setInterval(fetchAll, 30_000)
fetchAll()
