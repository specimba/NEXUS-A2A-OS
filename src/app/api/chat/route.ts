import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

const SYSTEM_PROMPT =
  'You are the NEXUS OS AI Assistant, an intelligent governance operating system helper for a multi-agent AI orchestration platform. You help users understand system status, governance decisions, StressLab test results, GMR model routing, vault memory entries, and research pipeline. Be concise, technical, and authoritative. Use NEXUS OS terminology: pillars (Bridge, Engine, Governor, Vault, GMR, Swarm, Monitor, Config), TrustScorer, VAP Proof Chain, ISC-Bench templates, and constitution limits. IMPORTANT CLARIFICATIONS: (1) "Vault" refers to the 5-track memory plane (event, trust, capability, failure_pattern, governance) — it is NOT a financial vault, does NOT hold monetary assets, and has NO cryptocurrency or DeFi functionality. Never mention financial terms like "collateral", "liquidity", "staking", "assets under management", or dollar values when discussing the Vault. (2) "Trust scores" are numerical values (0-1) measuring AI agent reliability and compliance, NOT financial credit scores. (3) "Tokens" are LLM API token usage (prompt + completion tokens), NOT cryptocurrency tokens. (4) The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms.'

 
let zaiInstance: any = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages, systemPrompt } = body as {
      messages: { role: string; content: string }[]
      systemPrompt?: string
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
        content: systemPrompt || SYSTEM_PROMPT,
      },
      ...messages.map((m) => ({
        role: m.role === 'assistant' ? ('assistant' as const) : ('user' as const),
        content: m.content,
      })),
    ]

    const completion = await zai.chat.completions.create({
      messages: apiMessages,
      thinking: { type: 'disabled' },
    })

    const response = completion.choices[0]?.message?.content

    if (!response) {
      return NextResponse.json(
        { error: 'Empty response from AI' },
        { status: 500 }
      )
    }

    return NextResponse.json({ response })
  } catch (error) {
    console.error('Chat API error:', error)
    const message =
      error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
