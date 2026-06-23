'use client'

import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, RefreshCw, Server, ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface BrainRouteProbe {
  id: string
  method: string
  path: string
  lane: string
  status: 'LIVE' | 'MOCK' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'
  httpStatus: number | null
  reason: string
}

interface BrainStatus {
  overall: BrainRouteProbe['status']
  counts: Record<BrainRouteProbe['status'], number>
  probedAt: string
  routes: BrainRouteProbe[]
}

interface PortProbe {
  port: number
  expectedOwner: string
  status: BrainRouteProbe['status']
  httpStatus: number | null
  detectedOwner: string
  reason: string
  url: string
}

interface PortDoctor {
  status: BrainRouteProbe['status']
  checkedAt: string
  ports: PortProbe[]
  nextAction: string
}

function statusClass(status: BrainRouteProbe['status']) {
  switch (status) {
    case 'LIVE':
      return 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400'
    case 'DEGRADED':
      return 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400'
    case 'OFFLINE':
      return 'border-red-600/30 text-red-600 dark:text-red-400'
    default:
      return 'border-muted-foreground/30 text-muted-foreground'
  }
}

export function BrainStatusTab() {
  const [brain, setBrain] = useState<BrainStatus | null>(null)
  const [ports, setPorts] = useState<PortDoctor | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const [brainRes, portRes] = await Promise.all([
        fetch('/api/brain-status', { cache: 'no-store' }),
        fetch('/api/doctor/ports', { cache: 'no-store' }),
      ])
      setBrain(await brainRes.json())
      setPorts(await portRes.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const brainPort = ports?.ports.find((port) => port.port === 7352)

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/10">
            <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Brain API Status</h2>
            <p className="text-xs text-muted-foreground">Honest dashboard contract probes. No fake green health.</p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={refresh} disabled={loading}>
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-red-600/30 bg-red-600/5">
          <CardContent className="flex items-center gap-2 p-4 text-sm text-red-600 dark:text-red-400">
            <ShieldAlert className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      {brainPort && brainPort.status !== 'LIVE' && (
        <Card className="border-yellow-600/30 bg-yellow-600/5">
          <CardContent className="flex items-start gap-3 p-4">
            <AlertTriangle className="mt-0.5 h-4 w-4 text-yellow-600 dark:text-yellow-400" />
            <div>
              <p className="text-sm font-medium">Port 7352 drift detected</p>
              <p className="text-xs text-muted-foreground">
                Expected {brainPort.expectedOwner}; detected {brainPort.detectedOwner}. {brainPort.reason}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Server className="h-4 w-4" />
              Port Ownership
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {ports?.ports.map((port) => (
              <div key={port.port} className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                <div>
                  <p className="text-xs font-medium">{port.port} - {port.expectedOwner}</p>
                  <p className="text-[10px] text-muted-foreground">{port.detectedOwner}: {port.reason}</p>
                </div>
                <Badge variant="outline" className={statusClass(port.status)}>{port.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4" />
              Brain API Contract
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-2">
              {brain && Object.entries(brain.counts).map(([status, count]) => (
                <div key={status} className="rounded-lg border border-border/60 p-3 text-center">
                  <p className="text-lg font-semibold">{count}</p>
                  <p className="text-[10px] text-muted-foreground">{status}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] text-muted-foreground">
              Mutating routes and WebSocket routes are listed as UNKNOWN unless explicitly smoke-tested.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Endpoint Probes</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border/60 text-[10px] uppercase text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">Lane</th>
                <th className="py-2 pr-3">Method</th>
                <th className="py-2 pr-3">Path</th>
                <th className="py-2 pr-3">HTTP</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2">Reason</th>
              </tr>
            </thead>
            <tbody>
              {brain?.routes.map((route) => (
                <tr key={route.id} className="border-b border-border/40">
                  <td className="py-2 pr-3 text-muted-foreground">{route.lane}</td>
                  <td className="py-2 pr-3 font-mono">{route.method}</td>
                  <td className="py-2 pr-3 font-mono">{route.path}</td>
                  <td className="py-2 pr-3">{route.httpStatus ?? '-'}</td>
                  <td className="py-2 pr-3">
                    <Badge variant="outline" className={statusClass(route.status)}>{route.status}</Badge>
                  </td>
                  <td className="py-2 text-muted-foreground">{route.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
