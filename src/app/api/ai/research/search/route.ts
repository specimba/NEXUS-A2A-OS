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
  // Extended fields for richer client mapping
  authors?: string[]
  abstract?: string
  category?: string
  year?: number | null
  pdfUrl?: string
  sourceUrl?: string
  hostName?: string
  noveltyScore?: number
  citationCount?: number
  researchRole?: string
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

// ── Web Search Helper ──────────────────────────────────────────────────

interface WebSearchItem {
  url: string
  name: string
  snippet: string
  host_name: string
  rank: number
  date: string
  favicon: string
}

async function performWebSearch(
  zai: Awaited<ReturnType<typeof ZAI.create>>,
  query: string,
  num: number
): Promise<WebSearchItem[]> {
  try {
    const results = await zai.functions.invoke('web_search', {
      query,
      num: Math.min(num, 20), // Web search API limit
      recency_days: 365,      // Last year for recent research
    })
    return Array.isArray(results) ? results : []
  } catch (error) {
    console.warn('Web search failed, will fall back to pure AI generation:', error)
    return []
  }
}

// ── Route Handler ──────────────────────────────────────────────────────

/**
 * POST /api/ai/research/search
 *
 * Research paper search endpoint powered by z-ai-web-dev-sdk.
 * Uses a two-phase approach:
 *   1. Real web search via z-ai functions API
 *   2. AI enrichment to structure results as research paper entries
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

    const startTime = Date.now()

    // ── Phase 1: Real Web Search ──
    const searchQuery = domain
      ? `${query.trim()} ${domain} research`
      : query.trim()

    const webResults = await performWebSearch(zai, searchQuery, clampedResults)

    // ── Phase 2: AI Enrichment ──
    const domainContext = domain
      ? ` Focus specifically on the "${domain}" domain.`
      : ''

    const depthInstructions: Record<string, string> = {
      shallow: 'Provide a brief overview with 2-3 key findings per result.',
      medium: 'Provide a balanced analysis with 3-5 key findings and suggested actions per result.',
      deep: 'Provide an in-depth analysis with 5-8 key findings, detailed suggested actions, and relevant citations per result.',
    }

    let systemPrompt: string
    let userPrompt: string

    if (webResults.length > 0) {
      // ── Enrichment mode: Structure real web search results ──
      const searchContext = webResults
        .slice(0, 20)
        .map((r, i) => `[${i + 1}] "${r.name}" — ${r.snippet} (Source: ${r.host_name}, URL: ${r.url}${r.date ? `, Date: ${r.date}` : ''})`)
        .join('\n')

      systemPrompt = `You are a research search assistant for NEXUS OS v3.1, a multi-agent AI governance platform. Your task is to take REAL web search results and structure them into academic-style research entries.${domainContext}

${depthInstructions[depth] || depthInstructions.medium}

IMPORTANT CONTEXT about NEXUS OS terminology:
- "Vault" = 5-track memory plane (event, trust, capability, failure_pattern, governance) — NOT a financial vault
- "Trust scores" = AI agent reliability metrics (0-1) — NOT financial credit scores
- "Tokens" = LLM API token usage — NOT cryptocurrency tokens
- "Governance" = AI agent governance and compliance — NOT corporate governance

You have been given ${webResults.length} real web search results. Your job is to:
1. Select the most relevant and high-quality results for the user's research query
2. Structure each selected result as a research paper/entry with proper categorization
3. Infer likely authors (from the source, host name, or snippet context — use format "Surname et al." when uncertain)
4. Write an informative abstract/summary based on the snippet and your knowledge
5. Extract or infer key findings relevant to the query
6. Assign a relevance score (0.0-1.0) based on how well the result matches the query
7. Assign a novelty score (0.0-1.0) based on how innovative or unique the contribution seems
8. Suggest concrete actions for NEXUS-OS integration
9. Include the original URL as pdfUrl/sourceUrl

Return your response as a JSON array of research results. Each result MUST have this exact structure:
{
  "title": "Title of the research finding or paper",
  "summary": "2-3 sentence summary of the research insight",
  "relevanceScore": 0.0-1.0,
  "noveltyScore": 0.0-1.0,
  "domain": "relevant domain category (e.g. Safety, Evaluation, Agents, RAG, Architecture, Tools)",
  "category": "same as domain — category for display",
  "keyFindings": ["finding1", "finding2", ...],
  "suggestedActions": ["action1", "action2", ...],
  "citations": ["citation1 — Author et al., Year", ...],
  "authors": ["Author1 et al.", "Author2 et al."],
  "abstract": "Detailed abstract based on the snippet and your knowledge",
  "year": 2024,
  "pdfUrl": "original URL from search result",
  "sourceUrl": "original URL from search result",
  "hostName": "source host name",
  "citationCount": estimated_number,
  "researchRole": "safety|evaluation|benchmark|memory|implementation|harness"
}

Generate at most ${clampedResults} results, selecting the most relevant from the search results. Return ONLY the JSON array, no markdown fences or extra text.`

      userPrompt = `Research query: "${query.trim()}"\n\nReal web search results:\n${searchContext}`
    } else {
      // ── Fallback: Pure AI generation (no web results available) ──
      systemPrompt = `You are a research search assistant for NEXUS OS v3.1, a multi-agent AI governance platform. Your task is to generate structured research insights based on the user's query.${domainContext}

${depthInstructions[depth] || depthInstructions.medium}

IMPORTANT CONTEXT about NEXUS OS terminology:
- "Vault" = 5-track memory plane (event, trust, capability, failure_pattern, governance) — NOT a financial vault
- "Trust scores" = AI agent reliability metrics (0-1) — NOT financial credit scores
- "Tokens" = LLM API token usage — NOT cryptocurrency tokens
- "Governance" = AI agent governance and compliance — NOT corporate governance

IMPORTANT: Since no web search results were available, generate research entries based on your knowledge of real, published research papers and findings in the relevant field. Use ACTUAL paper titles, authors, and findings where possible. Do NOT fabricate arXiv IDs or DOIs — use "N/A" for URLs you are not certain about.

Return your response as a JSON array of research results. Each result MUST have this exact structure:
{
  "title": "Title of an actual or well-known research paper/finding",
  "summary": "2-3 sentence summary of the research insight",
  "relevanceScore": 0.0-1.0,
  "noveltyScore": 0.0-1.0,
  "domain": "relevant domain category (e.g. Safety, Evaluation, Agents, RAG, Architecture, Tools)",
  "category": "same as domain — category for display",
  "keyFindings": ["finding1", "finding2", ...],
  "suggestedActions": ["action1", "action2", ...],
  "citations": ["citation1 — Author et al., Year", ...],
  "authors": ["Author1 et al.", "Author2 et al."],
  "abstract": "Detailed abstract of the research",
  "year": 2024,
  "pdfUrl": "URL if known, or N/A",
  "sourceUrl": "URL if known, or N/A",
  "citationCount": estimated_number,
  "researchRole": "safety|evaluation|benchmark|memory|implementation|harness"
}

Generate exactly ${clampedResults} results. Return ONLY the JSON array, no markdown fences or extra text.`

      userPrompt = `Research query: ${query.trim()}`
    }

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      thinking: { type: 'disabled' },
      temperature: 0.3, // Lower temperature for more factual, structured output
    })

    const rawResponse = completion.choices[0]?.message?.content || ''
    const latencyMs = Date.now() - startTime
    const model = completion.model || 'glm-4.7'

    // ── Parse the JSON response ──
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

    // ── Enrich results with metadata and map web search data back ──
    const enrichedResults = results.slice(0, clampedResults).map((r, index) => {
      // Try to match with web search result for additional data
      const webMatch = webResults.find(w =>
        r.pdfUrl === w.url ||
        r.sourceUrl === w.url ||
        r.title.toLowerCase().includes(w.name.toLowerCase().slice(0, 30)) ||
        w.name.toLowerCase().includes(r.title.toLowerCase().slice(0, 30))
      )

      const relevanceScore = typeof r.relevanceScore === 'number'
        ? Math.min(1, Math.max(0, r.relevanceScore))
        : 0.5

      const noveltyScore = typeof r.noveltyScore === 'number'
        ? Math.min(1, Math.max(0, r.noveltyScore))
        : relevanceScore * 0.8

      return {
        ...r,
        id: `research-${Date.now()}-${index}`,
        relevanceScore,
        noveltyScore,
        domain: r.domain || r.category || domain || 'general',
        category: r.category || r.domain || domain || 'general',
        // Prefer web search data when available
        authors: r.authors && r.authors.length > 0
          ? r.authors
          : (webMatch ? [webMatch.host_name.replace(/\.\w+$/, '') + ' Team'] : ['AI Research']),
        abstract: r.abstract || r.summary || '',
        year: r.year || (webMatch?.date ? new Date(webMatch.date).getFullYear() : new Date().getFullYear()),
        pdfUrl: r.pdfUrl || (webMatch?.url !== 'N/A' ? webMatch?.url : undefined),
        sourceUrl: r.sourceUrl || (webMatch?.url !== 'N/A' ? webMatch?.url : undefined),
        hostName: r.hostName || webMatch?.host_name || '',
        citationCount: r.citationCount ?? (r.citations?.length || 0),
        researchRole: r.researchRole || r.domain || 'research',
      }
    })

    // ── Build sources metadata ──
    const dbCount = enrichedResults.filter(r => r.hostName).length
    const arxivCount = enrichedResults.filter(r =>
      r.sourceUrl?.includes('arxiv') || r.pdfUrl?.includes('arxiv')
    ).length

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
          webSearchUsed: webResults.length > 0,
          webSearchCount: webResults.length,
        },
        sources: {
          database: dbCount,
          arxiv: arxivCount,
          aiSuggestions: enrichedResults.length - dbCount,
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
