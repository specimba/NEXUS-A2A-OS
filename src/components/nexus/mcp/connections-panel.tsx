'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plug,
  PlugZap,
  Loader2,
  AlertTriangle,
  Plus,
  Trash2,
  Pencil,
  RefreshCw,
  Activity,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { trackEvent } from '../posthog-provider'
import { cn } from '@/lib/utils'
import { jsonFetcher, safeArray, ApiError } from '@/lib/mcp-fetcher'

type Status = 'connected' | 'connecting' | 'disconnected' | 'error'

interface ConnectionDTO {
  id: string
  name: string
  endpoint: string
  transport: 'websocket' | 'sse' | 'http'
  status: Status
  lastError: string | null
  topicMap: Record<string, string>
  autoReconnect: boolean
  enabled: boolean
  hasApiKey: boolean
  totalEvents: number
  errorCount: number
  lastEventAt: string | null
  connectedAt: string | null
}

export function ConnectionsPanel() {
  // jsonFetcher throws on non-OK so SWR's `error` channel actually fires;
  // safeArray() then guarantees the panel never tries `.map()` on `{error: ...}`.
  const { data, isLoading, mutate, error } = useSWR<ConnectionDTO[]>(
    '/api/mcp/connections',
    jsonFetcher,
    { refreshInterval: 5000, shouldRetryOnError: true, errorRetryInterval: 5000 },
  )
  const connections = safeArray<ConnectionDTO>(data)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<ConnectionDTO | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function handleConnect(c: ConnectionDTO) {
    setBusyId(c.id)
    trackEvent('mcp.connect_clicked', { id: c.id, transport: c.transport })
    try {
      const res = await fetch(`/api/mcp/connections/${c.id}/connect`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      toast.success(`Connected ${c.name}`)
      mutate()
    } catch {
      toast.error(`Failed to connect ${c.name}`)
    } finally {
      setBusyId(null)
    }
  }

  async function handleDisconnect(c: ConnectionDTO) {
    setBusyId(c.id)
    trackEvent('mcp.disconnect_clicked', { id: c.id })
    try {
      const res = await fetch(`/api/mcp/connections/${c.id}/disconnect`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      toast.success(`Disconnected ${c.name}`)
      mutate()
    } catch {
      toast.error(`Failed to disconnect ${c.name}`)
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(c: ConnectionDTO) {
    if (!confirm(`Delete connection "${c.name}"? Event history will be removed.`)) return
    try {
      const res = await fetch(`/api/mcp/connections/${c.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      toast.success(`Deleted ${c.name}`)
      mutate()
    } catch {
      toast.error('Failed to delete')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="h-4 w-4 text-emerald-500" />
          {connections.filter((c) => c.status === 'connected').length} of {connections.length} connections live
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => mutate()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setEditing(null)
              setEditorOpen(true)
            }}
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" /> New connection
          </Button>
        </div>
      </div>

      {error && connections.length === 0 ? (
        <Card className="p-8 border-destructive/40 bg-destructive/5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <div className="space-y-1 min-w-0">
              <h3 className="font-semibold text-destructive">Unable to load connections</h3>
              <p className="text-sm text-muted-foreground">
                {error instanceof ApiError
                  ? `API responded ${error.status}: ${error.message}`
                  : 'Network error — check the dev server and database.'}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Common cause locally:{' '}
                <code className="px-1 py-0.5 rounded bg-muted">DATABASE_URL</code> not set, or
                Prisma client stale. Retry after restarting the dev server.
              </p>
              <Button size="sm" variant="outline" className="mt-3" onClick={() => mutate()}>
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry
              </Button>
            </div>
          </div>
        </Card>
      ) : isLoading && connections.length === 0 ? (
        <Card className="p-12 flex items-center justify-center text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading connections…
        </Card>
      ) : connections.length === 0 ? (
        <EmptyState onCreate={() => setEditorOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <AnimatePresence>
            {connections.map((c) => (
              <motion.div
                key={c.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ duration: 0.2 }}
              >
                <ConnectionCard
                  c={c}
                  busy={busyId === c.id}
                  onConnect={() => handleConnect(c)}
                  onDisconnect={() => handleDisconnect(c)}
                  onDelete={() => handleDelete(c)}
                  onEdit={() => {
                    setEditing(c)
                    setEditorOpen(true)
                  }}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <ConnectionEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        connection={editing}
        onSaved={() => {
          mutate()
          setEditorOpen(false)
        }}
      />
    </div>
  )
}

function ConnectionCard({
  c,
  busy,
  onConnect,
  onDisconnect,
  onDelete,
  onEdit,
}: {
  c: ConnectionDTO
  busy: boolean
  onConnect: () => void
  onDisconnect: () => void
  onDelete: () => void
  onEdit: () => void
}) {
  const isLive = c.status === 'connected'
  return (
    <Card className="p-4 flex flex-col gap-3 hover:border-emerald-500/40 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <StatusDot status={c.status} />
            <h3 className="font-semibold truncate">{c.name}</h3>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono mt-0.5">{c.endpoint}</p>
        </div>
        <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
          {c.transport}
        </Badge>
      </div>

      {c.lastError && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span className="truncate" title={c.lastError}>
            {c.lastError}
          </span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <Stat label="Events" value={c.totalEvents.toLocaleString()} />
        <Stat label="Errors" value={c.errorCount.toLocaleString()} accent={c.errorCount > 0 ? 'warn' : undefined} />
        <Stat label="Last" value={c.lastEventAt ? timeAgo(c.lastEventAt) : '—'} />
      </div>

      <Separator />

      <div className="flex items-center gap-2">
        {isLive ? (
          <Button size="sm" variant="outline" className="flex-1" onClick={onDisconnect} disabled={busy}>
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <WifiOff className="h-3.5 w-3.5" />}
            <span className="ml-1.5">Disconnect</span>
          </Button>
        ) : (
          <Button size="sm" className="flex-1" onClick={onConnect} disabled={busy || !c.enabled}>
            {busy || c.status === 'connecting' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Wifi className="h-3.5 w-3.5" />
            )}
            <span className="ml-1.5">{c.status === 'connecting' ? 'Connecting…' : 'Connect'}</span>
          </Button>
        )}
        <Button size="icon" variant="ghost" onClick={onEdit} aria-label="Edit connection">
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button size="icon" variant="ghost" onClick={onDelete} aria-label="Delete connection" className="text-destructive hover:text-destructive">
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </Card>
  )
}

function StatusDot({ status }: { status: Status }) {
  const styles: Record<Status, string> = {
    connected: 'bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.6)]',
    connecting: 'bg-amber-500',
    disconnected: 'bg-muted-foreground/40',
    error: 'bg-destructive',
  }
  return (
    <span className="relative flex h-2.5 w-2.5">
      {status === 'connected' && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
      )}
      <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', styles[status])} />
    </span>
  )
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: 'warn' }) {
  return (
    <div className="rounded-md bg-muted/40 px-2 py-1.5">
      <div className={cn('text-sm font-semibold tabular-nums', accent === 'warn' && 'text-amber-500')}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
    </div>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card className="p-12 flex flex-col items-center justify-center gap-3 text-center">
      <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
        <PlugZap className="h-6 w-6 text-emerald-500" />
      </div>
      <h3 className="text-lg font-semibold">No MCP connections yet</h3>
      <p className="text-sm text-muted-foreground max-w-md">
        Configure an endpoint to start streaming Model Context Protocol events into the Nexus event log.
      </p>
      <Button onClick={onCreate} className="mt-2">
        <Plus className="h-3.5 w-3.5 mr-1.5" /> Add your first connection
      </Button>
    </Card>
  )
}

function ConnectionEditor({
  open,
  onOpenChange,
  connection,
  onSaved,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  connection: ConnectionDTO | null
  onSaved: () => void
}) {
  const [name, setName] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [transport, setTransport] = useState<'websocket' | 'sse' | 'http'>('websocket')
  const [apiKey, setApiKey] = useState('')
  const [autoReconnect, setAutoReconnect] = useState(true)
  const [enabled, setEnabled] = useState(true)
  const [saving, setSaving] = useState(false)

  // Reset form when connection changes (open dialog / edit different row)
  useEffect(() => {
    if (open) {
      setName(connection?.name ?? '')
      setEndpoint(connection?.endpoint ?? '')
      setTransport((connection?.transport as 'websocket' | 'sse' | 'http') ?? 'websocket')
      setApiKey('')
      setAutoReconnect(connection?.autoReconnect ?? true)
      setEnabled(connection?.enabled ?? true)
    }
  }, [open, connection])

  async function handleSave() {
    if (!name.trim() || !endpoint.trim()) {
      toast.error('Name and endpoint are required')
      return
    }
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        name,
        endpoint,
        transport,
        autoReconnect,
        enabled,
      }
      if (apiKey.trim()) body.apiKey = apiKey.trim()

      const res = connection
        ? await fetch(`/api/mcp/connections/${connection.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
        : await fetch('/api/mcp/connections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
      if (!res.ok) throw new Error(await res.text())
      toast.success(connection ? 'Connection updated' : 'Connection created')
      trackEvent(connection ? 'mcp.connection_updated' : 'mcp.connection_created', { transport })
      onSaved()
    } catch {
      toast.error('Failed to save connection')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{connection ? 'Edit connection' : 'New MCP connection'}</DialogTitle>
          <DialogDescription>
            Configure how Nexus reaches this Model Context Protocol endpoint. Keys are stored encrypted server-side and never returned to the browser.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="mcp-name">Name</Label>
            <Input id="mcp-name" placeholder="e.g. Composio Tools" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="mcp-endpoint">Endpoint</Label>
            <Input
              id="mcp-endpoint"
              placeholder="wss://mcp.example.com/stream"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="font-mono"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <Label>Transport</Label>
              <Select value={transport} onValueChange={(v) => setTransport(v as 'websocket' | 'sse' | 'http')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="websocket">WebSocket</SelectItem>
                  <SelectItem value="sse">Server-Sent Events</SelectItem>
                  <SelectItem value="http">HTTP polling</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="mcp-key">API key {connection?.hasApiKey ? <span className="text-xs text-muted-foreground">(leave blank to keep)</span> : null}</Label>
              <Input
                id="mcp-key"
                type="password"
                placeholder={connection?.hasApiKey ? '••••••••' : 'Optional'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="font-mono"
              />
            </div>
          </div>
          <div className="flex items-center justify-between rounded-lg border px-3 py-2">
            <div>
              <Label htmlFor="auto-reconnect" className="text-sm">Auto-reconnect</Label>
              <p className="text-xs text-muted-foreground">Retry with exponential backoff on disconnect</p>
            </div>
            <Switch id="auto-reconnect" checked={autoReconnect} onCheckedChange={setAutoReconnect} />
          </div>
          <div className="flex items-center justify-between rounded-lg border px-3 py-2">
            <div>
              <Label htmlFor="enabled" className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">Disabled connections won&apos;t auto-reconnect or be probed</p>
            </div>
            <Switch id="enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Plug className="h-3.5 w-3.5 mr-1.5" />}
            {connection ? 'Save changes' : 'Create connection'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 1000) return 'now'
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  return `${Math.floor(h / 24)}d`
}
