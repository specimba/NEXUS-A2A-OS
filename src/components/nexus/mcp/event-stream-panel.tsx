'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import { motion, AnimatePresence } from 'framer-motion'
import { Pause, Play, Search, Filter, Download, Trash2, Radio } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { jsonFetcher, safeArray } from '@/lib/mcp-fetcher'

interface McpEventDTO {
  id: string
  connectionId: string
  connectionName?: string
  topic: string
  level: 'info' | 'warn' | 'error' | 'debug'
  payload: unknown
  occurredAt: string
}

interface ConnectionLite {
  id: string
  name: string
  status: string
}

const MAX_BUFFER = 500

export function EventStreamPanel() {
  // Safe fetcher: if /api/mcp/connections 500s, SWR surfaces it as `error`,
  // and safeArray() ensures the <Select> below never iterates `{error: ...}`.
  const { data: connectionsData } = useSWR<ConnectionLite[]>('/api/mcp/connections', jsonFetcher, {
    refreshInterval: 10000,
  })
  const connections = safeArray<ConnectionLite>(connectionsData)
  const [connectionId, setConnectionId] = useState<string>('all')
  const [level, setLevel] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [paused, setPaused] = useState(false)
  const [events, setEvents] = useState<McpEventDTO[]>([])
  const eventsRef = useRef(events)
  eventsRef.current = events
  const pausedRef = useRef(paused)
  pausedRef.current = paused

  // Seed: load most-recent events on first render or filter change.
  useEffect(() => {
    const params = new URLSearchParams()
    if (connectionId !== 'all') params.set('connectionId', connectionId)
    if (level !== 'all') params.set('level', level)
    params.set('limit', '100')
    fetch(`/api/mcp/events?${params.toString()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: unknown) => {
        // /api/mcp/events returns an array on success; if the server is in a
        // bad state it may return {error: "..."} with a 500 — guard against
        // that so the panel doesn't crash on `events.map()` later.
        setEvents(Array.isArray(data) ? (data as McpEventDTO[]) : [])
      })
      .catch(() => {
        // Keep whatever's in the buffer; the live SSE stream will fill in once
        // the backend recovers. Surface nothing here — the global toast
        // pattern handles user-visible errors.
      })
  }, [connectionId, level])

  // Open SSE for live stream. The stream is filtered by connectionId server-side
  // (when set) and by level/search client-side so the user can flip filters
  // without reconnecting.
  useEffect(() => {
    const params = new URLSearchParams()
    if (connectionId !== 'all') params.set('connectionId', connectionId)
    const url = `/api/mcp/stream?${params.toString()}`
    const es = new EventSource(url)
    es.addEventListener('mcp', (e: MessageEvent) => {
      if (pausedRef.current) return
      try {
        const evt = JSON.parse(e.data) as McpEventDTO
        setEvents((prev) => {
          // Skip duplicates that may also arrive via the initial seed fetch.
          if (prev.some((p) => p.id === evt.id)) return prev
          const next = [evt, ...prev]
          // Keep buffer bounded — UI lists this many max anyway.
          return next.length > MAX_BUFFER ? next.slice(0, MAX_BUFFER) : next
        })
      } catch {
        /* ignore */
      }
    })
    es.onerror = () => {
      // EventSource auto-reconnects; nothing to do.
    }
    return () => {
      es.close()
    }
  }, [connectionId])

  // Local filtering by level + search box.
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return events.filter((e) => {
      if (level !== 'all' && e.level !== level) return false
      if (q) {
        const haystack = `${e.topic} ${JSON.stringify(e.payload)}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [events, level, search])

  function handleExport() {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mcp-events-${new Date().toISOString()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-3">
      <Card className="p-3 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 mr-auto">
          <Radio
            className={cn(
              'h-4 w-4',
              paused ? 'text-muted-foreground' : 'text-emerald-500',
              !paused && 'animate-pulse',
            )}
          />
          <span className="text-sm font-medium">{paused ? 'Stream paused' : 'Live stream'}</span>
          <Badge variant="secondary" className="text-[10px] tabular-nums">
            {filtered.length} / {events.length}
          </Badge>
        </div>

        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search topic or payload…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-7 w-56"
          />
        </div>

        <Select value={connectionId} onValueChange={setConnectionId}>
          <SelectTrigger className="h-8 w-40">
            <Filter className="h-3.5 w-3.5 mr-1" />
            <SelectValue placeholder="Connection" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All connections</SelectItem>
            {connections.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={level} onValueChange={setLevel}>
          <SelectTrigger className="h-8 w-32">
            <SelectValue placeholder="Level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All levels</SelectItem>
            <SelectItem value="info">Info</SelectItem>
            <SelectItem value="warn">Warn</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="debug">Debug</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" onClick={() => setPaused((p) => !p)}>
          {paused ? <Play className="h-3.5 w-3.5 mr-1" /> : <Pause className="h-3.5 w-3.5 mr-1" />}
          {paused ? 'Resume' : 'Pause'}
        </Button>
        <Button variant="outline" size="sm" onClick={handleExport} disabled={filtered.length === 0}>
          <Download className="h-3.5 w-3.5 mr-1" /> Export
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setEvents([])}
          disabled={events.length === 0}
        >
          <Trash2 className="h-3.5 w-3.5 mr-1" /> Clear
        </Button>
      </Card>

      <Card className="overflow-hidden">
        <ScrollArea className="h-[600px]">
          {filtered.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No events match the current filters. Connect an endpoint or simulate one from Settings.
            </div>
          ) : (
            <ul className="divide-y divide-border/40">
              <AnimatePresence initial={false}>
                {filtered.map((e) => (
                  <motion.li
                    key={e.id}
                    layout
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="px-4 py-2.5 hover:bg-muted/40 font-mono text-xs"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <LevelBadge level={e.level} />
                      <span className="text-muted-foreground tabular-nums">{formatTime(e.occurredAt)}</span>
                      <span className="font-semibold text-emerald-500">{e.topic}</span>
                      {e.connectionName && (
                        <Badge variant="outline" className="text-[10px] font-mono">
                          {e.connectionName}
                        </Badge>
                      )}
                    </div>
                    <pre className="mt-1 text-[11px] text-muted-foreground whitespace-pre-wrap break-words leading-snug max-h-32 overflow-hidden">
                      {formatPayload(e.payload)}
                    </pre>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          )}
        </ScrollArea>
      </Card>
    </div>
  )
}

function LevelBadge({ level }: { level: 'info' | 'warn' | 'error' | 'debug' }) {
  const styles: Record<string, string> = {
    info: 'bg-sky-500/15 text-sky-500 border-sky-500/30',
    warn: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
    error: 'bg-destructive/15 text-destructive border-destructive/30',
    debug: 'bg-muted text-muted-foreground border-border',
  }
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded px-1.5 py-0.5 border text-[10px] font-bold uppercase tracking-wider tabular-nums w-14',
        styles[level],
      )}
    >
      {level}
    </span>
  )
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3, '0')
}

function formatPayload(payload: unknown): string {
  try {
    return typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2)
  } catch {
    return String(payload)
  }
}
