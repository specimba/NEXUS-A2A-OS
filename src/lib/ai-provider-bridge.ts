/**
 * AI Provider Bridge for NEXUS OS v3.0
 *
 * Transparent, honest model routing engine.
 * All models are labeled with their REAL names — no fake "Claude" naming.
 * Routes requests to the best available model based on tier, health, and latency.
 *
 * Providers:
 *   z-ai        → z-ai-web-dev-sdk (GLM-4.7)
 *   openrouter  → OpenRouter API with key rotation (free models)
 */

import ZAI from 'z-ai-web-dev-sdk'
import { getActiveKey, recordKeySuccess, recordKey429, recordKeyError } from './api-key-manager'
import { checkRateLimit, recordRequest, recordSuccess, recordError as recordRateLimitError } from './rate-limiter'

// ── Types ──────────────────────────────────────────────────────────────

export type ModelTier = 'reasoning' | 'balanced' | 'fast' | 'free'

export interface ModelRoute {
  id: string
  tier: ModelTier
  displayName: string
  actualModel: string
  provider: 'z-ai' | 'openrouter'
  providerLabel: string
  isFree: boolean
  rateLimitPerMin: number
  contextWindow: number
  capabilities: string[]
  health: 'healthy' | 'degraded' | 'down' | 'unknown'
  latencyMs: number
  totalCalls: number
  successRate: number
}

export interface ProviderStatus {
  provider: string
  label: string
  isAvailable: boolean
  activeModels: number
  totalModels: number
  health: 'healthy' | 'degraded' | 'down'
  rateLimitRemaining: number
  avgLatencyMs: number
}

export interface RouteRequestOptions {
  systemPrompt?: string
  maxTokens?: number
  temperature?: number
  preferModel?: string
}

export interface RouteRequestResult {
  model: ModelRoute
  response: string
  latencyMs: number
  optimized: boolean
}

export interface RequestOptimizationResult {
  optimized: boolean
  response?: string
  reason?: string
}

// ── Model Route Definitions (HONEST LABELING) ─────────────────────────

