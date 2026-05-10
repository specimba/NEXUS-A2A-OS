import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/ai/providers
 *
 * Returns all AI providers with detailed status information.
 * Wraps the existing /api/providers endpoint with additional
 * capabilities, cost estimation, and connection test support.
 */
export async function GET() {
  try {
    // Fetch from the existing detailed providers API
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'
    const providersResponse = await fetch(`${baseUrl}/api/providers`, {
      cache: 'no-store',
    })

    if (!providersResponse.ok) {
      throw new Error(`Providers API returned ${providersResponse.status}`)
    }

    const data = await providersResponse.json()

    // Add cost estimation and capabilities info to each provider
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

    // Enhance providers with additional data
    const enhancedProviders = (data.providers || []).map((provider: Record<string, unknown>) => {
      const providerName = provider.provider as string
      return {
        ...provider,
        costEstimate: costEstimates[providerName] || { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Unknown' },
        capabilities: capabilitiesMap[providerName] || { chat: true, vision: false, embedding: false, code: false, tools: false, completion: false },
      }
    })

    return NextResponse.json({
      ...data,
      providers: enhancedProviders,
    })
  } catch (error) {
    console.error('AI Providers API error:', error)

    // Graceful fallback to mock data
    const mockProviders = [
      {
        provider: 'z-ai',
        label: 'z-ai SDK',
        isAvailable: true,
        activeModels: 1,
        totalModels: 1,
        health: 'healthy' as const,
        rateLimitRemaining: 40,
        avgLatencyMs: 0,
        models: [{ id: 'glm-4-7-nim', tier: 'reasoning', displayName: 'GLM-4.7', health: 'healthy', capabilities: ['code', 'reasoning', 'tools'] }],
        keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'z-ai-sdk' },
        rateLimits: { rpm: 40, rpd: 1000, remaining: { rpm: 40, rpd: 1000 }, isCooldown: false, cooldownRemainingMs: 0, description: 'z-ai SDK free tier' },
        costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — z-ai SDK' },
        capabilities: { chat: true, vision: false, embedding: false, code: true, tools: true, completion: false },
      },
      {
        provider: 'openrouter',
        label: 'OpenRouter Free',
        isAvailable: true,
        activeModels: 6,
        totalModels: 6,
        health: 'healthy' as const,
        rateLimitRemaining: 20,
        avgLatencyMs: 0,
        models: [],
        keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-or-***' },
        rateLimits: { rpm: 20, rpd: 200, remaining: { rpm: 20, rpd: 200 }, isCooldown: false, cooldownRemainingMs: 0, description: 'Free models tier' },
        costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free models only' },
        capabilities: { chat: true, vision: true, embedding: false, code: true, tools: true, completion: false },
      },
      {
        provider: 'groq',
        label: 'Groq Free (LPU)',
        isAvailable: false,
        activeModels: 0,
        totalModels: 3,
        health: 'unknown' as const,
        rateLimitRemaining: 30,
        avgLatencyMs: 0,
        models: [],
        keyStatus: { totalKeys: 0, healthyKeys: 0, hasAvailableKey: false, activeKeyMasked: null },
        rateLimits: { rpm: 30, rpd: 14400, remaining: { rpm: 30, rpd: 14400 }, isCooldown: false, cooldownRemainingMs: 0, description: 'Free LPU tier' },
        costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — LPU Inference' },
        capabilities: { chat: true, vision: false, embedding: false, code: true, tools: true, completion: false },
      },
      {
        provider: 'cerebras',
        label: 'Cerebras Free',
        isAvailable: false,
        activeModels: 0,
        totalModels: 2,
        health: 'unknown' as const,
        rateLimitRemaining: 30,
        avgLatencyMs: 0,
        models: [],
        keyStatus: { totalKeys: 0, healthyKeys: 0, hasAvailableKey: false, activeKeyMasked: null },
        rateLimits: { rpm: 30, rpd: 14400, remaining: { rpm: 30, rpd: 14400 }, isCooldown: false, cooldownRemainingMs: 0, description: 'CS-3 Wafer free tier' },
        costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier — CS-3 Wafer' },
        capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: false },
      },
      {
        provider: 'dashscope',
        label: 'Alibaba Cloud Free',
        isAvailable: false,
        activeModels: 0,
        totalModels: 8,
        health: 'unknown' as const,
        rateLimitRemaining: 10,
        avgLatencyMs: 0,
        models: [],
        keyStatus: { totalKeys: 0, healthyKeys: 0, hasAvailableKey: false, activeKeyMasked: null },
        rateLimits: { rpm: 10, rpd: 10000, remaining: { rpm: 10, rpd: 10000 }, isCooldown: false, cooldownRemainingMs: 0, description: '1M free tokens each' },
        costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: '1M free tokens per model' },
        capabilities: { chat: true, vision: true, embedding: true, code: true, tools: true, completion: false },
      },
    ]

    return NextResponse.json({
      providers: mockProviders,
      modelRoutes: [],
      tiers: { reasoning: [], balanced: [], fast: [], free: [] },
      summary: {
        totalProviders: mockProviders.length,
        availableProviders: mockProviders.filter(p => p.isAvailable).length,
        totalModels: 20,
        healthyModels: 7,
      },
    })
  }
}

/**
 * POST /api/ai/providers
 *
 * Test a provider connection by running a health check.
 * Body: { provider: string }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider } = body as { provider: string }

    if (!provider) {
      return NextResponse.json(
        { error: 'Missing required field: provider' },
        { status: 400 }
      )
    }

    // Forward to the existing health check endpoint
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'
    const healthResponse = await fetch(`${baseUrl}/api/ai-bridge/providers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    })

    const healthData = await healthResponse.json()

    return NextResponse.json(healthData, { status: healthResponse.status })
  } catch (error) {
    console.error('AI Providers health check error:', error)
    return NextResponse.json(
      {
        provider: 'unknown',
        isAvailable: false,
        latencyMs: -1,
        testedModel: 'unknown',
        error: error instanceof Error ? error.message : 'Health check failed',
      },
      { status: 500 }
    )
  }
}
