import { NextRequest, NextResponse } from 'next/server'
import { routeRequest } from '@/lib/modelrelay/gateway'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prompt, strategy } = body as { prompt: string; strategy?: string }

    if (!prompt || typeof prompt !== 'string') {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      )
    }

    const result = routeRequest(prompt, strategy)
    return NextResponse.json(result)
  } catch (error) {
    return NextResponse.json(
      { error: 'Routing failed' },
      { status: 500 }
    )
  }
}
