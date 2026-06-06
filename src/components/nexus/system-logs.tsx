'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Terminal, X, ChevronDown, Trash2, Pause, Play, Download, Database, Wifi } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useApiData } from '@/hooks/use-api-data'

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'
type LogSource = 'BRIDGE' | 'ENGINE' | 'GOVERNOR' | 'VAULT' | 'GMR' | 'SWARM' | 'MONITOR' | 'CONFIG' | 'TOKENS'

interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  source: LogSource
  message: string
  metadata?: Record<string, unknown>
  isReal?: boolean // flag for real DB-sourced entries
}

const levelColors: Record<LogLevel, string> = {
  DEBUG: 'text-muted-foreground',
  INFO: 'text-blue-600 dark:text-blue-400',
  WARN: 'text-yellow-600 dark:text-yellow-400',
  ERROR: 'text-red-600 dark:text-red-400',
  CRITICAL: 'text-red-600 dark:text-red-500 font-bold',
}

const levelBgColors: Record<LogLevel, string> = {
  DEBUG: 'bg-muted/20',
  INFO: 'bg-blue-600/5',
  WARN: 'bg-yellow-600/5',
  ERROR: 'bg-red-600/10',
  CRITICAL: 'bg-red-600/15',
}

const sourceColors: Record<string, string> = {
  BRIDGE: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400',
  ENGINE: 'bg-blue-600/15 text-blue-600 dark:text-blue-400',
  GOVERNOR: 'bg-red-600/15 text-red-600 dark:text-red-400',
  VAULT: 'bg-purple-600/15 text-purple-600 dark:text-purple-400',
  GMR: 'bg-orange-600/15 text-orange-600 dark:text-orange-400',
  SWARM: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400',
  MONITOR: 'bg-pink-600/15 text-pink-600 dark:text-pink-400',
  CONFIG: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400',
  TOKENS: 'bg-teal-600/15 text-teal-600 dark:text-teal-400',
}

// Simulated log messages (fallback / live feed)
const logMessages: { level: LogLevel; source: LogSource; message: string }[] = [
  { level: 'INFO', source: 'BRIDGE', message: 'HMAC session verified for agent worker-3' },
  { level: 'INFO', source: 'ENGINE', message: 'Hermes routed request to trinity-large-preview (domain: reason)' },
  { level: 'WARN', source: 'GOVERNOR', message: 'HOLD: research-agent API call (CROSS scope) — trust 0.62 < threshold 0.70' },
  { level: 'INFO', source: 'VAULT', message: 'Stored TRUST entry V-2048 for agent-alpha (score: 0.82)' },
  { level: 'ERROR', source: 'SWARM', message: 'worker-2 error rate exceeded 34% — auto-recovery initiated' },
  { level: 'INFO', source: 'GMR', message: 'Rotated from gemma-fast to qwen3-coder (domain: code)' },
  { level: 'INFO', source: 'MONITOR', message: 'TokenGuard budget check: 73,450 of 100,000 remaining' },
  { level: 'DEBUG', source: 'CONFIG', message: 'Constitution check passed: all limits within bounds' },
  { level: 'INFO', source: 'ENGINE', message: 'Intent classified: code_generation → qwen3-coder pool' },
  { level: 'CRITICAL', source: 'GOVERNOR', message: 'DENY: worker-2 attempted "delete all vault entries" (CRIT impact, SYSTEM scope)' },
  { level: 'INFO', source: 'BRIDGE', message: 'New HMAC session established for coordinator' },
  { level: 'WARN', source: 'GMR', message: 'Model gemma-fast health check returned 88% — below 90% threshold' },
  { level: 'INFO', source: 'VAULT', message: 'Stored GOV entry V-2049: constitution.check' },
  { level: 'INFO', source: 'SWARM', message: 'worker-3 completed task T-0847 in 14.2s (3,420 tokens)' },
  { level: 'DEBUG', source: 'MONITOR', message: 'API call count: 12/20, file writes: 8/30, concurrent: 2/2' },
  { level: 'INFO', source: 'ENGINE', message: 'Routing escalation: security domain → PREMIUM pool' },
  { level: 'ERROR', source: 'SWARM', message: 'worker-2 rate limit hit: E-RATE-429 from gemma-fast endpoint' },
  { level: 'INFO', source: 'BRIDGE', message: 'Agent worker-1 authenticated via HMAC-SHA256' },
  { level: 'WARN', source: 'MONITOR', message: 'Token burn rate elevated: 142 tok/min (avg: 98 tok/min)' },
  { level: 'INFO', source: 'GMR', message: 'FREE_RESEARCH pool: all models within rate limits' },
]

