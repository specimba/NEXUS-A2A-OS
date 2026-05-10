import { NextResponse } from 'next/server'
import { getGatewayStatus } from '@/lib/modelrelay/gateway'

export async function GET() {
  try {
    const status = getGatewayStatus()
    return NextResponse.json(status)
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get gateway status' },
      { status: 500 }
    )
  }
}
