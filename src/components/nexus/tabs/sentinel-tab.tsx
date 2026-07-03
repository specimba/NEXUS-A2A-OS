'use client'

import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  GitBranch,
  Loader2,
  ShieldCheck,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type SentinelCase = {
  case_id: string
  title: string
  stage: string
  version: number
  risk_level: string
  policy_verdict?: string | null
  reason_codes: string[]
  retry_count: number
  trace_id: string
  vap_id?: string | null
  evidence_count: number
  approval_count: number
  verification_count: number
  event_count: number
  evidence_complete: boolean
  model_echo_mismatch: boolean
  updated_at: string
}

type SentinelEvent = {
  event_id: string
  case_version: number
  event_type: string
  actor_id: string
  previous_stage?: string | null
  new_stage: string
  trace_id: string
  vap_id?: string | null
  created_at: string
}

type SentinelResponse = {
  status: 'live' | 'degraded'
  source: string
  cases: SentinelCase[]
  reason?: string
  timestamp?: string
}

const stageTone: Record<string, string> = {
  CLOSURE: 'bg-emerald-500/15 text-emerald-400',
  ESCALATED: 'bg-red-500/15 text-red-400',
  HUMAN_DECISION: 'bg-amber-500/15 text-amber-400',
  VERIFICATION: 'bg-cyan-500/15 text-cyan-400',
  REWORK_REQUIRED: 'bg-orange-500/15 text-orange-400',
}

export function SentinelTab() {
  const [data, setData] = useState<SentinelResponse | null>(null)
  const [timeline, setTimeline] = useState<{ caseId: string; events: SentinelEvent[] } | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const response = await fetch('/api/sentinel', { cache: 'no-store' })
        const body = await response.json()
        if (active) setData(body)
      } catch (error) {
        if (active) {
          setData({
            status: 'degraded',
            source: 'dashboard',
            cases: [],
            reason: error instanceof Error ? error.message : 'Sentinel status unavailable',
          })
        }
      }
    }
    load()
    const timer = window.setInterval(load, 5000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const loadTimeline = async (caseId: string) => {
    try {
      const response = await fetch(`/api/sentinel?case_id=${encodeURIComponent(caseId)}`, {
        cache: 'no-store',
      })
      const body = await response.json()
      setTimeline({ caseId, events: body.events ?? [] })
    } catch {
      setTimeline({ caseId, events: [] })
    }
  }

  if (!data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  const pending = data.cases.filter((item) => item.stage === 'HUMAN_DECISION').length
  const verifying = data.cases.filter((item) => item.stage === 'VERIFICATION').length
  const escalated = data.cases.filter((item) => item.stage === 'ESCALATED').length
  const metrics = [
    { label: 'Human decisions', value: pending, icon: Clock3, tone: 'text-amber-400' },
    { label: 'Verification', value: verifying, icon: FileCheck2, tone: 'text-cyan-400' },
    { label: 'Escalated', value: escalated, icon: AlertTriangle, tone: 'text-red-400' },
  ]

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-cyan-400">
            <ShieldCheck className="h-4 w-4" />
            Governed case control
          </div>
          <h2 className="text-2xl font-semibold">NEXUS Sentinel</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Evidence-bound recovery cases, human decisions, KAIJU authorization, and verified closure.
          </p>
        </div>
        <Badge className={data.status === 'live'
          ? 'border-0 bg-emerald-500/15 text-emerald-400'
          : 'border-0 bg-red-500/15 text-red-400'}>
          {data.status === 'live' ? <CheckCircle2 className="mr-1 h-3 w-3" /> : <AlertTriangle className="mr-1 h-3 w-3" />}
          {data.status}
        </Badge>
      </div>

      {data.status === 'degraded' && (
        <Card className="border-red-500/30 bg-red-950/10">
          <CardContent className="flex items-center gap-3 p-4 text-sm text-red-200">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {data.reason || 'Brain API Sentinel routes are unavailable.'}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {metrics.map(({ label, value, icon: Icon, tone }) => (
          <Card key={label} className="border-border/60 bg-gradient-to-br from-cyan-500/5 to-transparent">
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="mt-1 text-3xl font-semibold">{value}</p>
              </div>
              <Icon className={`h-6 w-6 ${tone}`} />
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-cyan-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <GitBranch className="h-4 w-4 text-cyan-400" />
            Active case ledger
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.cases.map((item) => (
            <div key={item.case_id} className="grid gap-3 rounded-xl border border-border/60 p-4 lg:grid-cols-[1.4fr_.8fr_.6fr_1fr]">
              <div className="min-w-0">
                <p className="truncate font-medium">{item.title}</p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{item.case_id} · v{item.version}</p>
              </div>
              <div>
                <Badge className={`border-0 ${stageTone[item.stage] || 'bg-slate-500/15 text-slate-300'}`}>
                  {item.stage}
                </Badge>
                <p className="mt-2 text-xs text-muted-foreground">risk {item.risk_level}</p>
                <p className={`mt-1 text-xs ${item.evidence_complete ? 'text-emerald-400' : 'text-amber-400'}`}>
                  evidence {item.evidence_complete ? 'complete' : 'incomplete'}
                  {item.model_echo_mismatch ? ' · model mismatch' : ''}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Evidence / approvals / verification</p>
                <p className="font-mono text-sm">
                  {item.evidence_count} / {item.approval_count} / {item.verification_count}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Retries {item.retry_count}/3</p>
              </div>
              <div className="min-w-0">
                <p className="truncate font-mono text-xs text-muted-foreground">{item.vap_id || item.trace_id}</p>
                <p className="mt-2 truncate text-xs text-muted-foreground">
                  {item.reason_codes.length ? item.reason_codes.join(', ') : 'No active findings'}
                </p>
                <button
                  type="button"
                  onClick={() => loadTimeline(item.case_id)}
                  className="mt-2 text-xs font-medium text-cyan-400 hover:text-cyan-300"
                >
                  Audit timeline ({item.event_count})
                </button>
              </div>
            </div>
          ))}
          {!data.cases.length && (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              No Sentinel cases are recorded. This is an empty live state, not sample data.
            </div>
          )}
        </CardContent>
      </Card>

      {timeline && (
        <Card className="border-cyan-500/20">
          <CardHeader>
            <CardTitle className="text-sm">Audit timeline · {timeline.caseId}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {timeline.events.map((event) => (
              <div key={event.event_id} className="rounded-lg border border-border/60 p-3 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-cyan-300">{event.event_type}</span>
                  <span className="font-mono text-muted-foreground">v{event.case_version}</span>
                </div>
                <p className="mt-1 text-muted-foreground">
                  {event.previous_stage || 'START'} → {event.new_stage} · {event.actor_id}
                </p>
                <p className="mt-1 truncate font-mono text-muted-foreground">
                  {event.vap_id || event.trace_id}
                </p>
              </div>
            ))}
            {!timeline.events.length && (
              <p className="text-sm text-muted-foreground">Timeline unavailable or empty.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

