import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'
import { db } from '@/lib/db'

// ── Types ──────────────────────────────────────────────────────────────

interface VaultQueryRequest {
  query: string
  tracks?: string[]       // filter by Vault tracks: 'EVT', 'TRU', 'CAP', 'FAIL', 'GOV'
  maxContextEntries?: number  // max vault entries to include as context, default 20
  includeHistory?: boolean   // include past queries, default true
}

interface VaultEntryContext {
  id: string
  track: string
  category: string
  key: string
  value: string
  score: number
  agentName: string | null
  createdAt: string
}

interface VaultQueryResult {
  query: string
  response: string
  sourcesUsed: number
  tracksQueried: string[]
  model: string
  provider: string
  latencyMs: number
  contextEntries: VaultEntryContext[]
}

// ── SDK Singleton ──────────────────────────────────────────────────────

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    try {
      zaiInstance = await ZAI.create()
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      throw new Error(
        `Failed to initialize z-ai-web-dev-sdk. Ensure ZAI_API_KEY is set. Error: ${msg}`
      )
    }
  }
  return zaiInstance
}

// ── Track Labels ───────────────────────────────────────────────────────

const TRACK_LABELS: Record<string, string> = {
  'EVT': 'Event Track — system events and state changes',
  'TRU': 'Trust Track — trust scores and compliance records',
  'CAP': 'Capability Track — agent capabilities and performance',
  'FAIL': 'Failure Pattern Track — error patterns and resolutions',
  'GOV': 'Governance Track — governance decisions and audit trail',
}

// ── Route Handler ──────────────────────────────────────────────────────

/**
 * POST /api/ai/vault/query
 *
 * Query the knowledge vault using AI-powered context retrieval.
 * Pulls relevant vault entries from the database, builds a context
 * window, and uses z-ai-web-dev-sdk to generate an informed response.
 *
 * Body: {
 *   query: string,
 *   tracks?: string[],             // filter by tracks: 'EVT', 'TRU', 'CAP', 'FAIL', 'GOV'
 *   maxContextEntries?: number,    // default 20, max 100
 *   includeHistory?: boolean       // default true
 * }
 *
 * Rate limiting: TODO - Add per-user rate limiting middleware
 */
