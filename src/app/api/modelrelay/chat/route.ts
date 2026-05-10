import { NextRequest, NextResponse } from 'next/server'
import { routeRequest, recordSuccess, recordFailure } from '@/lib/modelrelay/gateway'
import { PROVIDERS, MODELS } from '@/lib/modelrelay/config'

export async function POST(request: NextRequest) {
  const isStreaming = request.nextUrl.searchParams.get('stream') === 'true'

  try {
    const body = await request.json()
    const { messages, strategy, model: requestedModel } = body as {
      messages: { role: string; content: string }[]
      strategy?: string
      model?: string
    }

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required' },
        { status: 400 }
      )
    }

    // Extract prompt for routing
    const prompt = messages.map(m => `${m.role}: ${m.content}`).join('\n')

    // Route the request
    const route = routeRequest(prompt, strategy)

    // Determine which model to actually use
    let actualModel = requestedModel || route.primaryModel
    let actualProvider = route.provider

    // If a specific model was requested, find its provider
    if (requestedModel) {
      const modelInfo = MODELS.find(m => m.modelId === requestedModel)
      if (modelInfo) {
        actualProvider = modelInfo.provider
        actualModel = requestedModel
      }
    }

    // Get provider config
    const providerConfig = PROVIDERS[actualProvider]
    if (!providerConfig) {
      return NextResponse.json(
        { error: `Provider ${actualProvider} not configured`, route },
        { status: 400 }
      )
    }

    // Get API key
    const apiKey = process.env[providerConfig.envKey]
    if (!apiKey && providerConfig.authType !== 'none') {
      // Try fallback chain
      for (const fallbackModelId of route.fallbackChain) {
        const fallbackModel = MODELS.find(m => m.modelId === fallbackModelId)
        if (fallbackModel) {
          const fallbackProvider = PROVIDERS[fallbackModel.provider]
          const fallbackKey = process.env[fallbackProvider?.envKey || '']
          if (fallbackKey) {
            actualProvider = fallbackModel.provider
            actualModel = fallbackModelId
            break
          }
        }
      }

      const finalProvider = PROVIDERS[actualProvider]
      const finalKey = process.env[finalProvider?.envKey || '']
      if (!finalKey && finalProvider?.authType !== 'none') {
        return NextResponse.json({
          error: `No API key available for ${actualProvider}`,
          route,
          suggestion: 'Add API keys in Settings or use a different model',
        }, { status: 401 })
      }
    }

    // Resolve model name for API call (strip provider prefix)
    const modelForApi = actualModel.includes('/')
      ? actualModel.split('/').slice(1).join('/')
      : actualModel

    // Build the request to the provider
    const providerCfg = PROVIDERS[actualProvider]
    const url = `${providerCfg.baseUrl}${providerCfg.chatPath}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    const key = process.env[providerCfg.envKey]
    if (key && providerCfg.authType === 'bearer') {
      headers['Authorization'] = `Bearer ${key}`
    }

    // Special headers for OpenRouter
    if (actualProvider === 'openrouter') {
      headers['HTTP-Referer'] = 'https://nexus-os.app'
      headers['X-Title'] = 'NEXUS OS v3.1'
    }

    const chatBody = {
      model: modelForApi,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      max_tokens: 4096,
      temperature: 0.7,
      stream: isStreaming,
    }

    const startTime = Date.now()

    if (isStreaming) {
      // Forward as SSE stream
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify(chatBody),
          signal: AbortSignal.timeout(60000),
        })

        const latencyMs = Date.now() - startTime

        if (!response.ok) {
          recordFailure(actualProvider, `HTTP ${response.status}`)
          const errorText = await response.text()
          return NextResponse.json(
            { error: `Provider ${actualProvider} error: ${response.status}`, details: errorText.slice(0, 500) },
            { status: response.status }
          )
        }

        recordSuccess(actualProvider, latencyMs)

        // Pass through the SSE stream
        return new Response(response.body, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            Connection: 'keep-alive',
            'X-Accel-Buffering': 'no',
          },
        })
      } catch (fetchError) {
        recordFailure(actualProvider, String(fetchError))
        return NextResponse.json(
          { error: `Connection failed to ${actualProvider}` },
          { status: 502 }
        )
      }
    }

    // Non-streaming
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(chatBody),
        signal: AbortSignal.timeout(60000),
      })

      const latencyMs = Date.now() - startTime

      if (!response.ok) {
        recordFailure(actualProvider, `HTTP ${response.status}`)
        const errorData = await response.text()
        return NextResponse.json({
          error: `Provider ${actualProvider} error: ${response.status}`,
          details: errorData.slice(0, 500),
          route,
        }, { status: response.status })
      }

      const data = await response.json()
      recordSuccess(actualProvider, latencyMs)

      // Extract output
      let output = ''
      if (data.choices && data.choices.length > 0) {
        output = data.choices[0].message?.content || ''
      }

      const usage = data.usage || {}

      return NextResponse.json({
        id: route.requestId,
        provider: actualProvider,
        model: actualModel,
        modelForApi,
        output,
        usage,
        routing: {
          intent: route.intent,
          strategy: route.strategy,
          candidates: route.fallbackChain.length + 1,
          score: route.score,
          reasoning: route.reasoning,
          latencyMs,
        },
      })
    } catch (fetchError) {
      recordFailure(actualProvider, String(fetchError))
      return NextResponse.json(
        { error: `Connection failed to ${actualProvider}`, route },
        { status: 502 }
      )
    }
  } catch (error) {
    return NextResponse.json(
      { error: 'Chat request failed' },
      { status: 500 }
    )
  }
}