const MODEL_ROUTES: ModelRoute[] = [
  // ── Reasoning Tier ──
  {
    id: 'glm-4-7-nim',
    tier: 'reasoning',
    displayName: 'GLM-4.7 (NIM Free)',
    actualModel: 'z-ai/glm-4.7',
    provider: 'z-ai',
    providerLabel: 'z-ai SDK',
    isFree: true,
    rateLimitPerMin: 40,
    contextWindow: 128000,
    capabilities: ['code', 'reasoning', 'tools'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },
  {
    id: 'deepseek-r1-or',
    tier: 'reasoning',
    displayName: 'DeepSeek R1 (OR Free)',
    actualModel: 'deepseek/deepseek-r1-0528:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 164000,
    capabilities: ['code', 'reasoning', 'tools'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },

  // ── Balanced Tier ──
  {
    id: 'trinity-large-or',
    tier: 'balanced',
    displayName: 'Trinity Large (OR Free)',
    actualModel: 'arcee-ai/trinity-large-preview:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 128000,
    capabilities: ['code', 'reasoning', 'tools'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },
  {
    id: 'qwen3-coder-or',
    tier: 'balanced',
    displayName: 'Qwen3 Coder (OR Free)',
    actualModel: 'qwen/qwen3-coder:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 128000,
    capabilities: ['code', 'tools'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },

  // ── Fast Tier ──
  {
    id: 'step-3-5-flash-or',
    tier: 'fast',
    displayName: 'Step 3.5 Flash (OR Free)',
    actualModel: 'stepfun/step-3.5-flash:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 64000,
    capabilities: ['code'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },
  {
    id: 'gemma-4-26b-or',
    tier: 'fast',
    displayName: 'Gemma 4 26B (OR Free)',
    actualModel: 'google/gemma-4-26b-a4b-it:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 96000,
    capabilities: ['code', 'vision'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },

  // ── Free Tier ──
  {
    id: 'kimi-k2-or',
    tier: 'free',
    displayName: 'Kimi K2 (OR Free)',
    actualModel: 'moonshotai/kimi-k2:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 128000,
    capabilities: ['code', 'reasoning'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },
  {
    id: 'nemotron-or',
    tier: 'free',
    displayName: 'Nemotron (OR Free)',
    actualModel: 'nvidia/llama-3.1-nemotron-70b-instruct:free',
    provider: 'openrouter',
    providerLabel: 'OpenRouter Free',
    isFree: true,
    rateLimitPerMin: 20,
    contextWindow: 128000,
    capabilities: ['code', 'reasoning'],
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successRate: 100,
  },
]

// ── Runtime State ──────────────────────────────────────────────────────

const routeHealth: Map<string, {
  health: ModelRoute['health']
  latencyMs: number
  totalCalls: number
  successes: number
  failures: number
  lastSuccessAt: number | null
  lastFailureAt: number | null
  consecutiveFailures: number
}> = new Map()

// Initialize health tracking
for (const route of MODEL_ROUTES) {
  routeHealth.set(route.id, {
    health: 'unknown',
    latencyMs: 0,
    totalCalls: 0,
    successes: 0,
    failures: 0,
    lastSuccessAt: null,
    lastFailureAt: null,
    consecutiveFailures: 0,
  })
}

// ── z-ai SDK Singleton ────────────────────────────────────────────────

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

// ── Request Optimization ──────────────────────────────────────────────

/**
 * Check if a request can be handled locally without calling the LLM.
 * Patterns borrowed from free-claude-code optimization:
 * - Quota check probes → mock affirmative
 * - Title generation → simple default title
 * - Prefix detection → extract command prefix
 * - Suggestion mode → empty response
 * This saves API quota on trivial requests.
 */
export function getRequestOptimization(messages: { role: string; content: string }[]): RequestOptimizationResult {
  if (!messages || messages.length === 0) {
    return { optimized: false }
  }

  const lastMessage = messages[messages.length - 1]
  if (!lastMessage?.content) {
    return { optimized: false }
  }

  const content = lastMessage.content.trim().toLowerCase()

  // Quota check probes — tools often ping with these
  if (
    content.includes('quota check') ||
    content.includes('check quota') ||
    content.includes('api quota') ||
    content === 'ping' ||
    content === 'health' ||
    content === 'status'
  ) {
    return {
      optimized: true,
      response: 'Quota check passed. All providers operational.',
      reason: 'quota_probe',
    }
  }

  // Title generation — short requests for conversation title
  if (
    content.includes('generate a title') ||
    content.includes('title for this conversation') ||
    content.includes('summarize in a short title')
  ) {
    return {
      optimized: true,
      response: 'Conversation',
      reason: 'title_generation',
    }
  }

  // Suggestion mode — empty/whitespace-only content or explicit suggestion request
  if (
    content === '' ||
    content === 'suggest' ||
    content === 'suggestions' ||
    content === 'auto-complete'
  ) {
    return {
      optimized: true,
      response: '',
      reason: 'suggestion_mode',
    }
  }

  // Prefix detection — command-style inputs starting with /
  if (content.startsWith('/') && content.split(' ').length <= 2) {
    const prefix = content.split(' ')[0]
    return {
      optimized: true,
      response: `Command prefix detected: ${prefix}`,
      reason: 'prefix_detection',
    }
  }

  return { optimized: false }
}

// ── Health Scoring ─────────────────────────────────────────────────────

function computeHealth(routeId: string): ModelRoute['health'] {
  const info = routeHealth.get(routeId)
  if (!info || info.totalCalls === 0) return 'unknown'

  const successRate = (info.successes / info.totalCalls) * 100

  if (info.consecutiveFailures >= 5) return 'down'
  if (successRate < 50 || info.consecutiveFailures >= 3) return 'degraded'
  return 'healthy'
}

function getEffectiveRoute(route: ModelRoute): ModelRoute {
  const info = routeHealth.get(route.id)
  if (!info) return route

  const totalCalls = info.totalCalls
  const successRate = totalCalls > 0 ? Math.round((info.successes / totalCalls) * 100) : 100

  return {
    ...route,
    health: computeHealth(route.id),
    latencyMs: info.latencyMs > 0 ? Math.round(info.latencyMs) : route.latencyMs,
    totalCalls,
    successRate,
  }
}

// ── Model Selection ───────────────────────────────────────────────────

/**
 * Score a model route for selection priority.
 * Lower score = higher priority.
 */
function scoreRoute(route: ModelRoute): number {
  let score = 0

  // Health penalty
  switch (route.health) {
    case 'down': score += 10000; break
    case 'degraded': score += 500; break
    case 'unknown': score += 100; break
    case 'healthy': score += 0; break
  }

  // Latency penalty (higher = worse)
  if (route.latencyMs > 0) {
    score += route.latencyMs / 100
  }

  // Success rate bonus (lower score for higher success rate)
  score -= route.successRate * 0.5

  // Slight preference for z-ai (more reliable, no key needed)
  if (route.provider === 'z-ai') {
    score -= 10
  }

  return score
}

/**
 * Get the best available model for a given tier.
 * Considers health, latency, and success rate.
 */
export function getModelForTier(tier: ModelTier): ModelRoute {
  const tierRoutes = MODEL_ROUTES.filter(r => r.tier === tier)
  if (tierRoutes.length === 0) {
    // Fallback to any available route
    return getBestAvailable()
  }

  const effectiveRoutes = tierRoutes.map(getEffectiveRoute)

  // Filter out down routes
  const availableRoutes = effectiveRoutes.filter(r => r.health !== 'down')

  // If all are down, try them anyway (health may be stale)
  const candidates = availableRoutes.length > 0 ? availableRoutes : effectiveRoutes

  // Sort by score (best first)
  candidates.sort((a, b) => scoreRoute(a) - scoreRoute(b))

  return candidates[0]
}

/**
 * Get the overall best available model across all tiers.
 */
function getBestAvailable(): ModelRoute {
  const allRoutes = MODEL_ROUTES.map(getEffectiveRoute)
  const available = allRoutes.filter(r => r.health !== 'down')
  const candidates = available.length > 0 ? available : allRoutes
  candidates.sort((a, b) => scoreRoute(a) - scoreRoute(b))
  return candidates[0]
}

// ── OpenRouter API Call ───────────────────────────────────────────────

async function callOpenRouter(
  model: string,
  messages: { role: string; content: string }[],
  options: RouteRequestOptions = {}
): Promise<string> {
  const apiKey = getActiveKey('openrouter')
  if (!apiKey) {
    throw new Error('No OpenRouter API key available. Configure OPENROUTER_API_KEY environment variable.')
  }

  // Check rate limit before making request
  const rateCheck = checkRateLimit('openrouter', '/chat/completions')
  if (!rateCheck.allowed && !rateCheck.isDedup) {
    throw new Error(`OpenRouter rate limited. Retry after ${Math.ceil(rateCheck.retryAfterMs / 1000)}s.`)
  }

  const systemMsg = options.systemPrompt
    ? [{ role: 'system' as const, content: options.systemPrompt }]
    : []

  const apiMessages = [
    ...systemMsg,
    ...messages.map(m => ({
      role: m.role === 'assistant' ? 'assistant' as const : 'user' as const,
      content: m.content,
    })),
  ]

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://nexus-os.dev',
      'X-Title': 'NEXUS OS v3.0',
    },
    body: JSON.stringify({
      model,
      messages: apiMessages,
      max_tokens: options.maxTokens ?? 4096,
      temperature: options.temperature ?? 0.7,
    }),
  })

  if (response.status === 429) {
    const retryAfter = parseInt(response.headers.get('retry-after') ?? '60', 10)
    recordKey429('openrouter', retryAfter)
    recordRateLimitError('openrouter', '429 Too Many Requests')
    throw new Error(`OpenRouter rate limited (429). Retry after ${retryAfter}s.`)
  }

  if (response.status === 401 || response.status === 403) {
    recordKeyError('openrouter', `${response.status} Auth Error`)
    throw new Error(`OpenRouter auth error (${response.status}). Check API key.`)
  }

  if (!response.ok) {
    const errorBody = await response.text().catch(() => 'Unknown error')
    recordKeyError('openrouter', `${response.status}: ${errorBody.slice(0, 200)}`)
    recordRateLimitError('openrouter', `${response.status}: ${errorBody.slice(0, 100)}`)
    throw new Error(`OpenRouter API error (${response.status}): ${errorBody.slice(0, 200)}`)
  }

  const data = await response.json()
  const content = data.choices?.[0]?.message?.content

  if (!content) {
    throw new Error('Empty response from OpenRouter')
  }

  // Record success
  recordKeySuccess('openrouter')
  recordSuccess('openrouter')
  recordRequest('openrouter', '/chat/completions', undefined, data)

  return content
}

// ── z-ai SDK Call ─────────────────────────────────────────────────────

async function callZAI(
  messages: { role: string; content: string }[],
  options: RouteRequestOptions = {}
): Promise<string> {
  const zai = await getZAI()

  const systemMsg = options.systemPrompt
    ? [{ role: 'assistant' as const, content: options.systemPrompt }]
    : []

  const apiMessages = [
    ...systemMsg,
    ...messages.map(m => ({
      role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
      content: m.content,
    })),
  ]

  const completion = await zai.chat.completions.create({
    messages: apiMessages,
    thinking: { type: 'disabled' },
  })

  const content = completion.choices?.[0]?.message?.content

  if (!content) {
    throw new Error('Empty response from z-ai SDK')
  }

  return content
}

// ── Main Routing Function ─────────────────────────────────────────────

/**
 * Route a chat request through the AI Provider Bridge.
 *
 * 1. Check request optimization (trivial requests handled locally)
 * 2. Select best model for the requested tier
 * 3. Execute the request via the appropriate provider
 * 4. Track health metrics after each request
 */
export async function routeRequest(
  tier: ModelTier,
  messages: { role: string; content: string }[],
  opts: RouteRequestOptions = {}
): Promise<RouteRequestResult> {
  // Step 1: Check request optimization
  const optimization = getRequestOptimization(messages)
  if (optimization.optimized && optimization.response !== undefined) {
    const model = getModelForTier(tier)
    return {
      model: getEffectiveRoute(model),
      response: optimization.response,
      latencyMs: 0,
      optimized: true,
    }
  }

  // Step 2: Select model (prefer specific model if requested)
  let model: ModelRoute
  if (opts.preferModel) {
    const preferred = MODEL_ROUTES.find(r => r.id === opts.preferModel || r.actualModel === opts.preferModel)
    model = preferred ? getEffectiveRoute(preferred) : getModelForTier(tier)
  } else {
    model = getModelForTier(tier)
  }

  // Step 3: Execute request
  const startTime = Date.now()
  let response: string

  try {
    if (model.provider === 'z-ai') {
      response = await callZAI(messages, opts)
    } else if (model.provider === 'openrouter') {
      response = await callOpenRouter(model.actualModel, messages, opts)
    } else {
      throw new Error(`Unknown provider: ${model.provider}`)
    }

    const latencyMs = Date.now() - startTime
    updateRouteHealth(model.id, true, latencyMs)

    return {
      model: getEffectiveRoute(model),
      response,
      latencyMs,
      optimized: false,
    }
  } catch (error) {
    const latencyMs = Date.now() - startTime
    updateRouteHealth(model.id, false, latencyMs)

    // Try fallback within the same tier
    const tierRoutes = MODEL_ROUTES.filter(
      r => r.tier === tier && r.id !== model.id && computeHealth(r.id) !== 'down'
    )

    if (tierRoutes.length > 0) {
      const fallbackRoutes = tierRoutes.map(getEffectiveRoute)
      fallbackRoutes.sort((a, b) => scoreRoute(a) - scoreRoute(b))
      const fallback = fallbackRoutes[0]
      const fbStart = Date.now()

      try {
        let fbResponse: string

        if (fallback.provider === 'z-ai') {
          fbResponse = await callZAI(messages, opts)
        } else {
          fbResponse = await callOpenRouter(fallback.actualModel, messages, opts)
        }

        const fbLatency = Date.now() - fbStart
        updateRouteHealth(fallback.id, true, fbLatency)

        return {
          model: getEffectiveRoute(fallback),
          response: fbResponse,
          latencyMs: fbLatency,
          optimized: false,
        }
      } catch {
        updateRouteHealth(fallback.id, false, Date.now() - fbStart)
        // Both primary and fallback failed
      }
    }

    // All routes failed — rethrow original error
    throw error instanceof Error ? error : new Error(String(error))
  }
}

// ── Health Update ──────────────────────────────────────────────────────

/**
 * Update the health metrics for a model route after a request.
 * Uses exponential moving average for latency to smooth out spikes.
 */
export function updateRouteHealth(routeId: string, success: boolean, latencyMs: number): void {
  const info = routeHealth.get(routeId)
  if (!info) return

  info.totalCalls++

  if (success) {
    info.successes++
    info.consecutiveFailures = 0
    info.lastSuccessAt = Date.now()

    // Exponential moving average for latency (alpha = 0.3)
    if (info.latencyMs === 0) {
      info.latencyMs = latencyMs
    } else {
      info.latencyMs = Math.round(0.3 * latencyMs + 0.7 * info.latencyMs)
    }
  } else {
    info.failures++
    info.consecutiveFailures++
    info.lastFailureAt = Date.now()
  }
}

// ── Query Functions ────────────────────────────────────────────────────

/**
 * Get all model routes with current health status.
 */
export function getAllRoutes(): ModelRoute[] {
  return MODEL_ROUTES.map(getEffectiveRoute)
}

/**
 * Get routes for a specific tier.
 */
export function getRoutesForTier(tier: ModelTier): ModelRoute[] {
  return MODEL_ROUTES.filter(r => r.tier === tier).map(getEffectiveRoute)
}

/**
 * Get a specific route by ID.
 */
export function getRouteById(routeId: string): ModelRoute | undefined {
  const route = MODEL_ROUTES.find(r => r.id === routeId)
  return route ? getEffectiveRoute(route) : undefined
}

/**
 * Get the status of a specific provider.
 */
export function getProviderStatus(provider: string): ProviderStatus {
  const providerRoutes = MODEL_ROUTES.filter(r => r.provider === provider)
  const effectiveRoutes = providerRoutes.map(getEffectiveRoute)

  const activeModels = effectiveRoutes.filter(r => r.health !== 'down').length
  const totalModels = effectiveRoutes.length

  const isAvailable = activeModels > 0

  // Determine overall provider health
  const healthyCount = effectiveRoutes.filter(r => r.health === 'healthy').length
  const degradedCount = effectiveRoutes.filter(r => r.health === 'degraded').length
  const downCount = effectiveRoutes.filter(r => r.health === 'down').length

  let health: ProviderStatus['health']
  if (downCount === totalModels) {
    health = 'down'
  } else if (degradedCount > 0 || (healthyCount > 0 && downCount > 0)) {
    health = 'degraded'
  } else if (healthyCount > 0) {
    health = 'healthy'
  } else {
    health = 'unknown' as ProviderStatus['health']
  }

  // Average latency across active models
  const activeLatencies = effectiveRoutes
    .filter(r => r.health !== 'down' && r.latencyMs > 0)
    .map(r => r.latencyMs)
  const avgLatencyMs = activeLatencies.length > 0
    ? Math.round(activeLatencies.reduce((sum, l) => sum + l, 0) / activeLatencies.length)
    : 0

  // Check rate limit remaining
  let rateLimitRemaining = 0
  try {
    const rlStatus = checkRateLimit(provider)
    rateLimitRemaining = rlStatus.remaining.rpm
  } catch {
    rateLimitRemaining = 0
  }

  const label = provider === 'z-ai'
    ? 'z-ai SDK (GLM-4.7)'
    : provider === 'openrouter'
      ? 'OpenRouter Free Tier'
      : provider

  return {
    provider,
    label,
    isAvailable,
    activeModels,
    totalModels,
    health,
    rateLimitRemaining,
    avgLatencyMs,
  }
}

/**
 * Get all provider statuses.
 */
export function getAllProviderStatuses(): ProviderStatus[] {
  const providerSet = new Set(MODEL_ROUTES.map(r => r.provider))
  const providers = Array.from(providerSet)
  return providers.map(getProviderStatus)
}

/**
 * Health check a specific provider by making a test request.
 */
export async function healthCheckProvider(provider: string): Promise<{
  provider: string
  isAvailable: boolean
  latencyMs: number
  testedModel: string
  error?: string
}> {
  const providerRoutes = MODEL_ROUTES.filter(r => r.provider === provider)
  if (providerRoutes.length === 0) {
    return {
      provider,
      isAvailable: false,
      latencyMs: 0,
      testedModel: 'none',
      error: `No routes found for provider: ${provider}`,
    }
  }

  // Pick the first non-down route for testing
  const testRoute = providerRoutes.find(r => computeHealth(r.id) !== 'down') ?? providerRoutes[0]
  const startTime = Date.now()

  try {
    const testMessages = [
      { role: 'user', content: 'Health check: respond with OK' },
    ]

    let response: string
    if (provider === 'z-ai') {
      response = await callZAI(testMessages, {
        systemPrompt: 'You are a health check endpoint. Respond with exactly: OK',
      })
    } else {
      response = await callOpenRouter(testRoute.actualModel, testMessages, {
        systemPrompt: 'You are a health check endpoint. Respond with exactly: OK',
        maxTokens: 10,
        temperature: 0,
      })
    }

    const latencyMs = Date.now() - startTime
    const isAvailable = response.length > 0

    updateRouteHealth(testRoute.id, isAvailable, latencyMs)

    return {
      provider,
      isAvailable,
      latencyMs,
      testedModel: testRoute.displayName,
    }
  } catch (error) {
    const latencyMs = Date.now() - startTime
    updateRouteHealth(testRoute.id, false, latencyMs)

    return {
      provider,
      isAvailable: false,
      latencyMs,
      testedModel: testRoute.displayName,
      error: error instanceof Error ? error.message : String(error),
    }
  }
}
