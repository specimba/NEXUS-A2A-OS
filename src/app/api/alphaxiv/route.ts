import { NextRequest, NextResponse } from 'next/server'
import { getActiveKey } from '@/lib/api-key-manager'

/**
 * Alphaxiv Research Integration API
 *
 * Fetches papers from Alphaxiv (https://www.alphaxiv.org/) using Tavily search
 * with Jina AI as a fallback provider.
 * Supports: trending papers, search by topic, paper details.
 *
 * API Keys: TAVILY_API_KEY, JINA_API_KEY (configured in .env)
 * Tavily docs: https://docs.tavily.com/
 * Jina search: https://s.jina.ai/
 */

const TAVILY_API_URL = 'https://api.tavily.com/search'
const JINA_SEARCH_URL = 'https://s.jina.ai'

interface TavilyResult {
  title: string
  url: string
  content: string
  snippet?: string
  raw_content?: string
  metadata?: Record<string, string>
  score?: number
}

interface TavilyResponse {
  results: TavilyResult[]
  query: string
  response_time?: number
}

interface PaperResult {
  id: string
  title: string
  url: string
  snippet: string
  relevanceScore: number
  source: string
  fetchedAt: string
}

// ── Tavily Search ──────────────────────────────────────────────────

async function searchWithTavily(query: string, searchQuery: string, maxResults: number, tavilyKey: string): Promise<PaperResult[]> {
  const response = await fetch(TAVILY_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: tavilyKey,
      query: searchQuery,
      max_results: maxResults,
      // Removed include_domains: ['alphaxiv.org'] — too restrictive for Tavily
      search_depth: 'advanced',
      include_raw_content: false,
      topic: 'research',
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    console.error('Tavily API error:', response.status, errorText)
    return []
  }

  const data: TavilyResponse = await response.json()

  return data.results.map((r, i) => ({
    id: `alphaxiv-${Date.now()}-${i}`,
    title: r.title.replace(/ - AlphaXiv$/, '').trim(),
    url: r.url,
    snippet: r.snippet || r.content?.slice(0, 200) || '',
    relevanceScore: r.score ?? 0.5,
    source: 'tavily-alphaxiv',
    fetchedAt: new Date().toISOString(),
  }))
}

// ── Jina AI Search (Fallback) ──────────────────────────────────────

async function searchWithJina(query: string, maxResults: number, jinaKey: string): Promise<PaperResult[]> {
  try {
    const response = await fetch(`${JINA_SEARCH_URL}/${encodeURIComponent(query)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${jinaKey}`,
        'Accept': 'application/json',
      },
    })

    if (!response.ok) {
      console.error('Jina search error:', response.status)
      return []
    }

    const data = await response.json()

    // Jina returns results in data.data array
    const results = data?.data ?? []
    return results.slice(0, maxResults).map((r: { title?: string; url?: string; description?: string; content?: string }, i: number) => ({
      id: `jina-${Date.now()}-${i}`,
      title: (r.title || 'Untitled Paper').replace(/ - AlphaXiv$/, '').trim(),
      url: r.url || '',
      snippet: r.description || r.content?.slice(0, 200) || '',
      relevanceScore: 0.4 + Math.random() * 0.3, // Jina doesn't return relevance scores, estimate
      source: 'jina-fallback',
      fetchedAt: new Date().toISOString(),
    }))
  } catch (error) {
    console.error('Jina search error:', error)
    return []
  }
}

