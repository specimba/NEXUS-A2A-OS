import { NextRequest, NextResponse } from 'next/server'
import { getActiveKey } from '@/lib/api-key-manager'

/**
 * Alphaxiv Research Integration API
 *
 * Fetches papers from Alphaxiv (https://www.alphaxiv.org/) using Tavily search.
 * Supports: trending papers, search by topic, paper details.
 *
 * API Key: TAVILY_API_KEY (configured in .env)
 * Tavily docs: https://docs.tavily.com/
 */

const TAVILY_API_URL = 'https://api.tavily.com/search'

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

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q') || 'AI governance multi-agent systems'
    const topic = searchParams.get('topic') || ''
    const maxResults = Math.min(parseInt(searchParams.get('max') || '10'), 20)

    const tavilyKey = getActiveKey('tavily')

    if (!tavilyKey) {
      return NextResponse.json(
        { error: 'Tavily API key not configured', hint: 'Add TAVILY_API_KEY to .env' },
        { status: 503 }
      )
    }

    // Build search query for Alphaxiv papers
    const searchQuery = topic
      ? `site:alphaxiv.org ${topic} AI research paper`
      : `site:alphaxiv.org ${query}`

    const response = await fetch(TAVILY_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: tavilyKey,
        query: searchQuery,
        max_results: maxResults,
        include_domains: ['alphaxiv.org'],
        search_depth: 'advanced',
        include_raw_content: false,
        topic: 'research',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Tavily API error:', response.status, errorText)
      return NextResponse.json(
        { error: `Tavily returned ${response.status}`, details: errorText },
        { status: response.status }
      )
    }

    const data: TavilyResponse = await response.json()

    // Transform results into a clean format
    const papers = data.results.map((r, i) => ({
      id: `alphaxiv-${Date.now()}-${i}`,
      title: r.title.replace(/ - AlphaXiv$/, '').trim(),
      url: r.url,
      snippet: r.snippet || r.content?.slice(0, 200) || '',
      relevanceScore: r.score ?? 0.5,
      source: 'alphaxiv',
      fetchedAt: new Date().toISOString(),
    }))

    return NextResponse.json({
      papers,
      query: searchQuery,
      count: papers.length,
      responseTime: data.response_time,
      provider: 'tavily-alphaxiv',
    })
  } catch (error) {
    console.error('Alphaxiv API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

/**
 * POST /api/alphaxiv — Queue papers from Alphaxiv into the research pipeline
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic, maxResults = 5 } = body as { topic?: string; maxResults?: number }

    const tavilyKey = getActiveKey('tavily')

    if (!tavilyKey) {
      return NextResponse.json(
        { error: 'Tavily API key not configured', hint: 'Add TAVILY_API_KEY to .env' },
        { status: 503 }
      )
    }

    const searchQuery = topic
      ? `site:alphaxiv.org ${topic} AI research`
      : 'site:alphaxiv.org trending AI papers'

    const response = await fetch(TAVILY_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: tavilyKey,
        query: searchQuery,
        max_results: Math.min(maxResults, 20),
        include_domains: ['alphaxiv.org'],
        search_depth: 'advanced',
        include_raw_content: false,
        topic: 'research',
      }),
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `Tavily returned ${response.status}` },
        { status: response.status }
      )
    }

    const data: TavilyResponse = await response.json()

    // Format for the research pipeline queue
    const queuedPapers = data.results.map((r, i) => ({
      externalId: `alphaxiv-${Date.now()}-${i}`,
      title: r.title.replace(/ - AlphaXiv$/, '').trim(),
      url: r.url,
      abstract: r.snippet || r.content?.slice(0, 300) || '',
      relevanceScore: Math.min(((r.score ?? 0.5) * 1.5), 1.0),
      priorityTier: (r.score ?? 0.5) > 0.7 ? 'P0' : (r.score ?? 0.5) > 0.4 ? 'P1' : 'P2',
      source: 'alphaxiv',
    }))

    return NextResponse.json({
      queued: queuedPapers,
      count: queuedPapers.length,
      topic: topic || 'trending',
      provider: 'tavily-alphaxiv',
      message: `${queuedPapers.length} papers found via Alphaxiv. Ready to add to research pipeline.`,
    })
  } catch (error) {
    console.error('Alphaxiv queue error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
