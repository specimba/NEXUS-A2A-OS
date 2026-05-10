import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

// ── Types ──────────────────────────────────────────────────────────────

interface ResearchSearchRequest {
  query: string
  maxResults?: number  // default 10, max 50
  domain?: string      // e.g. 'ai_safety', 'compbio', 'cyber'
  depth?: 'shallow' | 'medium' | 'deep'  // search depth
}

interface ResearchResult {
  title: string
  summary: string
  relevanceScore: number
  domain: string
  keyFindings: string[]
  suggestedActions: string[]
  citations: string[]
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

// ── Route Handler ──────────────────────────────────────────────────────

/**
 * POST /api/ai/research/search
 *
 * Research paper search endpoint powered by z-ai-web-dev-sdk.
 * Uses AI to generate structured research insights from a query.
 *
 * Body: {
 *   query: string,
 *   maxResults?: number,     // default 10, max 50
 *   domain?: string,         // optional domain filter
 *   depth?: 'shallow' | 'medium' | 'deep'  // default 'medium'
 * }
 *
 * Rate limiting: TODO - Add per-user rate limiting middleware
 */
export async function POST(request: NextRequest) {
  try {
    const body: ResearchSearchRequest = await request.json()
    const { query, maxResults = 10, domain, depth = 'medium' } = body

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

    const clampedResults = Math.min(Math.max(1, maxResults), 50)

    // ── Initialize SDK ──
    const zai = await getZAI()

    // Build the system prompt for research search
    const domainContext = domain
      ? ` Focus specifically on the "${domain}" domain.`
      : ''

    const depthInstructions: Record<string, string> = {
      shallow: 'Provide a brief overview with 2-3 key findings per result.',
      medium: 'Provide a balanced analysis with 3-5 key findings and suggested actions per result.',
      deep: 'Provide an in-depth analysis with 5-8 key findings, detailed suggested actions, and relevant citations per result.',
    }

    const systemPrompt = `You are a research search assistant for NEXUS OS v3.1, a multi-agent AI governance platform. Your task is to generate structured research insights based on the user's query.${domainContext}

${depthInstructions[depth] || depthInstructions.medium}

IMPORTANT CONTEXT about NEXUS OS terminology:
- "Vault" = 5-track memory plane (event, trust, capability, failure_pattern, governance) — NOT a financial vault
- "Trust scores" = AI agent reliability metrics (0-1) — NOT financial credit scores
- "Tokens" = LLM API token usage — NOT cryptocurrency tokens
- "Governance" = AI agent governance and compliance — NOT corporate governance

Return your response as a JSON array of research results. Each result MUST have this exact structure:
{
  "title": "Descriptive title of the finding",
  "summary": "2-3 sentence summary of the research insight",
  "relevanceScore": 0.0-1.0,
  "domain": "relevant domain category",
  "keyFindings": ["finding1", "finding2", ...],
  "suggestedActions": ["action1", "action2", ...],
  "citations": ["citation1", "citation2", ...]
}

Generate exactly ${clampedResults} results. Return ONLY the JSON array, no markdown fences or extra text.`

    const startTime = Date.now()

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: systemPrompt },
        { role: 'user', content: `Research query: ${query.trim()}` },
      ],
      thinking: { type: 'disabled' },
      temperature: 0.4, // Lower temperature for more structured output
    })

    const rawResponse = completion.choices[0]?.message?.content || ''
    const latencyMs = Date.now() - startTime
    const model = completion.model || 'glm-4.7'

    // Parse the JSON response
    let results: ResearchResult[]
    try {
      // Try to extract JSON from the response (handle markdown code fences)
      let jsonStr = rawResponse
      const jsonMatch = rawResponse.match(/```(?:json)?\s*([\s\S]*?)```/)
      if (jsonMatch) {
        jsonStr = jsonMatch[1].trim()
      }

      // Try parsing as array directly
      try {
        results = JSON.parse(jsonStr)
      } catch {
        // Try to find the array in the response
        const arrayMatch = jsonStr.match(/\[[\s\S]*\]/)
        if (arrayMatch) {
          results = JSON.parse(arrayMatch[0])
        } else {
          throw new Error('Could not parse research results as JSON array')
        }
      }

      if (!Array.isArray(results)) {
        throw new Error('Response is not an array')
      }
    } catch (parseError) {
      // If parsing fails, create a single result from the raw text
      results = [{
        title: `Research insights for: ${query.slice(0, 100)}`,
        summary: rawResponse.slice(0, 500),
        relevanceScore: 0.7,
        domain: domain || 'general',
        keyFindings: rawResponse.split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('•')).map(l => l.replace(/^[-•]\s*/, '').trim()).slice(0, 5),
        suggestedActions: ['Review the raw AI output for additional insights', 'Refine the search query for more specific results'],
        citations: [],
      }]
    }

    // Enrich results with metadata
    const enrichedResults = results.slice(0, clampedResults).map((r, index) => ({
      ...r,
      id: `research-${Date.now()}-${index}`,
      relevanceScore: typeof r.relevanceScore === 'number'
        ? Math.min(1, Math.max(0, r.relevanceScore))
        : 0.5,
      domain: r.domain || domain || 'general',
    }))

    return NextResponse.json({
      success: true,
      data: {
        results: enrichedResults,
        query: query.trim(),
        totalResults: enrichedResults.length,
        model,
        provider: 'z-ai',
        latencyMs,
        meta: {
          maxResults: clampedResults,
          depth,
          domain: domain || null,
        },
      },
    })
  } catch (error: any) {
    console.error('AI Research Search API error:', error)
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