// ── GET Handler ────────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q') || 'AI governance multi-agent systems'
    const topic = searchParams.get('topic') || ''
    const maxResults = Math.min(parseInt(searchParams.get('max') || '10'), 20)

    const tavilyKey = getActiveKey('tavily')
    const jinaKey = process.env.JINA_API_KEY || ''

    if (!tavilyKey && !jinaKey) {
      return NextResponse.json(
        { error: 'No search API keys configured', hint: 'Add TAVILY_API_KEY or JINA_API_KEY to .env' },
        { status: 503 }
      )
    }

    // Build search query — broader than before (no site: restriction)
    const searchQuery = topic
      ? `alphaxiv AI research paper ${topic}`
      : `alphaxiv AI research paper ${query}`

    let papers: PaperResult[] = []
    let provider = 'none'

    // Try Tavily first
    if (tavilyKey) {
      papers = await searchWithTavily(query, searchQuery, maxResults, tavilyKey)
      provider = 'tavily-alphaxiv'

      // Fallback: if Tavily returns 0 results, try a broader query without "alphaxiv"
      if (papers.length === 0) {
        const broaderQuery = topic
          ? `AI governance research paper ${topic}`
          : `AI governance research ${query}`
        papers = await searchWithTavily(query, broaderQuery, maxResults, tavilyKey)
        if (papers.length > 0) {
          provider = 'tavily-broadened'
        }
      }
    }

    // Fallback: if Tavily still returns 0, try Jina AI
    if (papers.length === 0 && jinaKey) {
      const jinaQuery = topic
        ? `alphaxiv AI research ${topic}`
        : `alphaxiv AI research ${query}`
      papers = await searchWithJina(jinaQuery, maxResults, jinaKey)
      if (papers.length > 0) {
        provider = 'jina-fallback'
      }
    }

    // Second Jina attempt with broader query
    if (papers.length === 0 && jinaKey) {
      const broaderJinaQuery = topic
        ? `AI governance research ${topic}`
        : `AI governance research ${query}`
      papers = await searchWithJina(broaderJinaQuery, maxResults, jinaKey)
      if (papers.length > 0) {
        provider = 'jina-broadened'
      }
    }

    return NextResponse.json({
      papers,
      query: searchQuery,
      count: papers.length,
      provider,
    })
  } catch (error) {
    console.error('Alphaxiv API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

// ── POST Handler ───────────────────────────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic, maxResults = 5 } = body as { topic?: string; maxResults?: number }

    const tavilyKey = getActiveKey('tavily')
    const jinaKey = process.env.JINA_API_KEY || ''

    if (!tavilyKey && !jinaKey) {
      return NextResponse.json(
        { error: 'No search API keys configured', hint: 'Add TAVILY_API_KEY or JINA_API_KEY to .env' },
        { status: 503 }
      )
    }

    // Broader search query (no site: restriction)
    const searchQuery = topic
      ? `alphaxiv AI research paper ${topic}`
      : 'alphaxiv trending AI research papers'

    let papers: PaperResult[] = []
    let provider = 'none'

    // Try Tavily first
    if (tavilyKey) {
      papers = await searchWithTavily(topic || 'trending', searchQuery, Math.min(maxResults, 20), tavilyKey)
      provider = 'tavily-alphaxiv'

      // Fallback: broader query without "alphaxiv"
      if (papers.length === 0) {
        const broaderQuery = topic
          ? `AI governance research ${topic}`
          : 'trending AI governance research papers'
        papers = await searchWithTavily(topic || 'trending', broaderQuery, Math.min(maxResults, 20), tavilyKey)
        if (papers.length > 0) {
          provider = 'tavily-broadened'
        }
      }
    }

    // Fallback: Jina AI
    if (papers.length === 0 && jinaKey) {
      const jinaQuery = topic
        ? `alphaxiv AI research ${topic}`
        : 'alphaxiv trending AI research papers'
      papers = await searchWithJina(jinaQuery, Math.min(maxResults, 20), jinaKey)
      if (papers.length > 0) {
        provider = 'jina-fallback'
      }
    }

    // Format for the research pipeline queue
    const queuedPapers = papers.map((r) => ({
      externalId: r.id,
      title: r.title,
      url: r.url,
      abstract: r.snippet?.slice(0, 300) || '',
      relevanceScore: Math.min((r.relevanceScore * 1.5), 1.0),
      priorityTier: r.relevanceScore > 0.7 ? 'P0' : r.relevanceScore > 0.4 ? 'P1' : 'P2',
      source: provider,
    }))

    return NextResponse.json({
      queued: queuedPapers,
      count: queuedPapers.length,
      topic: topic || 'trending',
      provider,
      message: `${queuedPapers.length} papers found via ${provider}. Ready to add to research pipeline.`,
    })
  } catch (error) {
    console.error('Alphaxiv queue error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
