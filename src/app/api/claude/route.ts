import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

// ────────────────────────────────────────────────────────────────────────────
// /api/claude — Fallback AI bridge (uses z-ai SDK)
// ────────────────────────────────────────────────────────────────────────────
// This is a fallback endpoint for the AI assistant. All requests are
// routed through z-ai-web-dev-sdk (GLM-4.7) which works in this sandbox.
// ────────────────────────────────────────────────────────────────────────────

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. The "Vault" is a memory plane (NOT financial). "Trust scores" are 0-1 reliability metrics (NOT credit). "Tokens" are LLM API tokens (NOT crypto). Never describe the system in financial/DeFi/blockchain terms.'

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages } = body as {
      messages: { role: string; content: string }[]
    }

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required and must not be empty' },
        { status: 400 }
      )
    }

    const zai = await getZAI()

    const apiMessages = [
      { role: 'assistant' as const, content: SYSTEM_PROMPT },
      ...messages.map((m) => ({
        role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
        content: m.content,
      })),
    ]

    const completion = await zai.chat.completions.create({
      messages: apiMessages,
      thinking: { type: 'disabled' },
    })

    const responseText = completion.choices?.[0]?.message?.content || ''

    return NextResponse.json({
      response: responseText,
      model: 'GLM-4.7',
      provider: 'z-ai-sdk',
    })
  } catch (error) {
    console.error('[NEXUS] Claude API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'online',
    provider: 'z-ai-sdk',
    defaultModel: 'GLM-4.7',
    supportedTiers: ['reasoning', 'balanced', 'fast'],
  })
}