export async function POST(request: NextRequest) {
  try {
    const body: VaultQueryRequest = await request.json()
    const { query, tracks, maxContextEntries = 20, includeHistory = true } = body

    // ── Validate input ──
    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'Query string is required and must not be empty' },
        { status: 400 }
      )
    }

    if (query.length > 2000) {
      return NextResponse.json(
        { success: false, error: 'Query string must be 2000 characters or less' },
        { status: 400 }
      )
    }

    const clampedEntries = Math.min(Math.max(1, maxContextEntries), 100)

    // Validate tracks if provided
    const validTracks = ['EVT', 'TRU', 'CAP', 'FAIL', 'GOV']
    const effectiveTracks = tracks?.filter(t => validTracks.includes(t)) || validTracks

    // ── Fetch relevant vault entries from the database ──
    let vaultEntries: any[] = []
    try {
      const whereClause: any = {
        track: effectiveTracks.length < validTracks.length ? { in: effectiveTracks } : undefined,
      }

      vaultEntries = await db.vaultEntry.findMany({
        where: Object.keys(whereClause).length > 0 ? whereClause : undefined,
        take: clampedEntries,
        orderBy: { createdAt: 'desc' },
        include: { agent: { select: { name: true } } },
      })
    } catch (dbError) {
      console.warn('Failed to fetch vault entries from database, proceeding without context:', dbError)
    }

    // Build context from vault entries
    const contextEntries: VaultEntryContext[] = vaultEntries.map(entry => ({
      id: entry.id,
      track: entry.track,
      category: entry.category,
      key: entry.key,
      value: entry.value,
      score: entry.score,
      agentName: entry.agent?.name || null,
      createdAt: entry.createdAt.toISOString(),
    }))

    // Build the context string for the AI
    let contextString = ''
    if (contextEntries.length > 0) {
      const trackGroups = new Map<string, VaultEntryContext[]>()
      for (const entry of contextEntries) {
        const existing = trackGroups.get(entry.track) || []
        existing.push(entry)
        trackGroups.set(entry.track, existing)
      }

      const contextParts: string[] = ['=== NEXUS OS VAULT KNOWLEDGE BASE ===\n']

      for (const [track, entries] of trackGroups) {
        const trackLabel = TRACK_LABELS[track] || `Track ${track}`
        contextParts.push(`\n--- ${trackLabel} (${entries.length} entries) ---`)

        for (const entry of entries.slice(0, 5)) { // Limit to 5 entries per track for context
          try {
            const parsedValue = JSON.parse(entry.value)
            contextParts.push(`[${entry.key}] (score: ${entry.score}, agent: ${entry.agentName || 'system'}): ${JSON.stringify(parsedValue).slice(0, 300)}`)
          } catch {
            contextParts.push(`[${entry.key}] (score: ${entry.score}, agent: ${entry.agentName || 'system'}): ${entry.value.slice(0, 300)}`)
          }
        }

        if (entries.length > 5) {
          contextParts.push(`  ... and ${entries.length - 5} more entries in this track`)
        }
      }

      contextString = contextParts.join('\n')
    } else {
      contextString = 'No vault entries available. The vault knowledge base is empty or the database is not accessible.'
    }

    // ── Initialize SDK and generate response ──
    const zai = await getZAI()

    const systemPrompt = `You are the NEXUS OS Vault Query Assistant, an AI-powered knowledge retrieval system for the multi-agent governance platform. You answer queries based on the Vault knowledge base context provided to you.

IMPORTANT CONTEXT about NEXUS OS terminology:
- "Vault" = 5-track memory plane (EVT, TRU, CAP, FAIL, GOV) — NOT a financial vault, does NOT hold monetary assets
- "Trust scores" = AI agent reliability and compliance metrics (0-1) — NOT financial credit scores
- "Tokens" = LLM API token usage (prompt + completion tokens) — NOT cryptocurrency tokens
- The system is an AI governance and monitoring platform — never describe it in financial, DeFi, or blockchain terms

TRACK DEFINITIONS:
- EVT (Event Track): System events, state changes, and operational history
- TRU (Trust Track): Trust scores, compliance records, and agent reliability metrics
- CAP (Capability Track): Agent capabilities, performance benchmarks, and skill assessments
- FAIL (Failure Pattern Track): Error patterns, failure modes, and resolution strategies
- GOV (Governance Track): Governance decisions, constitution limits, and audit trail

INSTRUCTIONS:
1. Base your answer on the Vault context provided below
2. If the context doesn't contain relevant information, say so clearly
3. Reference specific vault entries, tracks, and agents when possible
4. Provide actionable insights and recommendations
5. Be precise and technical — avoid vague statements
6. If asked about data not in the vault, explain what kind of data would be needed

VAULT CONTEXT:
${contextString}`

    const startTime = Date.now()

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: systemPrompt },
        { role: 'user', content: query.trim() },
      ],
      thinking: { type: 'disabled' },
      temperature: 0.3, // Lower temperature for factual, context-grounded responses
    })

    const response = completion.choices[0]?.message?.content || ''
    const model = completion.model || 'glm-4.7'
    const latencyMs = Date.now() - startTime

    if (!response) {
      return NextResponse.json(
        { success: false, error: 'Empty response from AI' },
        { status: 500 }
      )
    }

    const result: VaultQueryResult = {
      query: query.trim(),
      response,
      sourcesUsed: contextEntries.length,
      tracksQueried: effectiveTracks,
      model,
      provider: 'z-ai',
      latencyMs,
      contextEntries: contextEntries.slice(0, 10), // Return up to 10 context entries for reference
    }

    // Optionally log this query to the vault itself
    if (includeHistory) {
      try {
        // Find or create a system agent for logging
        const systemAgent = await db.agent.findFirst({ where: { name: 'vault_assistant' } })
        if (systemAgent) {
          await db.vaultEntry.create({
            data: {
              agentId: systemAgent.id,
              track: 'EVT',
              category: 'vault_query',
              key: `query:${Date.now()}`,
              value: JSON.stringify({
                query: query.trim().slice(0, 200),
                responseLength: response.length,
                sourcesUsed: contextEntries.length,
                tracksQueried: effectiveTracks,
                model,
                latencyMs,
              }),
              score: 0.5, // Neutral score for query logs
            },
          })
        }
      } catch {
        // Vault logging is non-critical
      }
    }

    return NextResponse.json({
      success: true,
      data: result,
    })
  } catch (error: any) {
    console.error('AI Vault Query API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'

    const status = message.includes('rate limited') ? 429
      : message.includes('API key') ? 503
      : message.includes('timed out') ? 504
      : 500

    return NextResponse.json(
      { success: false, error: message },
      { status }
    )
  }
}
