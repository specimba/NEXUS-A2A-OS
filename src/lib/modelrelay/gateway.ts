/**
 * ModelRelay Gateway — In-memory state management for provider health,
 * quota tracking, and dynamic routing. Server-side only.
 */

import {
  PROVIDERS,
  MODELS,
  ROUTING_STRATEGIES,
  DEFAULT_STRATEGY,
  INTENT_KEYWORDS,
  FALLBACK_CHAINS,
  CIRCUIT_BREAKER_THRESHOLD,
  CIRCUIT_BREAKER_COOLDOWN,
  LATENCY_SAMPLE_SIZE,
  type ProviderHealth,
  type QuotaInfo,
  type GatewayStats,
  type RouteResult,
  type ModelInfo,
  type IntentCategory,
} from './config'

// ─── In-Memory State ──────────────────────────────────────────────────────

const providerHealth: Map<string, ProviderHealth> = new Map()
const providerQuotas: Map<string, QuotaInfo> = new Map()
const stats: GatewayStats = {
  totalRequests: 0,
  successfulRequests: 0,
  failedRequests: 0,
  totalTokens: 0,
  totalCost: 0,
  startTime: Date.now(),
  requestsPerMinute: 0,
}

// Initialize health and quotas from config
function initializeState() {
  for (const [pid, cfg] of Object.entries(PROVIDERS)) {
    providerHealth.set(pid, {
      providerId: pid,
      state: cfg.status,
      latencyMs: cfg.latencyMs,
      latencyHistory: [cfg.latencyMs],
      failureCount: 0,
      consecutiveFailures: 0,
      lastSuccess: null,
      lastFailure: null,
      lastCheck: null,
      cooldownUntil: null,
    })

    const quotaType = cfg.quotaType
    let remaining = -1
    if (typeof cfg.quotaRemaining === 'number') {
      remaining = cfg.quotaRemaining
    }

    providerQuotas.set(pid, {
      providerId: pid,
      quotaType,
      remaining,
      remainingStr: typeof cfg.quotaRemaining === 'number' ? String(cfg.quotaRemaining) : String(cfg.quotaRemaining),
      isExhausted: remaining === 0,
      dailyLimit: null,
      dailyUsed: 0,
    })
  }
}

initializeState()

// ─── Intent Classification ────────────────────────────────────────────────

function classifyIntent(prompt: string): IntentCategory {
  const text = prompt.toLowerCase()
  const scores: Record<IntentCategory, number> = {
    code: 0, reasoning: 0, research: 0, speed: 0, general: 0, security: 0,
  }

  for (const [cat, keywords] of Object.entries(INTENT_KEYWORDS)) {
    for (const kw of keywords) {
      if (text.includes(kw)) {
        scores[cat as IntentCategory] += 1
      }
    }
  }

  let best: IntentCategory = 'general'
  let bestScore = 0
  for (const [cat, score] of Object.entries(scores)) {
    if (score > bestScore) {
      bestScore = score
      best = cat as IntentCategory
    }
  }

  return bestScore > 0 ? best : 'general'
}

// ─── Model Scoring ────────────────────────────────────────────────────────

function scoreModel(model: ModelInfo, intent: IntentCategory, stratConfig: typeof ROUTING_STRATEGIES[string], health: ProviderHealth | undefined): number {
  const latencyInv = 1000 / (model.latencyMsTypical + 1)
  const costInv = model.costPer1mInput + model.costPer1mOutput > 0
    ? 1 / (model.costPer1mInput + model.costPer1mOutput + 0.01)
    : 1000
  const quality = Math.min(model.tier / 100, 1.0)

  let score = latencyInv * stratConfig.latencyWeight + costInv * stratConfig.costWeight + quality * stratConfig.qualityWeight

  // Availability penalty
  if (health) {
    if (health.state === 'up') score *= 1.0
    else if (health.state === 'degraded') score *= 0.7
    else score *= 0.0 // down or cooldown
  }

  // Intent match bonus
  if (supportsIntent(model, intent)) {
    score += stratConfig.availabilityWeight
  }

  // Free/local bonus
  if (model.isFree) score *= 1.1
  if (model.isLocal) score *= 1.05

  return Math.round(score * 10000) / 10000
}

