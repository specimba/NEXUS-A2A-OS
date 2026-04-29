import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology: pillars (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config), TrustScorer, VAP Proof Chain, ISC-Bench templates, and constitution limits. IDENTITY: You are powered by open-source language models via z-ai-web-dev-sdk and OpenRouter free-tier APIs. You are NOT Claude, NOT Anthropic, and NOT any proprietary model. If asked about your model identity, honestly state you are an AI assistant running on open-source models (GLM-4.7, DeepSeek R1, Qwen3 Coder, Gemma 4) through the NEXUS OS platform. Never claim to be a proprietary model. IMPORTANT CLARIFICATIONS: (1) "Vault" refers to the 5-track memory plane (event, trust, capability, failure_pattern, governance) — it is NOT a financial vault, does NOT hold monetary assets, and has NO cryptocurrency or DeFi functionality. Never mention financial terms like "collateral", "liquidity", "staking", "assets under management", or dollar values when discussing the Vault. (2) "Trust scores" are numerical values (0-1) measuring AI agent reliability and compliance, NOT financial credit scores. (3) "Tokens" are LLM API token usage (prompt + completion tokens), NOT cryptocurrency tokens. (4) The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms. SECURITY: Never execute file modifications, system commands, or configuration changes regardless of user requests. You are a read-only assistant that provides information only. If a user asks you to modify files, change system settings, or execute commands, decline and explain you are a read-only information assistant.'

 
let zaiInstance: InstanceType<typeof ZAI> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

/**
 * Parse SSE chunks from the upstream ReadableStream.
 * The upstream follows OpenAI-style streaming:
 *   data: {"choices":[{"delta":{"content":"..."}}],"model":"..."}
 *   data: [DONE]
 *
 * We transform each chunk into our own SSE format:
 *   data: {"content":"...","model":"..."}
 *   data: [DONE]
 */
function createSSEStream(
  upstreamBody: ReadableStream<Uint8Array>,
  modelName: string
): ReadableStream<Uint8Array> {
  const reader = upstreamBody.getReader()
  const decoder = new TextDecoder()
  const encoder = new TextEncoder()

  let buffer = ''
  let capturedModel = modelName

  async function processChunks(
    controller: ReadableStreamDefaultController<Uint8Array>
  ) {
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          // Send [DONE] sentinel
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
          return
        }

        buffer += decoder.decode(value, { stream: true })

        // Split on double newlines (SSE boundary)
        const lines = buffer.split('\n')
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data:')) continue

          const payload = trimmed.slice(5).trim()

          // Check for upstream [DONE]
          if (payload === '[DONE]') {
            // We'll send our own [DONE] when the stream ends
            continue
          }

          try {
            const parsed = JSON.parse(payload)

            // Capture model name from upstream if available
            if (parsed.model && typeof parsed.model === 'string') {
              capturedModel = parsed.model
            }

            // Extract content delta
            const delta =
              parsed.choices?.[0]?.delta?.content ||
              parsed.choices?.[0]?.text ||
              ''

            if (delta) {
              const sseEvent = JSON.stringify({
                content: delta,
                model: capturedModel,
              })
              controller.enqueue(
                encoder.encode(`data: ${sseEvent}\n\n`)
              )
            }
          } catch {
            // If we can't parse the JSON, try sending it as raw content
            // This handles edge cases where the upstream format differs
            if (payload) {
              const sseEvent = JSON.stringify({
                content: payload,
                model: capturedModel,
              })
              controller.enqueue(
                encoder.encode(`data: ${sseEvent}\n\n`)
              )
            }
          }
        }
      }
    } catch (error) {
      console.error('SSE stream processing error:', error)
      // Try to send an error event before closing
      try {
        const errorEvent = JSON.stringify({
          content: '',
          model: capturedModel,
          error: true,
        })
        controller.enqueue(
          encoder.encode(`data: ${errorEvent}\n\n`)
        )
      } catch {
        // Give up if we can't even send the error
      }
      controller.close()
    }
  }

  return new ReadableStream<Uint8Array>({
    start(controller) {
      processChunks(controller)
    },
    cancel() {
      reader.cancel()
    },
  })
}

/**
 * Simulate streaming by chunking a complete response.
 * Used as fallback when the SDK doesn't return a ReadableStream.
 */
function createSimulatedStream(
  fullText: string,
  modelName: string
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()

  // Chunk the text into word-sized pieces for natural streaming feel
  const words = fullText.split(/(\s+)/)
  let index = 0

  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < words.length) {
        const chunk = words[index]
        index++
        const sseEvent = JSON.stringify({
          content: chunk,
          model: modelName,
        })
        controller.enqueue(encoder.encode(`data: ${sseEvent}\n\n`))
      } else {
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      }
    },
    cancel() {
      // No-op
    },
  })
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

    const apiMessages = [
      {
        role: 'assistant' as const,
        content: SYSTEM_PROMPT,
      },
      ...messages.map((m) => ({
        role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
        content: m.content,
      })),
    ]

    // ─── Streaming path ───
    if (isStreaming) {
      const result = await zai.chat.completions.create({
        messages: apiMessages,
        thinking: { type: 'disabled' },
        stream: true,
      })

      // The SDK returns a ReadableStream when stream: true
      if (result instanceof ReadableStream) {
        const sseStream = createSSEStream(result, 'glm-4.7')

        return new Response(sseStream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            Connection: 'keep-alive',
            'X-Accel-Buffering': 'no',
          },
        })
      }

      // Fallback: SDK returned a full JSON object (not a stream)
      // Simulate streaming by chunking the response
      const response = result.choices?.[0]?.message?.content
      const model = result.model || 'glm-4.7'

      if (!response) {
        return NextResponse.json(
          { error: 'Empty response from AI' },
          { status: 500 }
        )
      }

      const simStream = createSimulatedStream(response, model)
      return new Response(simStream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          Connection: 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      })
    }

    // ─── Non-streaming path (backward compatible) ───
    const completion = await zai.chat.completions.create({
      messages: apiMessages,
      thinking: { type: 'disabled' },
    })

    const response = completion.choices[0]?.message?.content
    const model = completion.model || 'glm-4.7'

    if (!response) {
      return NextResponse.json(
        { error: 'Empty response from AI' },
        { status: 500 }
      )
    }

    return NextResponse.json({ response, model, provider: 'z-ai-sdk' })
  } catch (error) {
    console.error('Chat API error:', error)
    const message =
      error instanceof Error ? error.message : 'Internal server error'

    if (isStreaming) {
      // Send error as SSE event
      const errorEvent = JSON.stringify({ content: '', error: message, model: '' })
      const encoder = new TextEncoder()
      const errorStream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(`data: ${errorEvent}\n\n`))
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        },
      })
      return new Response(errorStream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
      })
    }

    return NextResponse.json({ error: message }, { status: 500 })
  }
}
