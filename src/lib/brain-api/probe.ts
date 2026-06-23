import { fetchBrainApi } from './client'
import { READ_ONLY_BRAIN_ROUTES, type BrainApiRoute, type BrainRouteStatus } from './contract'

export interface BrainRouteProbe {
  id: string
  method: BrainApiRoute['method']
  path: string
  lane: string
  status: BrainRouteStatus
  httpStatus: number | null
  contentType: string
  reason: string
}

export function classifyBrainResponse(result: {
  ok: boolean
  status: number | null
  contentType: string
  data: unknown
  textPreview: string
  error?: string
}): { status: BrainRouteStatus; reason: string } {
  if (result.error || result.status === null) {
    return { status: 'OFFLINE', reason: result.error || 'connection failed' }
  }
  if (result.contentType.includes('text/html')) {
    return { status: 'DEGRADED', reason: `unexpected HTML response (${result.status})` }
  }
  if (!result.ok) {
    return { status: 'OFFLINE', reason: `HTTP ${result.status}` }
  }
  if (!result.contentType.includes('application/json')) {
    return { status: 'DEGRADED', reason: `unexpected content type: ${result.contentType || 'none'}` }
  }
  return { status: 'LIVE', reason: 'JSON response' }
}

export async function probeBrainRoute(route: BrainApiRoute): Promise<BrainRouteProbe> {
  if (route.kind !== 'read' || route.method !== 'GET') {
    return {
      id: route.id,
      method: route.method,
      path: route.path,
      lane: route.lane,
      status: 'UNKNOWN',
      httpStatus: null,
      contentType: '',
      reason: 'not probed because route is mutating or websocket',
    }
  }

  const result = await fetchBrainApi(route.path)
  const classified = classifyBrainResponse(result)
  return {
    id: route.id,
    method: route.method,
    path: route.path,
    lane: route.lane,
    status: classified.status,
    httpStatus: result.status,
    contentType: result.contentType,
    reason: classified.reason,
  }
}

export async function probeReadOnlyBrainRoutes(): Promise<BrainRouteProbe[]> {
  return Promise.all(READ_ONLY_BRAIN_ROUTES.map((route) => probeBrainRoute(route)))
}

export function summarizeBrainProbes(probes: BrainRouteProbe[]) {
  const counts: Record<BrainRouteStatus, number> = {
    LIVE: 0,
    MOCK: 0,
    DEGRADED: 0,
    OFFLINE: 0,
    UNKNOWN: 0,
  }
  for (const probe of probes) {
    counts[probe.status] += 1
  }
  const overall: BrainRouteStatus =
    counts.LIVE > 0 && counts.DEGRADED === 0 && counts.OFFLINE === 0 ? 'LIVE' :
      counts.LIVE > 0 ? 'DEGRADED' :
        counts.DEGRADED > 0 ? 'DEGRADED' :
          counts.OFFLINE > 0 ? 'OFFLINE' :
            'UNKNOWN'
  return { overall, counts }
}
