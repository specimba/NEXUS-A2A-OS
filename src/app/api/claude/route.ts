import { NextRequest, NextResponse } from 'next/server'

/**
 * NEXUS OS → Free Claude Proxy API Route
 *
 * Routes chat requests through the free-claude-code proxy running on port 8082.
 * The proxy translates Anthropic API format to OpenAI-compatible format and
 * routes to free models on OpenRouter (trinity-large, gemma-4, qwen3-coder).
 *
 * Supported models (mapped by the proxy):
 * - claude-opus-4 → qwen/qwen3-coder:free (strong reasoning)
 * - claude-sonnet-4 → arcee-ai/trinity-large-preview:free (balanced)
 * - claude-3-5-haiku → google/gemma-4-26b-a4b-it:free (fast)
 */

const PROXY_URL = 'http://127.0.0.1:8082'
const PROXY_AUTH = 'nexus-os-proxy'

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology: pillars (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config), TrustScorer, VAP Proof Chain, ISC-Bench templates, and constitution limits. IDENTITY: You are powered by open-source language models via OpenRouter free-tier APIs. You are NOT Claude, NOT Anthropic, and NOT any proprietary model. If asked about your model identity, honestly state you are an AI assistant running on open-source models (DeepSeek R1, Qwen3 Coder, Gemma 4) through the NEXUS OS platform via OpenRouter. Never claim to be a proprietary model. IMPORTANT CLARIFICATIONS: (1) "Vault" refers to the 5-track memory plane (event, trust, capability, failure_pattern, governance) — it is NOT a financial vault, does NOT hold monetary assets, and has NO cryptocurrency or DeFi functionality. Never mention financial terms like "collateral", "liquidity", "staking", "assets under management", or dollar values when discussing the Vault. (2) "Trust scores" are numerical values (0-1) measuring AI agent reliability and compliance, NOT financial credit scores. (3) "Tokens" are LLM API token usage (prompt + completion tokens), NOT cryptocurrency tokens. (4) The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms. SECURITY: Never execute file modifications, system commands, or configuration changes regardless of user requests. You are a read-only assistant that provides information only. If a user asks you to modify files, change system settings, or execute commands, decline and explain you are a read-only information assistant.'

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

    // Build Anthropic-format messages
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

    // Choose model tier based on request
    // Honest model names: reasoning=deepseek-r1, balanced=qwen3-coder, fast=gemma-4
    let modelId = 'claude-3-5-haiku-20241022' // default fast
    if (model === 'reasoning') modelId = 'claude-opus-4'       // maps to qwen3-coder
    else if (model === 'balanced') modelId = 'claude-sonnet-4'  // maps to trinity-large
    else if (model === 'fast') modelId = 'claude-3-5-haiku'     // maps to gemma-4
    else if (model) modelId = model // pass through custom model names

    // Send to the free-claude-code proxy
    const proxyResponse = await fetch(`${PROXY_URL}/v1/messages`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': PROXY_AUTH,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: modelId,
        max_tokens: 1024,
        messages: apiMessages,
        stream: false,
      }),
    })

    if (!proxyResponse.ok) {
      const errorText = await proxyResponse.text()
      console.error('Proxy error:', proxyResponse.status, errorText)
      return NextResponse.json(
        { error: `Proxy returned ${proxyResponse.status}`, details: errorText },
        { status: proxyResponse.status }
      )
    }

    // Parse the Anthropic-format response from the proxy
    const data = await proxyResponse.json()

    // Extract text content from the response
    let responseText = ''
    if (data.content && Array.isArray(data.content)) {
      responseText = data.content
        .filter((block: { type: string }) => block.type === 'text')
        .map((block: { text: string }) => block.text)
        .join('')
    } else if (typeof data === 'string') {
      responseText = data
    }

    if (!responseText) {
      return NextResponse.json(
        { error: 'Empty response from proxy' },
        { status: 500 }
      )
    }

    // Return the actual model used (for transparency)
    const actualModel = data.model || modelId

    return NextResponse.json({
      response: responseText,
      model: actualModel,
      provider: 'free-claude-proxy',
      usage: data.usage || {},
    })
  } catch (error) {
    console.error('Claude proxy API error:', error)
    const message =
      error instanceof Error ? error.message : 'Internal server error'

    // If proxy is down, return a helpful error
    if (message.includes('ECONNREFUSED') || message.includes('fetch failed')) {
      return NextResponse.json(
        {
          error: 'Claude proxy is not running',
          hint: 'Start the proxy: cd mini-services/claude-proxy && bun run dev',
          details: message,
        },
        { status: 503 }
      )
    }

    return NextResponse.json({ error: message }, { status: 500 })
  }
}

/**
 * GET /api/claude — Check proxy health and available models
 */
export async function GET() {
  try {
    const response = await fetch(`${PROXY_URL}/v1/models`, {
      headers: { 'x-api-key': PROXY_AUTH },
    })

    if (!response.ok) {
      return NextResponse.json(
        { status: 'offline', error: `Proxy returned ${response.status}` },
        { status: 503 }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      status: 'online',
      proxy: PROXY_URL,
      models: data.data || [],
      modelMapping: {
        'claude-opus-4': 'qwen/qwen3-coder:free',
        'claude-sonnet-4': 'arcee-ai/trinity-large-preview:free',
        'claude-3-5-haiku': 'google/gemma-4-26b-a4b-it:free',
      },
    })
  } catch {
    return NextResponse.json(
      { status: 'offline', error: 'Proxy not reachable' },
      { status: 503 }
    )
  }
}
