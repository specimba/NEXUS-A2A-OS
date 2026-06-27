'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  Clock,
  GitBranch,
  Globe2,
  Loader2,
  Network,
  RadioTower,
  Shield,
  Users,
  WifiOff,
  Zap,
} from 'lucide-react'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge, type DataSource } from '@/components/nexus/data-source-badge'

interface NexusClawStats {
  agentPool: {
    total: number
    online: number
    busy: number
    error: number
  }
  brainstorm: {
    activeSessions: number
    totalProposals: number
    pendingVotes: number
  }
  memoryChannels?: {
    episodic: number
    task: number
    trust: number
  }
  trustEngine: {
    avgTrust: number
    degradedAgents: number
  }
}

interface LocalProbe {
  id: string
  label: string
  port: number
  expectedOwner: string
  url: string
  status: 'live' | 'offline' | 'error'
  latencyMs?: number
  statusCode?: number
  error?: string
}

interface BrowserAiBridgeStatus {
  status: 'live' | 'offline' | 'error'
  version: string
  server: string
  toolCount: number
  queue: {
    pending: number
    claimed: number
    done: number
    failed: number
  }
  registrySchemaHash: string
  l1RegistrySchemaHash: boolean
  l3OutputTaint: boolean
  allowedHostCount: number
  privateTargetsBlocked: boolean
}


interface SupervisorProfileStatus {
  sourceId: string
  cadenceSeconds: number
  requiresBridge: boolean
  cdpPort?: number
  urlHint?: string
  active: boolean
}

interface SupervisorMemoryStatus {
  path: string
  exists: boolean
  lastAction?: string
  lastRunId?: string
  lastSourceId?: string
  lastCompletedAt?: string
  lastBlocker?: string | null
  providerCallsLastRecord?: number
}

interface BrowserAiSupervisorStatus {
  status: 'memory-backed' | 'awaiting-memory'
  profiles: SupervisorProfileStatus[]
  memories: SupervisorMemoryStatus[]
  activeMemory?: SupervisorMemoryStatus
  rules: {
    noopUnchangedProviderCalls: number
    setupBlockerProviderCalls: number
    maxProviderCallsPerMaterialDelta: number
    providerCooldownSeconds: number
    maxProviderCallsPerHourPerSource: number
  }
}interface NexusClawStatus {
  status: 'operational' | 'degraded' | 'halted'
  source?: 'brain-api' | 'local-probe' | 'fallback'
  brainApiLive?: boolean
  stats: NexusClawStats
  browserAiBridge?: BrowserAiBridgeStatus
  browserAiSupervisor?: BrowserAiSupervisorStatus
  localProbes?: LocalProbe[]
  routing?: Record<string, string>
  controls?: Record<string, boolean | number | string>
  warnings?: string[]
  timestamp?: string
}

function getStatusColor(status: string) {
  switch (status) {
    case 'operational': return 'text-emerald-400'
    case 'degraded': return 'text-yellow-400'
    default: return 'text-red-400'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'operational': return CheckCircle2
    case 'degraded': return AlertTriangle
    default: return Shield
  }
}

function mapDataSource(source?: NexusClawStatus['source']): DataSource {
  if (source === 'brain-api') return 'live'
  if (source === 'local-probe') return 'computed'
  return 'mock'
}

function percentFromTrust(value: number) {
  return value <= 1 ? Math.round(value * 100) : Math.round(value)
}

function probeBadgeClass(status: LocalProbe['status']) {
  if (status === 'live') return 'bg-emerald-600/15 text-emerald-500 border-emerald-600/20'
  if (status === 'error') return 'bg-yellow-600/15 text-yellow-500 border-yellow-600/20'
  return 'bg-red-600/15 text-red-500 border-red-600/20'
}

function compactStatus(status: LocalProbe['status']) {
  return status === 'live' ? 'LIVE' : status === 'error' ? 'ERROR' : 'OFFLINE'
}

