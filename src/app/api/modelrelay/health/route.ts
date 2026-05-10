import { NextResponse } from 'next/server'
import { healthCheck } from '@/lib/modelrelay/gateway'

export async function GET() {
  try {
    const health = healthCheck()
    return NextResponse.json(health)
  } catch (error) {
    return NextResponse.json(
      { status: 'error', error: 'Health check failed' },
      { status: 500 }
    )
  }
}