let logCounter = 0

function generateSimulatedEntry(): LogEntry {
  const template = logMessages[logCounter % logMessages.length]
  logCounter++
  const now = new Date()
  const timestamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}.${String(now.getMilliseconds()).padStart(3, '0')}`
  return {
    id: `sim-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp,
    level: template.level,
    source: template.source,
    message: template.message,
    isReal: false,
  }
}

// Format ISO string to readable timestamp
function formatTimestamp(isoString: string): string {
  try {
    const d = new Date(isoString)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`
  } catch {
    return isoString
  }
}

export function SystemLogsPanel({ open, onOpenChange }: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isPaused, setIsPaused] = useState(false)
  const [filterLevel, setFilterLevel] = useState<string>('ALL')
  const [filterSource, setFilterSource] = useState<string>('ALL')
  const [logMode, setLogMode] = useState<'real' | 'live'>('live') // 'real' = DB only, 'live' = real + simulated
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Fetch real log entries from /api/logs
  const { data: logsData } = useApiData<{ entries: LogEntry[] }>('/api/logs', 10000)

  // Convert API entries to LogEntry format
  const realLogEntries = useCallback(() => {
    if (!logsData?.entries) return []
    return logsData.entries.map((entry) => ({
      id: entry.id || `real-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: formatTimestamp(entry.timestamp),
      level: (entry.level || 'INFO') as LogLevel,
      source: (entry.source || 'VAULT') as LogSource,
      message: entry.message || '',
      metadata: entry.metadata,
      isReal: true,
    }))
  }, [logsData])

  // Auto-generate simulated logs
  useEffect(() => {
    if (isPaused || !open) return
    const interval = setInterval(() => {
      const entry = generateSimulatedEntry()
      setLogs(prev => [entry, ...prev].slice(0, 500))
    }, 1500 + Math.random() * 2000)
    return () => clearInterval(interval)
  }, [isPaused, open])

  // Auto-scroll to top (newest)
  useEffect(() => {
    if (scrollRef.current && !isPaused) {
      scrollRef.current.scrollTop = 0
    }
  }, [logs, isPaused])

  // Merge real and simulated logs based on mode
  const allLogs = useMemo(() => {
    if (logMode === 'real') {
      return realLogEntries()
    }
    // Live mode: show real logs first, then simulated
    const real = realLogEntries()
    return [...real, ...logs]
  }, [logMode, realLogEntries, logs])

  const filteredLogs = allLogs.filter(log => {
    if (filterLevel !== 'ALL' && log.level !== filterLevel) return false
    if (filterSource !== 'ALL' && log.source !== filterSource) return false
    return true
  })

  const handleClear = () => {
    setLogs([])
    toast.success('Simulated logs cleared')
  }

  const handleExport = () => {
    const text = filteredLogs.map(l =>
      `[${l.timestamp}] [${l.level}] [${l.source}]${l.isReal ? ' [DB]' : ' [SIM]'} ${l.message}`
    ).join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nexus-logs-${new Date().toISOString().slice(0, 19)}.log`
    a.click()
    URL.revokeObjectURL(url)
    toast.success(`Exported ${filteredLogs.length} log entries (${filteredLogs.filter(l => l.isReal).length} real, ${filteredLogs.filter(l => !l.isReal).length} simulated)`)
  }

  const realCount = filteredLogs.filter(l => l.isReal).length
  const simCount = filteredLogs.filter(l => !l.isReal).length

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-none">
      <div className="pointer-events-auto w-full max-w-5xl mx-4 mb-4 rounded-xl border border-border/60 bg-card/95 backdrop-blur-xl shadow-2xl shadow-black/40 overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-gradient-to-r from-emerald-600/5 via-transparent to-transparent">
          <div className="flex items-center gap-3">
            <Terminal className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-semibold">System Logs</h3>
            <Badge variant="outline" className="text-[9px] gap-1">
              <span className={`h-1.5 w-1.5 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-emerald-500 animate-pulse'}`} />
              {isPaused ? 'Paused' : 'Live'}
            </Badge>
            <span className="text-[10px] text-muted-foreground tabular-nums">{filteredLogs.length} entries</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Log mode toggle */}
            <div className="flex items-center gap-0.5 rounded-md border border-border/50 bg-muted/30 p-0.5">
              <Button
                variant={logMode === 'real' ? 'default' : 'ghost'}
                size="sm"
                className={`h-6 text-[9px] gap-1 px-2 rounded transition-all duration-200 ${logMode === 'real' ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30 hover:bg-emerald-700' : 'hover:bg-accent/50'}`}
                onClick={() => setLogMode('real')}
              >
                <Database className="h-2.5 w-2.5" />
                Real Logs
              </Button>
              <Button
                variant={logMode === 'live' ? 'default' : 'ghost'}
                size="sm"
                className={`h-6 text-[9px] gap-1 px-2 rounded transition-all duration-200 ${logMode === 'live' ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30 hover:bg-emerald-700' : 'hover:bg-accent/50'}`}
                onClick={() => setLogMode('live')}
              >
                <Wifi className="h-2.5 w-2.5" />
                Live Feed
              </Button>
            </div>
            <Select value={filterLevel} onValueChange={setFilterLevel}>
              <SelectTrigger className="h-7 w-24 text-[10px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Levels</SelectItem>
                <SelectItem value="DEBUG">DEBUG</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARN">WARN</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
                <SelectItem value="CRITICAL">CRITICAL</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterSource} onValueChange={setFilterSource}>
              <SelectTrigger className="h-7 w-28 text-[10px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Sources</SelectItem>
                <SelectItem value="BRIDGE">BRIDGE</SelectItem>
                <SelectItem value="ENGINE">ENGINE</SelectItem>
                <SelectItem value="GOVERNOR">GOVERNOR</SelectItem>
                <SelectItem value="VAULT">VAULT</SelectItem>
                <SelectItem value="GMR">GMR</SelectItem>
                <SelectItem value="SWARM">SWARM</SelectItem>
                <SelectItem value="MONITOR">MONITOR</SelectItem>
                <SelectItem value="CONFIG">CONFIG</SelectItem>
                <SelectItem value="TOKENS">TOKENS</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setIsPaused(p => !p)}>
              {isPaused ? <Play className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> : <Pause className="h-3.5 w-3.5" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleExport}>
              <Download className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleClear}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onOpenChange(false)}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* Log entries */}
        <div ref={scrollRef} className="max-h-80 overflow-y-auto custom-scrollbar font-mono text-[11px] leading-relaxed">
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-xs">
              {logMode === 'real' ? 'No database log entries found' : 'Waiting for log entries...'}
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div
                key={log.id}
                className={`flex items-start gap-2 px-4 py-1 border-b border-border/20 hover:bg-accent/30 transition-colors ${levelBgColors[log.level]} ${log.isReal ? 'log-entry-real' : 'log-entry-simulated'}`}
              >
                <span className="text-[10px] text-muted-foreground/60 tabular-nums shrink-0 w-44">{log.timestamp}</span>
                <span className={`shrink-0 w-16 font-bold ${levelColors[log.level]}`}>[{log.level}]</span>
                <Badge className={`shrink-0 text-[8px] border-0 px-1.5 h-4 ${sourceColors[log.source] || 'bg-muted text-muted-foreground'}`}>{log.source}</Badge>
                {log.isReal && (
                  <Badge className="shrink-0 text-[7px] border-0 px-1 h-4 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">DB</Badge>
                )}
                <span className="flex-1 min-w-0 text-foreground/90">{log.message}</span>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-border/50 bg-muted/20">
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            <span>Level filters:</span>
            {(['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'] as const).map(level => (
              <span key={level} className={levelColors[level]}>{level}</span>
            ))}
          </div>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            {/* Data source indicator */}
            <span className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${realCount > 0 ? 'bg-emerald-500' : 'bg-muted-foreground/30'}`} />
              {realCount > 0 ? `${realCount} DB` : 'No DB data'}
              <span className="text-muted-foreground/40">|</span>
              <span className={`${simCount > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground/30'}`}>
                {simCount} simulated
              </span>
            </span>
            <span>
              Press <kbd className="px-1 py-0.5 rounded bg-muted text-[9px] font-mono">Ctrl+L</kbd> to toggle
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