export function NexusClawTab() {
  const { data: nexusclaw } = useApiData<NexusClawStatus>('/api/nexusclaw/status', 5000)

  if (!nexusclaw) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  const StatusIcon = getStatusIcon(nexusclaw.status)
  const source = mapDataSource(nexusclaw.source)
  const bridge = nexusclaw.browserAiBridge
  const supervisor = nexusclaw.browserAiSupervisor
  const grokProfile = supervisor?.profiles.find((profile) => profile.sourceId === 'grok-project-nexus')
  const queue = bridge?.queue ?? { pending: 0, claimed: 0, done: 0, failed: 0 }
  const trustPercent = percentFromTrust(nexusclaw.stats.trustEngine.avgTrust)
  const probes = nexusclaw.localProbes ?? []
  const liveProbes = probes.filter((probe) => probe.status === 'live').length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 via-emerald-500 to-slate-900 shadow-lg shadow-emerald-500/10">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">NEXUSCLAW Control Center</h2>
            <p className="text-sm text-muted-foreground">
              Governed browser-AI, Hermes/GMR, Chimera, and ModelRelay coordination
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DataSourceBadge source={source} />
          <Badge className={cn(
            'border-0 uppercase',
            nexusclaw.status === 'operational' ? 'bg-emerald-600/15 text-emerald-500' :
            nexusclaw.status === 'degraded' ? 'bg-yellow-600/15 text-yellow-500' :
            'bg-red-600/15 text-red-500'
          )}>
            <StatusIcon className="mr-1 h-3 w-3" />
            {nexusclaw.status}
          </Badge>
        </div>
      </div>

      {!!nexusclaw.warnings?.length && (
        <Card className="border-yellow-600/25 bg-yellow-950/10">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm text-yellow-300">
              <AlertTriangle className="h-4 w-4" />
              Honest Degradation Notes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-yellow-100/80">
            {nexusclaw.warnings.map((warning) => (
              <p key={warning}>- {warning}</p>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-cyan-600/20 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <RadioTower className="h-4 w-4 text-cyan-500" />
              Browser-AI MCP Bridge
              <DataSourceBadge source={bridge?.status === 'live' ? 'live' : source} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-border/60 p-3">
                <p className="text-xs text-muted-foreground">Server</p>
                <p className="truncate font-mono text-sm">{bridge?.server ?? 'unknown'}</p>
                <p className="mt-1 text-xs text-muted-foreground">v{bridge?.version ?? 'unknown'}</p>
              </div>
              <div className="rounded-lg border border-border/60 p-3">
                <p className="text-xs text-muted-foreground">MCP Tools</p>
                <p className="text-2xl font-bold text-cyan-400">{bridge?.toolCount ?? 0}</p>
              </div>
              <div className="rounded-lg border border-border/60 p-3">
                <p className="text-xs text-muted-foreground">Queue Pending</p>
                <p className="text-2xl font-bold text-amber-400">{queue.pending}</p>
                <p className="mt-1 text-xs text-muted-foreground">claimed {queue.claimed} / done {queue.done}</p>
              </div>
              <div className="rounded-lg border border-border/60 p-3">
                <p className="text-xs text-muted-foreground">HTTP Hands</p>
                <p className="text-2xl font-bold text-emerald-400">{bridge?.allowedHostCount ?? 0}</p>
                <p className="mt-1 text-xs text-muted-foreground">allowlisted hosts</p>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Badge variant="outline" className={bridge?.l1RegistrySchemaHash ? 'border-emerald-600/30 text-emerald-400' : 'border-red-600/30 text-red-400'}>
                L1 schema hash {bridge?.l1RegistrySchemaHash ? 'active' : 'missing'}
              </Badge>
              <Badge variant="outline" className={bridge?.l3OutputTaint ? 'border-emerald-600/30 text-emerald-400' : 'border-red-600/30 text-red-400'}>
                L3 taint {bridge?.l3OutputTaint ? 'active' : 'missing'}
              </Badge>
              <Badge variant="outline" className={bridge?.privateTargetsBlocked ? 'border-emerald-600/30 text-emerald-400' : 'border-red-600/30 text-red-400'}>
                private egress {bridge?.privateTargetsBlocked ? 'blocked' : 'unknown'}
              </Badge>
            </div>
            {bridge?.registrySchemaHash && (
              <p className="text-xs text-muted-foreground">Registry schema hash: <span className="font-mono">{bridge.registrySchemaHash}</span></p>
            )}
          </CardContent>
        </Card>

        <Card className="border-emerald-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Shield className="h-4 w-4 text-emerald-500" />
              Governance Contract
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span>7352 Brain API only</span>
              <Badge className="border-0 bg-emerald-600/15 text-emerald-500">LOCKED</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Broad polling</span>
              <Badge className="border-0 bg-emerald-600/15 text-emerald-500">DISABLED</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Browser tool execution</span>
              <Badge className="border-0 bg-yellow-600/15 text-yellow-500">PROPOSAL ONLY</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Fingerprint memory gate</span>
              <Badge className="border-0 bg-cyan-600/15 text-cyan-400">REQUIRED</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-cyan-600/20 bg-cyan-950/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Zap className="h-4 w-4 text-cyan-400" />
            Browser-AI Supervisor Lane
            <DataSourceBadge source={supervisor?.status === 'memory-backed' ? 'computed' : 'mock'} />
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-4">
          <div className="rounded-lg border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Supervisor State</p>
            <p className="text-lg font-semibold text-cyan-300">{supervisor?.status ?? 'unknown'}</p>
            <p className="mt-1 text-xs text-muted-foreground">{supervisor?.activeMemory?.path ?? 'no JSONL memory found'}</p>
          </div>
          <div className="rounded-lg border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Grok Cadence</p>
            <p className="text-lg font-semibold text-emerald-300">{grokProfile ? `${Math.round(grokProfile.cadenceSeconds / 60)} min` : 'unknown'}</p>
            <p className="mt-1 text-xs text-muted-foreground">CDP {grokProfile?.cdpPort ?? 'n/a'} - bridge required {grokProfile?.requiresBridge ? 'yes' : 'no'}</p>
          </div>
          <div className="rounded-lg border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Last Action</p>
            <p className="truncate text-lg font-semibold text-amber-300">{supervisor?.activeMemory?.lastAction || 'none'}</p>
            <p className="mt-1 text-xs text-muted-foreground">provider calls {supervisor?.activeMemory?.providerCallsLastRecord ?? 0}</p>
          </div>
          <div className="rounded-lg border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Provider Guard</p>
            <p className="text-lg font-semibold text-emerald-300">1 max</p>
            <p className="mt-1 text-xs text-muted-foreground">cooldown {Math.round((supervisor?.rules.providerCooldownSeconds ?? 0) / 60)} min - unchanged = 0 calls</p>
          </div>
        </CardContent>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-purple-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Network className="h-4 w-4 text-purple-500" />
              Port Ownership Doctor
              <DataSourceBadge source="computed" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {probes.map((probe) => (
              <div key={probe.id} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-sm">{probe.port}</p>
                    <p className="truncate text-sm font-medium">{probe.label}</p>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">{probe.expectedOwner}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {probe.latencyMs !== undefined && <span className="text-xs text-muted-foreground">{probe.latencyMs}ms</span>}
                  <Badge variant="outline" className={probeBadgeClass(probe.status)}>{compactStatus(probe.status)}</Badge>
                </div>
              </div>
            ))}
            {!probes.length && (
              <div className="flex items-center gap-2 rounded-lg border border-border/60 p-3 text-sm text-muted-foreground">
                <WifiOff className="h-4 w-4" />
                No local probes returned from the dashboard API.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-blue-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <GitBranch className="h-4 w-4 text-blue-500" />
              Routing Chain
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(nexusclaw.routing ?? {}).map(([lane, state]) => (
              <div key={lane} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2">
                <span className="text-sm capitalize">{lane.replace(/([A-Z])/g, ' $1')}</span>
                <span className="max-w-[60%] text-right text-xs text-muted-foreground">{state}</span>
              </div>
            ))}
            {!nexusclaw.routing && (
              <p className="text-sm text-muted-foreground">Routing metadata is unavailable from the current status source.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-purple-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-purple-500" />
              Agent Pool
              <DataSourceBadge source={source} />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-3 text-center">
              <div>
                <p className="text-2xl font-bold">{nexusclaw.stats.agentPool.total}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-500">{nexusclaw.stats.agentPool.online}</p>
                <p className="text-xs text-muted-foreground">Online</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-amber-500">{nexusclaw.stats.agentPool.busy}</p>
                <p className="text-xs text-muted-foreground">Busy</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-500">{nexusclaw.stats.agentPool.error}</p>
                <p className="text-xs text-muted-foreground">Error</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">Live probes: {liveProbes}/{probes.length}</p>
          </CardContent>
        </Card>

        <Card className="border-emerald-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Shield className="h-4 w-4 text-emerald-500" />
              Trust Engine
              <DataSourceBadge source={source} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm">Average Trust</span>
                <span className="font-mono text-sm">{trustPercent}%</span>
              </div>
              <Progress value={trustPercent} className="h-2" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Degraded Agents</span>
              <Badge className="border-0 bg-yellow-600/15 text-yellow-500">
                {nexusclaw.stats.trustEngine.degradedAgents}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-600/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-amber-500" />
              Work Queue
              <DataSourceBadge source={bridge?.status === 'live' ? 'live' : source} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between"><span>Pending</span><span className="font-mono">{queue.pending}</span></div>
            <div className="flex items-center justify-between"><span>Claimed</span><span className="font-mono">{queue.claimed}</span></div>
            <div className="flex items-center justify-between"><span>Done</span><span className="font-mono">{queue.done}</span></div>
            <div className="flex items-center justify-between"><span>Failed</span><span className="font-mono">{queue.failed}</span></div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> Updated {nexusclaw.timestamp ? new Date(nexusclaw.timestamp).toLocaleTimeString() : 'unknown'}</span>
        <span className="inline-flex items-center gap-1"><Zap className="h-3 w-3" /> Refresh 5s</span>
        <span className="inline-flex items-center gap-1"><Globe2 className="h-3 w-3" /> Browser sources remain advisory until local verification passes</span>
      </div>
    </div>
  )
}
