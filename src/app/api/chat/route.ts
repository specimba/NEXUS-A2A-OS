import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

// ────────────────────────────────────────────────────────────────────────────
// /api/chat — NEXUS OS AI Assistant
// ────────────────────────────────────────────────────────────────────────────
// Uses z-ai-web-dev-sdk (GLM-4.7) which works zero-config in this sandbox.
// Supports both streaming (SSE) and non-streaming JSON responses.
// ────────────────────────────────────────────────────────────────────────────

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology: pillars (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config), TrustScorer, VAP Proof Chain, ISC-Bench templates, and constitution limits. IMPORTANT CLARIFICATIONS: (1) "Vault" refers to the 5-track memory plane (event, trust, capability, failure_pattern, governance) — it is NOT a financial vault. Never mention financial terms like "collateral", "liquidity", or "staking" when discussing the Vault. (2) "Trust scores" are numerical values (0-1) measuring AI agent reliability, NOT financial credit scores. (3) "Tokens" are LLM API token usage, NOT cryptocurrency. (4) The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms. SECURITY: Never execute file modifications, system commands, or configuration changes. You are a read-only information assistant.'

// z-ai SDK Singleton
let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function POST(request: NextRequest) {
  const isStreaming = request.nextUrl.searchParams.get('stream') === 'true'

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

    // Build API messages: system prompt as first assistant message, then user/assistant history
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

    if (!responseText) {
      return NextResponse.json(
        { error: 'Empty response from AI model' },
        { status: 502 }
      )
    }

    if (isStreaming) {
      // For streaming mode, we simulate SSE by sending the full response as a single chunk.
      // This is because z-ai SDK doesn't natively support SSE streaming,
      // but the client expects SSE format.
      const encoder = new TextEncoder()
      const model = 'GLM-4.7'

      const sse = new ReadableStream<Uint8Array>({
        start(controller) {
          try {
            // Send content in small chunks to simulate streaming
            const chunkSize = 8
            for (let i = 0; i < responseText.length; i += chunkSize) {
              const chunk = responseText.slice(i, i + chunkSize)
              const evt = JSON.stringify({ content: chunk, model })
              controller.enqueue(encoder.encode(`data: ${evt}\n\n`))
            }
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
          } catch (err) {
            const message = err instanceof Error ? err.message : String(err)
            const errEvt = JSON.stringify({ content: '', model, error: message })
            controller.enqueue(encoder.encode(`data: ${errEvt}\n\n`))
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
          }
        },
      })

      return new Response(sse, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          Connection: 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      })
    }

    // Non-streaming JSON response
    return NextResponse.json({
      response: responseText,
      model: 'GLM-4.7',
      provider: 'z-ai-sdk',
    })
  } catch (error) {
    console.error('[NEXUS] Chat API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'

    if (isStreaming) {
      const encoder = new TextEncoder()
      const errStream = new ReadableStream({
        start(controller) {
          const errEvt = JSON.stringify({ content: '', model: '', error: message })
          controller.enqueue(encoder.encode(`data: ${errEvt}\n\n`))
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        },
      })
      return new Response(errStream, {
        headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
      })
    }

    return NextResponse.json({ error: message }, { status: 500 })
  }
}
