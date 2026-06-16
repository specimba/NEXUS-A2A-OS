'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import {
  Brain,
  Users,
  Activity,
  Shield,
  Zap,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
} from 'lucide-react'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'

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
  memoryChannels: {
    episodic: number
    task: number
    trust: number
  }
  trustEngine: {
    avgTrust: number
    degradedAgents: number
  }
}

interface NexusClawStatus {
  status: 'operational' | 'degraded' | 'halted'
  stats: NexusClawStats
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

export function NexusClawTab() {
  const { data: nexusclaw } = useApiData<NexusClawStatus>('/api/nexusclaw/status', 2000)

  if (!nexusclaw) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  const StatusIcon = getStatusIcon(nexusclaw.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-blue-600">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">NEXUSCLAW Orchestrator</h2>
            <p className="text-sm text-muted-foreground">Multi-agent coordination layer</p>
          </div>
        </div>
        <Badge className={cn(
          'border-0',
          nexusclaw.status === 'operational' ? 'bg-emerald-600/15 text-emerald-600' :
          nexusclaw.status === 'degraded' ? 'bg-yellow-600/15 text-yellow-600' :
          'bg-red-600/15 text-red-600'
        )}>
          <StatusIcon className="h-3 w-3 mr-1" />
          {nexusclaw.status}
        </Badge>
      </div>

      {/* Agent Pool Status */}
      <Card className="border-purple-600/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Users className="h-4 w-4 text-purple-600" />
            Agent Pool
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold">{nexusclaw.stats.agentPool.total}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">{nexusclaw.stats.agentPool.online}</p>
              <p className="text-xs text-muted-foreground">Online</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">{nexusclaw.stats.agentPool.busy}</p>
              <p className="text-xs text-muted-foreground">Busy</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{nexusclaw.stats.agentPool.error}</p>
              <p className="text-xs text-muted-foreground">Error</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Brainstorm Sessions */}
      <Card className="border-blue-600/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4 text-blue-600" />
            Brainstorm Sessions
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">Active Sessions</span>
              <Badge className="bg-blue-600/15 text-blue-600 border-0">
                {nexusclaw.stats.brainstorm.activeSessions}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Total Proposals</span>
              <Badge className="bg-blue-600/15 text-blue-600 border-0">
                {nexusclaw.stats.brainstorm.totalProposals}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Pending Votes</span>
              <Badge className="bg-yellow-600/15 text-yellow-600 border-0">
                {nexusclaw.stats.brainstorm.pendingVotes}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Trust Engine */}
      <Card className="border-emerald-600/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600" />
            Trust Engine
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Average Trust Score</span>
                <span className="text-sm font-mono">{nexusclaw.stats.trustEngine.avgTrust.toFixed(2)}</span>
              </div>
              <Progress value={nexusclaw.stats.trustEngine.avgTrust * 100} className="h-2" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Degraded Agents</span>
              <Badge className="bg-yellow-600/15 text-yellow-600 border-0">
                {nexusclaw.stats.trustEngine.degradedAgents}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}