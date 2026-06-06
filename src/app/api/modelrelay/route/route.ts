import { NextRequest, NextResponse } from 'next/server'

const INTENT_MAP: Record<string, { intent: string; strategy: string; primaryModel: string; provider: string; fallbackChain: string[] }> = {
  code: { intent: 'code', strategy: 'code-optimized', primaryModel: 'qwen3-coder', provider: 'openrouter', fallbackChain: ['glm-4-7-nim', 'llama3.3-70b'] },
  reasoning: { intent: 'reasoning', strategy: 'quality-first', primaryModel: 'deepseek-r1-free', provider: 'openrouter', fallbackChain: ['glm-4-7-nim', 'trinity-large'] },
  chat: { intent: 'chat', strategy: 'balanced', primaryModel: 'llama4-maverick', provider: 'openrouter', fallbackChain: ['gemma-3-27b', 'mistral-small'] },
  fast: { intent: 'fast', strategy: 'speed-first', primaryModel: 'llama3.1-8b-groq', provider: 'groq', fallbackChain: ['qwen3-8b-cerebras', 'gemma2-9b-groq'] },
  analysis: { intent: 'analysis', strategy: 'quality-first', primaryModel: 'deepseek-r1-free', provider: 'openrouter', fallbackChain: ['glm-4-7-nim', 'llama3.3-70b'] },
  creative: { intent: 'creative', strategy: 'balanced', primaryModel: 'gemma-3-27b', provider: 'openrouter', fallbackChain: ['llama4-maverick', 'mistral-small'] },
  default: { intent: 'general', strategy: 'balanced', primaryModel: 'llama4-maverick', provider: 'openrouter', fallbackChain: ['glm-4-7-nim', 'llama3.3-70b'] },
}

function classifyIntent(prompt: string): string {
  const lower = prompt.toLowerCase()
  if (/code|function|implement|debug|program|class |def |import /i.test(lower)) return 'code'
  if (/analyz|explain|reason|think|compare|evaluate/i.test(lower)) return 'reasoning'
  if (/quick|fast|simple|brief|short/i.test(lower)) return 'fast'
  if (/data|chart|statistic|metric|report/i.test(lower)) return 'analysis'
  if (/write|story|creative|poem|imagin/i.test(lower)) return 'creative'
  return 'default'
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prompt, strategy } = body as { prompt: string; strategy?: string }

    if (!prompt || typeof prompt !== 'string') {
      return NextResponse.json({ error: 'Prompt is required' }, { status: 400 })
    }

    const intent = classifyIntent(prompt)
    const route = INTENT_MAP[strategy ? (INTENT_MAP[strategy] ? strategy : intent) : intent] || INTENT_MAP.default

    return NextResponse.json({
      requestId: `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      intent: route.intent,
      strategy: route.strategy,
      primaryModel: route.primaryModel,
      provider: route.provider,
      fallbackChain: route.fallbackChain,
      score: 0.85 + Math.random() * 0.1,
      reasoning: `Classified as "${route.intent}" — routed to ${route.provider}/${route.primaryModel} via ${route.strategy} strategy`,
      timestamp: new Date().toISOString(),
    })
  } catch {
    return NextResponse.json({ error: 'Routing failed' }, { status: 500 })
  }
}
