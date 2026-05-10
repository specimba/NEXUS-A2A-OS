import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

let zaiInstance: InstanceType<typeof ZAI> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q')
    const num = Math.min(parseInt(searchParams.get('num') || '10'), 20)

    if (!query || query.trim().length === 0) {
      return NextResponse.json(
        { error: 'Query parameter "q" is required' },
        { status: 400 }
      )
    }

    const zai = await getZAI()
    const results = await zai.functions.invoke('web_search', {
      query: query,
      num,
    })

    return NextResponse.json({
      success: true,
      query,
      totalResults: results.length,
      results: results.map((r: any) => ({
        title: r.name,
        url: r.url,
        snippet: r.snippet,
        domain: r.host_name,
        date: r.date,
        rank: r.rank,
      })),
    })
  } catch (error) {
    console.error('Web search API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Search failed' },
      { status: 500 }
    )
  }
}
