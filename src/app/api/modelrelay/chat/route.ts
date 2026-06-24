import { NextRequest, NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages, model } = body as {
      messages: { role: string; content: string }[]
      model?: string
    }

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json({ error: 'Messages array is required' }, { status: 400 })
    }

    const selectedModel = model || 'llama4-maverick'
    const provider = selectedModel.includes('groq') ? 'groq'
      : selectedModel.includes('cerebras') ? 'cerebras'
      : selectedModel.includes('z-ai') || selectedModel.includes('glm') ? 'z-ai'
      : 'openrouter'

    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/relay/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        body: JSON.stringify(body),
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data)
      }
    } catch (pyError) {
      console.warn('Python relay chat API offline, falling back to mock:', pyError)
    }

    // Fallback to mock response
    const lastMessage = messages[messages.length - 1]?.content || ''
    const simulatedLatency = provider === 'groq' ? 38
      : provider === 'cerebras' ? 45
      : provider === 'z-ai' ? 12
      : 180 + Math.floor(Math.random() * 80)

    return NextResponse.json({
      id: `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      provider,
      model: selectedModel,
      output: `[Simulated response from ${provider}/${selectedModel}]\n\nYou said: "${lastMessage.slice(0, 100)}${lastMessage.length > 100 ? '...' : ''}"\n\nThis is a lightweight mock response. The actual AI provider connection has been disabled to prevent OOM issues. To enable real AI responses, configure API keys and remove the mock route.`,
      usage: {
        prompt_tokens: Math.ceil(lastMessage.length / 4),
        completion_tokens: 42,
        total_tokens: Math.ceil(lastMessage.length / 4) + 42,
      },
      routing: {
        intent: 'general',
        strategy: 'balanced',
        provider,
        model: selectedModel,
        latencyMs: simulatedLatency,
      },
    })
  } catch {
    return NextResponse.json({ error: 'Chat request failed' }, { status: 500 })
  }
}
