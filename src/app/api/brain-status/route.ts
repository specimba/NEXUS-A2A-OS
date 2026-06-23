import { NextResponse } from 'next/server'
import { BRAIN_API_ROUTES } from '@/lib/brain-api/contract'
import { probeReadOnlyBrainRoutes, summarizeBrainProbes } from '@/lib/brain-api/probe'

export async function GET() {
  const probes = await probeReadOnlyBrainRoutes()
  const summary = summarizeBrainProbes(probes)
  const deferred = BRAIN_API_ROUTES
    .filter((route) => route.kind !== 'read' || route.method !== 'GET')
    .map((route) => ({
      id: route.id,
      method: route.method,
      path: route.path,
      lane: route.lane,
      status: 'UNKNOWN',
      httpStatus: null,
      contentType: '',
      reason: 'not probed because route is mutating or websocket',
    }))

  return NextResponse.json({
    ...summary,
    probedAt: new Date().toISOString(),
    routes: [...probes, ...deferred],
  })
}
