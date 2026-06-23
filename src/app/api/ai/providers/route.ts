import { NextRequest, NextResponse } from 'next/server'

// ── Cost Estimates & Capabilities (static data — no imports needed) ─────

const costEstimates: Record<string, { inputPer1k: number; outputPer1k: number; currency: string; note: string }> = {
  'z-ai': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — z-ai SDK' },
  'openrouter': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free models only' },
  'cerebras': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — CS-3 Wafer' },
  'groq': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — LPU Inference' },
  'mistral': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Experiment plan — 1B tok/mo' },
  'codestral': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — 30 RPM' },
  'fireworks': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: '$1 free credits — use sparingly' },
  'scaleway': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: '1M tokens one-time — EU hosted' },
  'dashscope': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: '1M free tokens per model' },
  'bitdeer': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Cloud GPU free tier' },
  'nvidia': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: '1K free credits' },
  'sambanova': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
  'siliconflow': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
  'opencode': { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
}

const capabilitiesMap: Record<string, { chat: boolean; vision: boolean; embedding: boolean; code: boolean; tools: boolean; completion: boolean }> = {
  'z-ai': { chat: true, vision: false, embedding: false, code: true, tools: true, completion: false },
  'openrouter': { chat: true, vision: true, embedding: false, code: true, tools: true, completion: false },
  'cerebras': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
  'groq': { chat: true, vision: false, embedding: false, code: true, tools: true, completion: false },
  'mistral': { chat: true, vision: false, embedding: true, code: true, tools: true, completion: false },
  'codestral': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
  'fireworks': { chat: true, vision: true, embedding: true, code: true, tools: false, completion: false },
  'scaleway': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
  'dashscope': { chat: true, vision: true, embedding: true, code: true, tools: true, completion: false },
  'bitdeer': { chat: true, vision: false, embedding: false, code: true, tools: true, completion: false },
  'nvidia': { chat: true, vision: false, embedding: true, code: true, tools: false, completion: false },
  'sambanova': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
  'siliconflow': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
  'opencode': { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
}

// ── Static mock providers ─────────────────────────────────────────────

const MOCK_PROVIDERS = [
  { provider: 'z-ai', label: 'z-ai SDK', isAvailable: true, activeModels: 1, totalModels: 1, health: 'healthy' as const, rateLimitRemaining: 40, avgLatencyMs: 12 },
  { provider: 'openrouter', label: 'OpenRouter Free', isAvailable: true, activeModels: 6, totalModels: 6, health: 'healthy' as const, rateLimitRemaining: 20, avgLatencyMs: 180 },
  { provider: 'cerebras', label: 'Cerebras Free', isAvailable: true, activeModels: 2, totalModels: 2, health: 'healthy' as const, rateLimitRemaining: 30, avgLatencyMs: 45 },
  { provider: 'groq', label: 'Groq Free (LPU)', isAvailable: true, activeModels: 3, totalModels: 3, health: 'healthy' as const, rateLimitRemaining: 30, avgLatencyMs: 38 },
  { provider: 'mistral', label: 'Mistral AI', isAvailable: true, activeModels: 2, totalModels: 2, health: 'degraded' as const, rateLimitRemaining: 15, avgLatencyMs: 320 },
  { provider: 'codestral', label: 'Codestral', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 30, avgLatencyMs: 0 },
  { provider: 'fireworks', label: 'Fireworks AI', isAvailable: true, activeModels: 2, totalModels: 2, health: 'healthy' as const, rateLimitRemaining: 10, avgLatencyMs: 95 },
  { provider: 'scaleway', label: 'Scaleway AI', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
  { provider: 'dashscope', label: 'Alibaba Cloud Free', isAvailable: false, activeModels: 0, totalModels: 8, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
  { provider: 'bitdeer', label: 'BitDeer AI', isAvailable: true, activeModels: 1, totalModels: 1, health: 'degraded' as const, rateLimitRemaining: 8, avgLatencyMs: 410 },
  { provider: 'nvidia', label: 'NVIDIA NIM Free', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
  { provider: 'sambanova', label: 'SambaNova Free', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
  { provider: 'siliconflow', label: 'SiliconFlow Free', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
  { provider: 'opencode', label: 'OpenCode', isAvailable: false, activeModels: 0, totalModels: 1, health: 'unknown' as const, rateLimitRemaining: 10, avgLatencyMs: 0 },
]

const MOCK_MODEL_ROUTES = [
  { id: 'glm-5-2-zai', tier: 'reasoning', displayName: 'GLM-5.2', actualModel: 'z-ai/glm-5.2', provider: 'z-ai', providerLabel: 'z-ai SDK', isFree: true, health: 'healthy' },
  { id: 'deepseek-r1-free', tier: 'reasoning', displayName: 'DeepSeek R1 Free', actualModel: 'openrouter/deepseek/deepseek-r1:free', provider: 'openrouter', providerLabel: 'OpenRouter Free', isFree: true, health: 'healthy' },
  { id: 'qwen3-coder', tier: 'reasoning', displayName: 'Qwen3 Coder', actualModel: 'openrouter/qwen/qwen3-coder:free', provider: 'openrouter', providerLabel: 'OpenRouter Free', isFree: true, health: 'healthy' },
  { id: 'llama4-maverick', tier: 'balanced', displayName: 'Llama 4 Maverick', actualModel: 'openrouter/meta-llama/llama-4-maverick:free', provider: 'openrouter', providerLabel: 'OpenRouter Free', isFree: true, health: 'healthy' },
  { id: 'gemma-3-27b', tier: 'balanced', displayName: 'Gemma 3 27B', actualModel: 'openrouter/google/gemma-3-27b-it:free', provider: 'openrouter', providerLabel: 'OpenRouter Free', isFree: true, health: 'healthy' },
  { id: 'mistral-small', tier: 'balanced', displayName: 'Mistral Small', actualModel: 'mistral/mistral-small-latest', provider: 'mistral', providerLabel: 'Mistral AI', isFree: true, health: 'degraded' },
  { id: 'llama3.3-70b', tier: 'balanced', displayName: 'Llama 3.3 70B', actualModel: 'cerebras/llama-3.3-70b', provider: 'cerebras', providerLabel: 'Cerebras Free', isFree: true, health: 'healthy' },
  { id: 'qwen3-8b-cerebras', tier: 'fast', displayName: 'Qwen3 8B', actualModel: 'cerebras/qwen3-8b', provider: 'cerebras', providerLabel: 'Cerebras Free', isFree: true, health: 'healthy' },
  { id: 'llama3.1-8b-groq', tier: 'fast', displayName: 'Llama 3.1 8B', actualModel: 'groq/llama-3.1-8b-instant', provider: 'groq', providerLabel: 'Groq Free (LPU)', isFree: true, health: 'healthy' },
  { id: 'mixtral-8x7b-groq', tier: 'fast', displayName: 'Mixtral 8x7B', actualModel: 'groq/mixtral-8x7b-32768', provider: 'groq', providerLabel: 'Groq Free (LPU)', isFree: true, health: 'healthy' },
  { id: 'gemma2-9b-groq', tier: 'fast', displayName: 'Gemma 2 9B', actualModel: 'groq/gemma2-9b-it', provider: 'groq', providerLabel: 'Groq Free (LPU)', isFree: true, health: 'healthy' },
  { id: 'fireworks-llama3.1', tier: 'balanced', displayName: 'Llama 3.1 70B', actualModel: 'fireworks/accounts/fireworks/models/llama-v3p1-70b-instruct', provider: 'fireworks', providerLabel: 'Fireworks AI', isFree: true, health: 'healthy' },
  { id: 'fireworks-qwen2.5', tier: 'fast', displayName: 'Qwen 2.5 72B', actualModel: 'fireworks/accounts/fireworks/models/qwen2p5-72b-instruct', provider: 'fireworks', providerLabel: 'Fireworks AI', isFree: true, health: 'healthy' },
  { id: 'bitdeer-deepseek', tier: 'reasoning', displayName: 'DeepSeek V3', actualModel: 'bitdeer/deepseek-v3', provider: 'bitdeer', providerLabel: 'BitDeer AI', isFree: true, health: 'degraded' },
]

// ── GET handler ───────────────────────────────────────────────────────

export async function GET() {
  const providers = MOCK_PROVIDERS.map(p => ({
    ...p,
    models: MOCK_MODEL_ROUTES.filter(m => m.provider === p.provider),
    keyStatus: {
      totalKeys: p.isAvailable ? 1 : 0,
      healthyKeys: p.isAvailable ? 1 : 0,
      hasAvailableKey: p.isAvailable,
      activeKeyMasked: p.isAvailable ? `${p.provider}-***` : null,
    },
    rateLimits: {
      rpm: p.rateLimitRemaining,
      rpd: p.rateLimitRemaining * 50,
      remaining: { rpm: p.rateLimitRemaining, rpd: p.rateLimitRemaining * 50 },
      isCooldown: false,
      cooldownRemainingMs: 0,
      description: `${p.label} rate limits`,
    },
    costEstimate: costEstimates[p.provider] || { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Unknown' },
    capabilities: capabilitiesMap[p.provider] || { chat: true, vision: false, embedding: false, code: false, tools: false, completion: false },
  }))

  const tiers = {
    reasoning: MOCK_MODEL_ROUTES.filter(r => r.tier === 'reasoning').map(r => r.id),
    balanced: MOCK_MODEL_ROUTES.filter(r => r.tier === 'balanced').map(r => r.id),
    fast: MOCK_MODEL_ROUTES.filter(r => r.tier === 'fast').map(r => r.id),
    free: MOCK_MODEL_ROUTES.filter(r => r.tier === 'free').map(r => r.id),
  }

  const healthyModels = MOCK_MODEL_ROUTES.filter(r => r.health === 'healthy').length
  const availableProviders = providers.filter(p => p.isAvailable).length

  return NextResponse.json({
    providers,
    modelRoutes: MOCK_MODEL_ROUTES,
    tiers,
    summary: {
      totalProviders: providers.length,
      availableProviders,
      totalModels: MOCK_MODEL_ROUTES.length,
      healthyModels,
    },
  })
}

// ── POST handler (simulated health check) ─────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider } = body as { provider: string }

    if (!provider) {
      return NextResponse.json({ error: 'Missing required field: provider' }, { status: 400 })
    }

    const providerInfo = MOCK_PROVIDERS.find(p => p.provider === provider)
    if (!providerInfo) {
      return NextResponse.json({ error: `Unknown provider: ${provider}` }, { status: 404 })
    }

    return NextResponse.json({
      provider,
      isAvailable: providerInfo.isAvailable,
      latencyMs: providerInfo.avgLatencyMs || Math.floor(Math.random() * 300) + 50,
      testedModel: MOCK_MODEL_ROUTES.find(m => m.provider === provider)?.actualModel || 'unknown',
      health: providerInfo.health,
      checkedAt: new Date().toISOString(),
    })
  } catch {
    return NextResponse.json({ error: 'Health check failed' }, { status: 500 })
  }
}
