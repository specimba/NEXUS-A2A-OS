import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    status: 'operational',
    providers: 13,
    models: 24,
    healthyProviders: 5,
    degradedProviders: 3,
    unknownProviders: 6,
    totalRequests: 15420,
    successRate: 94.2,
    avgLatencyMs: 245,
    uptime: '99.7%',
    circuitBreakers: { open: 0, halfOpen: 1, closed: 13 },
    lastUpdated: new Date().toISOString(),
  })
}
