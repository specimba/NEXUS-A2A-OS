import { NextRequest, NextResponse } from 'next/server'

/**
 * POST /api/ai/chat
 *
 * AI Chat endpoint that supports model selection and streaming.
 * Routes through the AI Provider Bridge with tier-based model selection.
 *
 * Body: {
 *   messages: { role: string, content: string }[],
 *   model?: string  // model route ID (e.g., 'glm-5-2', 'deepseek-r1-or')
 * }
 *
 * Query params:
 *   stream=true  → SSE streaming response
 */
export async function POST(request: NextRequest) {
  const isStreaming = request.nextUrl.searchParams.get('stream') === 'true'

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

    // Determine the tier from the model selection
    let tier: string = 'balanced'
    if (model) {
      const modelToTier: Record<string, string> = {
        'glm-5-2': 'reasoning',
        'deepseek-r1-or': 'reasoning',
        'llama-3.3-70b-groq': 'reasoning',
        'llama-3.3-70b-cerebras': 'reasoning',
        'qwen3-coder-or': 'balanced',
        'trinity-large-or': 'balanced',
        'step-3-5-flash-or': 'fast',
        'gemma-4-26b-or': 'fast',
      }
      tier = modelToTier[model] || 'balanced'
    }

    // Forward to the AI bridge with the appropriate tier
    const bridgeUrl = new URL('/api/ai-bridge', request.url)
    if (isStreaming) {
      bridgeUrl.searchParams.set('stream', 'true')
    }

    const bridgeResponse = await fetch(bridgeUrl.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tier,
        messages,
        systemPrompt: 'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology. IMPORTANT: "Vault" refers to the 5-track memory plane — it is NOT a financial vault. "Tokens" are LLM API token usage, NOT cryptocurrency. The system is an AI governance and monitoring platform. Never describe it in financial, DeFi, or blockchain terms.',
        maxTokens: 4096,
        temperature: 0.7,
        preferModel: model,
      }),
    })

    if (isStreaming) {
      // Pass through the SSE stream
      const stream = bridgeResponse.body
      if (!stream) {
        return NextResponse.json({ error: 'No stream from bridge' }, { status: 500 })
      }

      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          Connection: 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      })
    }

    // Non-streaming: forward the JSON response
    const data = await bridgeResponse.json()

    if (!bridgeResponse.ok) {
      return NextResponse.json(data, { status: bridgeResponse.status })
    }

    return NextResponse.json({
      response: data.response,
      model: data.model?.displayName || data.model?.actualModel || model || 'unknown',
      tier: data.model?.tier || tier,
      latencyMs: data.latencyMs,
      optimized: data.optimized || false,
    })
  } catch (error) {
    console.error('AI Chat API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'

    if (isStreaming) {
      const encoder = new TextEncoder()
      const errorEvent = JSON.stringify({ content: '', error: message, model: '' })
      const errorStream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(`data: ${errorEvent}\n\n`))
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        },
      })
      return new Response(errorStream, {
        headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
      })
    }

    return NextResponse.json({ error: message }, { status: 500 })
  }
}