function supportsIntent(model: ModelInfo, intent: IntentCategory): boolean {
  switch (intent) {
    case 'code': return model.supportsFunctionCalling || model.tier >= 50
    case 'reasoning': return model.tier >= 70
    case 'speed': return model.isLocal || model.latencyMsTypical < 200
    case 'security': return model.tier >= 80
    default: return true
  }
}

// ─── Public API ───────────────────────────────────────────────────────────

export function routeRequest(prompt: string, strategy: string = DEFAULT_STRATEGY): RouteResult {
  stats.totalRequests++

  const intent = classifyIntent(prompt)
  const stratConfig = ROUTING_STRATEGIES[strategy] || ROUTING_STRATEGIES[DEFAULT_STRATEGY]

  // Score all models
  const scored = MODELS
    .map(model => ({
      model,
      score: scoreModel(model, intent, stratConfig, providerHealth.get(model.provider)),
    }))
    .filter(entry => entry.score > 0)
    .sort((a, b) => b.score - a.score)

  if (scored.length === 0) {
    // Fallback
    const fallback = FALLBACK_CHAINS[intent] || FALLBACK_CHAINS.general
    return {
      requestId: `relay-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      primaryModel: fallback[0],
      fallbackChain: fallback.slice(1),
      provider: 'fallback',
      intent,
      strategy,
      score: 0,
      estimatedLatencyMs: 999,
      estimatedCost: 0,
      reasoning: 'No candidates available, using hard fallback',
    }
  }

  const best = scored[0]
  const fallbackChain = scored
    .slice(1, 5)
    .filter(e => e.model.provider !== best.model.provider)
    .map(e => e.model.modelId)

  // Add from domain mapping fallback
  const domainFallbacks = FALLBACK_CHAINS[intent] || []
  for (const fid of domainFallbacks) {
    if (!fallbackChain.includes(fid) && fid !== best.model.modelId) {
      fallbackChain.push(fid)
      if (fallbackChain.length >= 5) break
    }
  }

  const isFree = best.model.isFree
  const reasoning = [
    `Intent: ${intent}`,
    `Strategy: ${strategy}`,
    `Selected: ${best.model.modelId} (score=${best.score})`,
    `Latency: ~${best.model.latencyMsTypical}ms`,
    `Cost: $${(best.model.costPer1mInput + best.model.costPer1mOutput).toFixed(4)}/1M tokens`,
    `Candidates considered: ${scored.length}`,
    isFree ? 'Free tier' : '',
    best.model.isLocal ? 'Local model' : '',
  ].filter(Boolean).join(' | ')

  return {
    requestId: `relay-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    primaryModel: best.model.modelId,
    fallbackChain: fallbackChain.slice(0, 5),
    provider: best.model.provider,
    intent,
    strategy,
    score: best.score,
    estimatedLatencyMs: best.model.latencyMsTypical,
    estimatedCost: best.model.costPer1mInput + best.model.costPer1mOutput,
    reasoning,
  }
}

export function getGatewayStatus() {
  const uptimeSeconds = (Date.now() - stats.startTime) / 1000
  return {
    providers: getProviderStatusSummary(),
    quotas: getQuotaStatus(),
    statistics: {
      ...stats,
      requestsPerMinute: Math.round(stats.totalRequests / Math.max(1, uptimeSeconds / 60) * 100) / 100,
    },
    activeStrategy: DEFAULT_STRATEGY,
    uptimeSeconds: Math.round(uptimeSeconds),
    availableProviders: getAvailableProviders().length,
    totalModels: MODELS.length,
    freeModels: MODELS.filter(m => m.isFree).length,
  }
}

export function getProviderStatusSummary() {
  const result: Record<string, any> = {}
  for (const [pid, cfg] of Object.entries(PROVIDERS)) {
    const h = providerHealth.get(pid)
    result[pid] = {
      name: cfg.name,
      state: h?.state || 'unknown',
      latencyMs: h?.latencyHistory?.length ? Math.round(h.latencyHistory.reduce((a, b) => a + b, 0) / h.latencyHistory.length) : cfg.latencyMs,
      tier: cfg.tier,
      priority: cfg.priority,
      isFree: cfg.isFree,
      isLocal: cfg.isLocal,
      quotaType: cfg.quotaType,
      failureCount: h?.failureCount || 0,
      lastCheck: h?.lastCheck,
      modelCount: MODELS.filter(m => m.provider === pid).length,
    }
  }
  return result
}

export function getQuotaStatus() {
  const result: Record<string, any> = {}
  for (const [pid, cfg] of Object.entries(PROVIDERS)) {
    const q = providerQuotas.get(pid)
    result[pid] = {
      name: cfg.name,
      quotaType: q?.quotaType || cfg.quotaType,
      remaining: q?.remaining ?? -1,
      remainingStr: q?.remainingStr || String(cfg.quotaRemaining),
      isExhausted: q?.isExhausted || false,
      isAvailable: !q?.isExhausted,
      dailyLimit: q?.dailyLimit,
      dailyUsed: q?.dailyUsed || 0,
    }
  }
  return result
}

export function getAvailableProviders(): string[] {
  const available: string[] = []
  for (const [pid, h] of providerHealth.entries()) {
    if (h.state === 'up' || h.state === 'degraded') {
      if (h.state === 'cooldown' && h.cooldownUntil && Date.now() < h.cooldownUntil) continue
      const q = providerQuotas.get(pid)
      if (!q?.isExhausted) available.push(pid)
    }
  }
  return available
}

export function getAllProviders() {
  return Object.entries(PROVIDERS).map(([pid, cfg]) => ({
    id: pid,
    name: cfg.name,
    status: providerHealth.get(pid)?.state || cfg.status,
    tier: cfg.tier,
    priority: cfg.priority,
    isFree: cfg.isFree,
    isLocal: cfg.isLocal,
    quotaType: cfg.quotaType,
    modelCount: MODELS.filter(m => m.provider === pid).length,
  }))
}

export function getAllModels() {
  return MODELS.map(m => ({
    ...m,
    providerName: PROVIDERS[m.provider]?.name || m.provider,
    costPer1mTotal: m.costPer1mInput + m.costPer1mOutput,
    qualityScore: Math.min(m.tier / 100, 1.0),
  }))
}

export function healthCheck() {
  return {
    status: 'operational',
    timestamp: Date.now(),
    components: {
      providerManager: 'ok',
      quotaGuard: 'ok',
      router: 'ok',
      modelsRegistry: `${MODELS.length} models`,
    },
    providersAvailable: getAvailableProviders().length,
  }
}

export function recordSuccess(providerId: string, latencyMs: number) {
  const h = providerHealth.get(providerId)
  if (h) {
    h.state = 'up'
    h.consecutiveFailures = 0
    h.lastSuccess = Date.now()
    h.latencyMs = latencyMs
    h.latencyHistory.push(latencyMs)
    if (h.latencyHistory.length > LATENCY_SAMPLE_SIZE) h.latencyHistory.shift()
  }
  stats.successfulRequests++
}

export function recordFailure(providerId: string, error?: string) {
  const h = providerHealth.get(providerId)
  if (h) {
    h.consecutiveFailures++
    h.failureCount++
    h.lastFailure = Date.now()
    if (h.consecutiveFailures >= CIRCUIT_BREAKER_THRESHOLD) {
      h.state = 'cooldown'
      h.cooldownUntil = Date.now() + CIRCUIT_BREAKER_COOLDOWN * 1000
    } else if (h.state !== 'cooldown') {
      h.state = 'degraded'
    }
  }
  stats.failedRequests++
}

export function getRoutingStrategies() {
  return Object.entries(ROUTING_STRATEGIES).map(([id, cfg]) => ({
    id,
    ...cfg,
  }))
}

export function getFallbackChains() {
  return FALLBACK_CHAINS
}

export function getIntentKeywords() {
  return INTENT_KEYWORDS
}
