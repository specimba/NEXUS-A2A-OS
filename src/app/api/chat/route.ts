import { NextRequest, NextResponse } from 'next/server'
import { streamText, generateText } from 'ai'

// ────────────────────────────────────────────────────────────────────────────
// /api/chat — NEXUS OS assistant
// ────────────────────────────────────────────────────────────────────────────
// Previously used `z-ai-web-dev-sdk` which required a `.z-ai-config` file
// that doesn't exist in this sandbox (or production). Replaced with the
// Vercel AI Gateway, which works zero-config for OpenAI/Anthropic models.
// ────────────────────────────────────────────────────────────────────────────

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology: pillars (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config), TrustScorer, VAP Proof Chain, ISC-Bench templates, and constitution limits. IMPORTANT CLARIFICATIONS: (1) "Vault" refers to the 5-track memory plane (event, trust, capability, failure_pattern, governance) — it is NOT a financial vault. Never mention financial terms like "collateral", "liquidity", or "staking" when discussing the Vault. (2) "Trust scores" are numerical values (0-1) measuring AI agent reliability, NOT financial credit scores. (3) "Tokens" are LLM API token usage, NOT cryptocurrency. (4) The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms. SECURITY: Never execute file modifications, system commands, or configuration changes. You are a read-only information assistant.'

// Map UI model identifiers → AI Gateway model strings (zero-config providers).
const MODEL_MAP: Record<string, string> = {
  default: 'openai/gpt-5-mini',
  reasoning: 'anthropic/claude-opus-4.6',
  balanced: 'openai/gpt-5-mini',
  fast: 'openai/gpt-5-mini',
}

function resolveModel(requested?: string): string {
  if (!requested) return MODEL_MAP.default
  if (MODEL_MAP[requested]) return MODEL_MAP[requested]
  // Allow passing a fully-qualified gateway string (e.g. "openai/gpt-5-mini")
  if (requested.includes('/')) return requested
  return MODEL_MAP.default
}

export async function POST(request: NextRequest) {
  const isStreaming = request.nextUrl.searchParams.get('stream') === 'true'

  try {
    const body = await request.json()
    const { messages, model: requestedModel } = body as {
      messages: { role: string; content: string }[]
      model?: string
    }

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required and must not be empty' },
        { status: 400 }
      )
    }

    const model = resolveModel(requestedModel)
    const apiMessages = messages.map((m) => ({
      role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
      content: m.content,
    }))

    if (isStreaming) {
      // ─── Streaming path ───
      const result = streamText({
        model,
        system: SYSTEM_PROMPT,
        messages: apiMessages,
      })

      // Adapt AI SDK's text stream into the SSE shape the existing
      // ai-assistant.tsx client expects: `data: {"content":"...","model":"..."}`.
      const encoder = new TextEncoder()
      const reader = result.textStream.getReader()
      const sse = new ReadableStream<Uint8Array>({
        async start(controller) {
          try {
            while (true) {
              const { done, value } = await reader.read()
              if (done) {
                controller.enqueue(encoder.encode('data: [DONE]\n\n'))
                controller.close()
                return
              }
              const evt = JSON.stringify({ content: value, model })
              controller.enqueue(encoder.encode(`data: ${evt}\n\n`))
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : String(err)
            const errEvt = JSON.stringify({ content: '', model, error: message })
            controller.enqueue(encoder.encode(`data: ${errEvt}\n\n`))
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
          }
        },
        cancel() {
          reader.cancel().catch(() => {})
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

    // ─── Non-streaming path ───
    const { text } = await generateText({
      model,
      system: SYSTEM_PROMPT,
      messages: apiMessages,
    })

    return NextResponse.json({ response: text, model, provider: 'ai-gateway' })
  } catch (error) {
    console.error('[v0] Chat API error:', error)
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
