'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Zap,
  Shield,
  Router,
  Database,
  FlaskConical,
  Bug,
  Activity,
  Settings,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from 'lucide-react'

const pillars = [
  { name: 'Bridge', icon: Zap, status: 'operational', health: 100, desc: 'HMAC auth · JSON-RPC' },
  { name: 'Engine', icon: Router, status: 'operational', health: 98, desc: 'Hermes intent routing' },
  { name: 'Governor', icon: Shield, status: 'operational', health: 95, desc: 'Kaiju + TrustScorer' },
  { name: 'Vault', icon: Database, status: 'operational', health: 100, desc: '5-Track memory' },
  { name: 'GMR', icon: Router, status: 'operational', health: 92, desc: 'Model rotation' },
  { name: 'Swarm', icon: Bug, status: 'operational', health: 88, desc: 'Worker pool' },
  { name: 'Monitor', icon: Activity, status: 'operational', health: 96, desc: 'Token budget + audit' },
  { name: 'Config', icon: Settings, status: 'operational', health: 100, desc: 'Constitution' },
]

const recentActivity = [
  { time: '2s ago', event: 'Agent worker-3 completed task T-0847', type: 'success' },
  { time: '5s ago', event: 'GMR rotated to trinity-large-preview', type: 'info' },
  { time: '12s ago', event: 'Governor ALLOWED read file (scope: SELF)', type: 'info' },
  { time: '28s ago', event: 'Vault stored TRUST entry for agent-alpha', type: 'success' },
  { time: '45s ago', event: 'StressLab test ISC-023 completed: PASS', type: 'success' },
  { time: '1m ago', event: 'TokenGuard budget check: 73,450 remaining', type: 'info' },
  { time: '2m ago', event: 'Swarm worker-1 status: ERROR → recovering', type: 'warning' },
  { time: '3m ago', event: 'Bridge verified HMAC signature for agent-beta', type: 'info' },
]

export function OverviewTab() {
  return (
    <div className="space-y-6 p-6">
      {/* Top Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-emerald-600/20 bg-emerald-600/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Token Budget</p>
                <p className="text-2xl font-bold text-emerald-400">73,450</p>
                <p className="text-[10px] text-muted-foreground">of 100,000 remaining</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-emerald-600/15 flex items-center justify-center">
                <Activity className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
            <Progress value={73.45} className="mt-3 h-1.5" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Active Agents</p>
                <p className="text-2xl font-bold">3</p>
                <p className="text-[10px] text-muted-foreground">of 5 max</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-600/15 flex items-center justify-center">
                <Bug className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">StressLab Runs</p>
                <p className="text-2xl font-bold">47</p>
                <p className="text-[10px] text-muted-foreground">12 templates tested</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-orange-600/15 flex items-center justify-center">
                <FlaskConical className="h-5 w-5 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Collapse Rate</p>
                <p className="text-2xl font-bold text-red-400">23.4%</p>
                <p className="text-[10px] text-muted-foreground">↓ from 95.3% baseline</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-red-600/15 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 8-Pillar Health Grid */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">System Pillars</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map((p) => (
            <Card key={p.name} className="group hover:border-emerald-600/30 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
                    <p.icon className="h-4 w-4 text-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{p.name}</span>
                      <Badge
                        variant="secondary"
                        className="h-5 text-[10px] bg-emerald-600/15 text-emerald-400 border-0"
                      >
                        {p.health}%
                      </Badge>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{p.desc}</p>
                    <Progress value={p.health} className="mt-2 h-1" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Bottom Row: Activity Feed + Quick Stats */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Activity Feed */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Live Activity Feed</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {recentActivity.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  {item.type === 'success' && <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-emerald-400" />}
                  {item.type === 'info' && <Clock className="mt-0.5 h-3 w-3 shrink-0 text-blue-400" />}
                  {item.type === 'warning' && <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-orange-400" />}
                  <span className="flex-1 text-muted-foreground">{item.event}</span>
                  <span className="shrink-0 text-[10px] text-muted-foreground/60">{item.time}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Governance Stats</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Governor Decisions (24h)</span>
                <div className="flex gap-2">
                  <Badge className="bg-emerald-600/15 text-emerald-400 border-0 hover:bg-emerald-600/20">ALLOW 847</Badge>
                  <Badge className="bg-red-600/15 text-red-400 border-0 hover:bg-red-600/20">DENY 23</Badge>
                  <Badge className="bg-yellow-600/15 text-yellow-400 border-0 hover:bg-yellow-600/20">HOLD 5</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Trust Score Average</span>
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="h-3 w-3 text-emerald-400" />
                  <span className="text-sm font-medium text-emerald-400">0.73</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">VAP Chain Length</span>
                <span className="text-sm font-medium">1,247 entries</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">API Calls This Session</span>
                <span className="text-sm font-medium">12 / 20</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">File Writes</span>
                <span className="text-sm font-medium">8 / 30</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Concurrent Agents</span>
                <span className="text-sm font-medium">2 / 2</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
