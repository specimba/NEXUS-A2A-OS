import { NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const apiKey = process.env.NEXUS_BRAIN_API_KEY
  if (!apiKey) {
    return NextResponse.json(
      {
        status: 'degraded',
        source: 'unavailable',
        cases: [],
        reason: 'NEXUS_BRAIN_API_KEY is not configured',
      },
      { status: 503 }
    )
  }

  try {
    const caseId = new URL(request.url).searchParams.get('case_id')
    const endpoint = caseId
      ? `/api/sentinel/cases/${encodeURIComponent(caseId)}/timeline`
      : '/api/sentinel/cases'
    const response = await fetch(`${BRAIN_API_BASE}${endpoint}`, {
      headers: { 'x-api-key': apiKey },
      cache: 'no-store',
      signal: AbortSignal.timeout(4000),
    })
    if (!response.ok) {
      return NextResponse.json(
        {
          status: 'degraded',
          source: 'brain-api',
          cases: [],
          reason: `Brain API returned ${response.status}`,
        },
        { status: 503 }
      )
    }
    const body = await response.json()
    return NextResponse.json({
      status: 'live',
      source: 'brain-api',
      cases: body.cases ?? [],
      events: body.events ?? [],
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    return NextResponse.json(
      {
        status: 'degraded',
        source: 'brain-api',
        cases: [],
        reason: error instanceof Error ? error.message : 'Brain API unavailable',
      },
      { status: 503 }
    )
  }
}

