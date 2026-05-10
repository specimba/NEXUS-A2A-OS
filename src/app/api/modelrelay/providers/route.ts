import { NextResponse } from 'next/server'
import { getAllProviders, getProviderStatusSummary } from '@/lib/modelrelay/gateway'

export async function GET() {
  try {
    const providers = getAllProviders()
    const statusSummary = getProviderStatusSummary()
    return NextResponse.json({ providers, status: statusSummary })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get providers' },
      { status: 500 }
    )
  }
}
