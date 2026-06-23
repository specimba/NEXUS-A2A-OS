import { NextResponse } from 'next/server'
import { probeReadOnlyBrainRoutes, summarizeBrainProbes, type BrainRouteProbe } from '@/lib/brain-api/probe'
import type { BrainRouteStatus } from '@/lib/brain-api/contract'

type PanelResult = {
  relayed: boolean
  source: string
  brainApiStatus: BrainRouteStatus
  error?: string
  routes: Array<Pick<BrainRouteProbe, 'id' | 'path' | 'status' | 'httpStatus' | 'reason'>>
}

const PANEL_ROUTES: Record<string, string[]> = {
  overview: ['health', 'stats'],
  governance: ['stats'],
  trust: ['trust'],
  providers: ['providers'],
  modelrelay: ['relay-health', 'relay-ready', 'relay-metrics', 'relay-models'],
  tasks: ['tasks'],
  agents: ['agents'],
  vault: ['state'],
  research: ['wiki', 'wiki-pages', 'wiki-sources'],
  brain: ['health', 'stats'],
}

const STATUS_RANK: Record<BrainRouteStatus, number> = {
  LIVE: 0,
  MOCK: 1,
  DEGRADED: 2,
  UNKNOWN: 3,
  OFFLINE: 4,
}

function worstStatus(probes: BrainRouteProbe[]): BrainRouteStatus {
  if (probes.length === 0) return 'UNKNOWN'
  return probes.reduce<BrainRouteStatus>((worst, probe) => (
    STATUS_RANK[probe.status] > STATUS_RANK[worst] ? probe.status : worst
  ), 'LIVE')
}

function panelFromRoutes(allProbes: BrainRouteProbe[], routeIds: string[]): PanelResult {
  const routes = allProbes.filter((probe) => routeIds.includes(probe.id))
  const brainApiStatus = worstStatus(routes)
  const badRoutes = routes.filter((route) => route.status !== 'LIVE')

  return {
    relayed: brainApiStatus === 'LIVE',
    source: 'brain-api',
    brainApiStatus,
    error: badRoutes.length > 0
      ? badRoutes.map((route) => `${route.id}: ${route.reason}`).join('; ')
      : undefined,
    routes: routes.map((route) => ({
      id: route.id,
      path: route.path,
      status: route.status,
      httpStatus: route.httpStatus,
      reason: route.reason,
    })),
  }
}

export async function GET() {
  const probes = await probeReadOnlyBrainRoutes()
  const summary = summarizeBrainProbes(probes)
  const panels = Object.fromEntries(
    Object.entries(PANEL_ROUTES).map(([panel, routeIds]) => [panel, panelFromRoutes(probes, routeIds)])
  )

  return NextResponse.json({
    ...summary,
    probedAt: new Date().toISOString(),
    panels,
  })
}
