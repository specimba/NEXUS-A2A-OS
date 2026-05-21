'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { Send, Shield, Settings2, KeyRound, Sparkles, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { jsonFetcher, safeArray } from '@/lib/mcp-fetcher'

interface AuditEntry {
  id: string
  actor: string
  action: string
  target: string | null
  metadata: unknown
  ip: string | null
  createdAt: string
}

interface ConnectionLite {
  id: string
  name: string
  status: string
}

const POSTHOG_CONFIGURED = !!process.env.NEXT_PUBLIC_POSTHOG_KEY

export function SettingsPanel() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 space-y-4">
        <PostHogStatusCard />
        <EventSimulator />
      </div>
      <AuditLogPanel />
    </div>
  )
}

function PostHogStatusCard() {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-sky-500/10 text-sky-500 flex items-center justify-center shrink-0">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold">PostHog analytics</h3>
            <Badge variant={POSTHOG_CONFIGURED ? 'default' : 'secondary'} className="text-[10px]">
              {POSTHOG_CONFIGURED ? 'Configured' : 'Not configured'}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Set <code className="px-1 py-0.5 rounded bg-muted text-xs">NEXT_PUBLIC_POSTHOG_KEY</code> (and optionally{' '}
            <code className="px-1 py-0.5 rounded bg-muted text-xs">NEXT_PUBLIC_POSTHOG_HOST</code>) in your Vercel project to enable user-flow capture, heatmaps, and feature flags. MCP actions are auto-instrumented as <code className="px-1 py-0.5 rounded bg-muted text-xs">mcp.*</code> events.
          </p>
        </div>
      </div>
    </Card>
  )
}

function EventSimulator() {
  const { data: connectionsData } = useSWR<ConnectionLite[]>('/api/mcp/connections', jsonFetcher, {
    refreshInterval: 10000,
  })
  const connections = safeArray<ConnectionLite>(connectionsData)
  const [connectionId, setConnectionId] = useState('')
  const [topic, setTopic] = useState('tool_call')
  const [level, setLevel] = useState('info')
  const [payload, setPayload] = useState('{\n  "tool": "search",\n  "args": {"q": "nexus"}\n}')
  const [sending, setSending] = useState(false)

  async function handleSend() {
    if (!connectionId) {
      toast.error('Pick a connection first')
      return
    }
    let parsedPayload: unknown
    try {
      parsedPayload = JSON.parse(payload)
    } catch {
      toast.error('Payload is not valid JSON')
      return
    }
    setSending(true)
    try {
      const res = await fetch('/api/mcp/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connectionId, topic, level, payload: parsedPayload }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Event sent')
    } catch {
      toast.error('Failed to send event')
    } finally {
      setSending(false)
    }
  }

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3 mb-4">
        <div className="h-10 w-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
          <Settings2 className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-semibold">Event simulator</h3>
          <p className="text-sm text-muted-foreground">
            Inject events into the live stream to exercise filters, alerts, and PostHog instrumentation.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="grid gap-1.5 md:col-span-2">
            <Label className="text-xs">Connection</Label>
            <Select value={connectionId} onValueChange={setConnectionId}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Select connection…" />
              </SelectTrigger>
              <SelectContent>
                {connections.length === 0 ? (
                  <SelectItem value="__none__" disabled>
                    No connections — create one first
                  </SelectItem>
                ) : (
                  connections.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label className="text-xs">Level</Label>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="info">Info</SelectItem>
                <SelectItem value="warn">Warn</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="debug">Debug</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label className="text-xs">Topic</Label>
          <Input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="font-mono"
            placeholder="tool_call"
          />
        </div>
        <div className="grid gap-1.5">
          <Label className="text-xs">Payload (JSON)</Label>
          <Textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            className="font-mono text-xs min-h-32"
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSend} disabled={sending || !connectionId}>
            {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Send className="h-3.5 w-3.5 mr-1.5" />}
            Send event
          </Button>
        </div>
      </div>
    </Card>
  )
}

function AuditLogPanel() {
  const { data: logsData, isLoading } = useSWR<AuditEntry[]>('/api/audit?limit=50', jsonFetcher, {
    refreshInterval: 10000,
  })
  const logs = safeArray<AuditEntry>(logsData)

  return (
    <Card className="p-4 flex flex-col">
      <div className="flex items-start gap-3 mb-3">
        <div className="h-10 w-10 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0">
          <Shield className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold flex items-center gap-2">
            Audit log
            <Badge variant="secondary" className="text-[10px]">
              <KeyRound className="h-2.5 w-2.5 mr-0.5" /> Immutable
            </Badge>
          </h3>
          <p className="text-xs text-muted-foreground">Last 50 admin actions</p>
        </div>
      </div>
      <Separator className="mb-2" />
      <ScrollArea className="h-[480px] -mx-1 px-1">
        {isLoading ? (
          <div className="p-6 text-center text-xs text-muted-foreground">Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            No audit entries yet. Create or connect to an MCP endpoint to populate the log.
          </div>
        ) : (
          <ul className="space-y-1.5">
            {logs.map((l) => (
              <li key={l.id} className="rounded-md border border-border/40 px-2.5 py-1.5 hover:bg-muted/40">
                <div className="flex items-center gap-2 flex-wrap">
                  <code className="text-[11px] font-mono font-semibold text-emerald-500">{l.action}</code>
                  <span className="text-[10px] text-muted-foreground tabular-nums ml-auto">
                    {timeAgo(l.createdAt)}
                  </span>
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1.5 flex-wrap">
                  <Badge variant="outline" className="text-[10px] h-4 px-1">
                    {l.actor}
                  </Badge>
                  {l.target && <span className="font-mono truncate">target={l.target.slice(0, 12)}…</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>
    </Card>
  )
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}
