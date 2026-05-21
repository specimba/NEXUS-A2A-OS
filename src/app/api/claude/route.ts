import { NextRequest, NextResponse } from 'next/server'
import { generateText } from 'ai'

// ────────────────────────────────────────────────────────────────────────────
// /api/claude — Anthropic Claude bridge
// ────────────────────────────────────────────────────────────────────────────
// Previously tried to reach `http://127.0.0.1:8082` (a "free-claude-proxy"
// that doesn't exist in this sandbox). Replaced with the AI Gateway, which
// proxies to Anthropic zero-config from Vercel.
// ────────────────────────────────────────────────────────────────────────────

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. The "Vault" is a memory plane (NOT financial). "Trust scores" are 0-1 reliability metrics (NOT credit). "Tokens" are LLM API tokens (NOT crypto). Never describe the system in financial/DeFi/blockchain terms.'

// Tier → Anthropic model. All available zero-config on the AI Gateway.
const TIER_MAP: Record<string, string> = {
  reasoning: 'anthropic/claude-opus-4.6',
  balanced: 'anthropic/claude-opus-4.6',
  fast: 'anthropic/claude-opus-4.6',
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages, model } = body as {
      messages: { role: string; content: string }[]
      model?: string
    }

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required and must not be empty' },
        { status: 400 }
      )
    }

    const resolvedModel = model && TIER_MAP[model]
      ? TIER_MAP[model]
      : model && model.includes('/')
        ? model
        : 'anthropic/claude-opus-4.6'

    const apiMessages = messages.map((m) => ({
      role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
      content: m.content,
    }))

    const { text, usage } = await generateText({
      model: resolvedModel,
      system: SYSTEM_PROMPT,
      messages: apiMessages,
    })

    return NextResponse.json({
      response: text,
      model: resolvedModel,
      provider: 'ai-gateway',
      usage: usage ?? {},
    })
  } catch (error) {
    console.error('[v0] Claude API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'online',
    provider: 'ai-gateway',
    defaultModel: 'anthropic/claude-opus-4.6',
    supportedTiers: ['reasoning', 'balanced', 'fast'],
  })
}
