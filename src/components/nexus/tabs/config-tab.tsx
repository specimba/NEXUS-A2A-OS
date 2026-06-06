'use client'

import { useCallback, useRef, useState } from 'react'
import useSWR, { mutate } from 'swr'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { Upload, FileWarning, CheckCircle2, History, Trash2, FileCode2, RefreshCw } from 'lucide-react'
import { jsonFetcher } from '@/lib/mcp-fetcher'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { staggerContainer, staggerItem } from '@/components/nexus/tab-content'
import { cn } from '@/lib/utils'

// ────────────────────────────────────────────────────────────────────────────
// Types matching /api/config response
// ────────────────────────────────────────────────────────────────────────────

interface ConfigRecord {
  data: Record<string, unknown>
  raw: string
  filename: string | null
  uploadedAt: string
}

interface ConfigState {
  current: ConfigRecord | null
  history: (ConfigRecord & { slot: string })[]
}

interface UploadError {
  path: string
  message: string
}

interface UploadResponse {
  ok: boolean
  parsed?: Record<string, unknown>
  warnings?: string[]
  errors?: UploadError[]
  filename?: string | null
}

// ────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────

const SAMPLE_YAML = `version: 1
kernel:
  name: nexus-prod
  tier: prod
  maxAgents: 32
governor:
  approvalThreshold: 0.82
  maxConcurrent: 8
  escalationPolicy: human-in-the-loop
agents:
  - id: planner-01
    name: Planner
    model: claude-3-5-sonnet-latest,
    status: online
    tokenBudget: 1500000
  - id: researcher-02
    name: Researcher
    model: openai/gpt-5-mini
    status: online
    tokenBudget: 800000
models:
  - id: anthropic/claude-opus-4.6
    tier: reasoning
    provider: anthropic
  - id: openai/gpt-5-mini
    tier: fast
    provider: openai
alerts:
  onConfigError: true
  onStreamFailure: true
`

export function ConfigTab() {
  const { data, error, isLoading } = useSWR<ConfigState>('/api/config', jsonFetcher, {
    refreshInterval: 0,
    revalidateOnFocus: false,
  })

  const [rawInput, setRawInput] = useState<string>('')
  const [pending, setPending] = useState(false)
  const [validation, setValidation] = useState<UploadResponse | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const submitRaw = useCallback(async (raw: string, filename?: string) => {
    setPending(true)
    setValidation(null)
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ raw, filename }),
      })
      const body = (await res.json()) as UploadResponse
      setValidation(body)
      if (body.ok) {
        toast.success(`Config saved${filename ? `: ${filename}` : ''}`)
        await mutate('/api/config')
      } else {
        toast.error(`Validation failed: ${body.errors?.length ?? 0} issue(s)`)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setValidation({ ok: false, errors: [{ path: 'network', message }] })
      toast.error(message)
    } finally {
      setPending(false)
    }
  }, [])

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.match(/\.(ya?ml)$/i) && !file.type.match(/yaml/i)) {
      toast.warning(`"${file.name}" is not a .yaml/.yml file — attempting to parse anyway`)
    }
    const text = await file.text()
    setRawInput(text)
    await submitRaw(text, file.name)
  }, [submitRaw])

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) void handleFile(file)
  }, [handleFile])

  const clearAll = useCallback(async () => {
    if (!confirm('Delete the current config and all history? This cannot be undone.')) return
    setPending(true)
    try {
      const res = await fetch('/api/config', { method: 'DELETE' })
      if (res.ok) {
        toast.success('Config cleared')
        setRawInput('')
        setValidation(null)
        await mutate('/api/config')
      } else {
        toast.error('Failed to clear config')
      }
    } finally {
      setPending(false)
    }
  }, [])

  const current = data?.current ?? null
  const history = data?.history ?? []

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      exit="exit"
      className="space-y-4 p-4 md:p-6"
    >
      {/* Header */}
      <motion.div variants={staggerItem} className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <FileCode2 className="h-5 w-5 text-emerald-500" />
            Configuration
          </h2>
          <p className="text-sm text-muted-foreground">
            Upload, parse, and validate <code className="text-xs">config.yaml</code> for the NEXUS kernel.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => mutate('/api/config')}
            disabled={isLoading}
          >
            <RefreshCw className={cn('h-3.5 w-3.5 mr-1.5', isLoading && 'animate-spin')} />
            Refresh
          </Button>
          {current && (
            <Button variant="destructive" size="sm" onClick={clearAll} disabled={pending}>
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Clear
            </Button>
          )}
        </div>
      </motion.div>

      {/* Upload / paste */}
      <motion.div variants={staggerItem} className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Upload file</CardTitle>
            <CardDescription>Drop a <code className="text-xs">.yaml</code> file or click to browse.</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-8 cursor-pointer transition-colors',
                dragging
                  ? 'border-emerald-500 bg-emerald-500/5'
                  : 'border-border hover:border-emerald-500/50 hover:bg-accent/30',
              )}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <div className="text-sm text-center">
                <span className="font-medium">Click to upload</span>
                <span className="text-muted-foreground"> or drag and drop</span>
              </div>
              <span className="text-xs text-muted-foreground">YAML files only · max 1MB</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".yaml,.yml,application/yaml,application/x-yaml,text/yaml"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) void handleFile(file)
                  e.target.value = ''
                }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Paste YAML</CardTitle>
            <CardDescription>Edit in-place, then save to apply.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder={SAMPLE_YAML}
              spellCheck={false}
              className="font-mono text-xs h-40 resize-y"
            />
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => void submitRaw(rawInput || SAMPLE_YAML, rawInput ? 'pasted.yaml' : 'sample.yaml')}
                disabled={pending}
              >
                {pending ? <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
                {pending ? 'Saving…' : 'Validate & save'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setRawInput(SAMPLE_YAML)}>
                Load sample
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Validation result */}
      {validation && (
        <motion.div variants={staggerItem}>
          <Card className={cn(
            'border-l-4',
            validation.ok ? 'border-l-emerald-500' : 'border-l-rose-500',
          )}>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                {validation.ok ? (
                  <><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Valid configuration</>
                ) : (
                  <><FileWarning className="h-4 w-4 text-rose-500" /> Validation issues</>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {validation.errors && validation.errors.length > 0 && (
                <ul className="space-y-1">
                  {validation.errors.map((err, i) => (
                    <li key={i} className="text-xs flex items-start gap-2">
                      <Badge variant="destructive" className="font-mono shrink-0">{err.path}</Badge>
                      <span className="text-muted-foreground">{err.message}</span>
                    </li>
                  ))}
                </ul>
              )}
              {validation.warnings && validation.warnings.length > 0 && (
                <ul className="space-y-1 pt-1">
                  {validation.warnings.map((w, i) => (
                    <li key={i} className="text-xs flex items-start gap-2">
                      <Badge variant="secondary" className="bg-amber-500/15 text-amber-700 dark:text-amber-400 shrink-0">warning</Badge>
                      <span className="text-muted-foreground">{w}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Active config */}
      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div>
                <CardTitle className="text-sm">Active configuration</CardTitle>
                <CardDescription>
                  {current
                    ? `${current.filename ?? 'inline'} · uploaded ${new Date(current.uploadedAt).toLocaleString()}`
                    : 'No config loaded yet — upload one above.'}
                </CardDescription>
              </div>
              {current && <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-0">live</Badge>}
            </div>
          </CardHeader>
          <CardContent>
            {error && !current && (
              <p className="text-xs text-rose-500">Failed to load config: {error.message}</p>
            )}
            {isLoading && !data && (
              <p className="text-xs text-muted-foreground">Loading…</p>
            )}
            {current && <ParsedPreview data={current.data} raw={current.raw} />}
          </CardContent>
        </Card>
      </motion.div>

      {/* History */}
      {history.length > 0 && (
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <History className="h-4 w-4" /> Revision history
              </CardTitle>
              <CardDescription>Last {history.length} previous version(s).</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-48">
                <ul className="space-y-1 pr-3">
                  {history.map((h) => (
                    <li
                      key={h.slot}
                      className="flex items-center justify-between gap-2 text-xs rounded px-2 py-1.5 hover:bg-accent/50"
                    >
                      <span className="font-mono text-muted-foreground">{h.slot.replace('nexus.config.history.', '#')}</span>
                      <span className="truncate flex-1">{h.filename ?? 'inline'}</span>
                      <span className="text-muted-foreground tabular-nums">
                        {new Date(h.uploadedAt).toLocaleString()}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-xs"
                        onClick={() => { setRawInput(h.raw); toast.info('Loaded into editor — click "Validate & save" to apply') }}
                      >
                        Restore
                      </Button>
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Parsed preview — renders the parsed structure + raw YAML side-by-side
// ────────────────────────────────────────────────────────────────────────────

function ParsedPreview({ data, raw }: { data: Record<string, unknown>; raw: string }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Parsed</div>
        <ScrollArea className="h-64 rounded-md border bg-card">
          <pre className="text-[11px] font-mono p-3 leading-relaxed">
            {JSON.stringify(data, null, 2)}
          </pre>
        </ScrollArea>
        <Separator />
        <KeyHighlights data={data} />
      </div>
      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Raw YAML</div>
        <ScrollArea className="h-64 rounded-md border bg-card">
          <pre className="text-[11px] font-mono p-3 leading-relaxed whitespace-pre">
            {raw}
          </pre>
        </ScrollArea>
      </div>
    </div>
  )
}

function KeyHighlights({ data }: { data: Record<string, unknown> }) {
  const agents = Array.isArray(data.agents) ? (data.agents as Array<{ status?: string }>) : []
  const models = Array.isArray(data.models) ? data.models : []
  const governor = (data.governor as { approvalThreshold?: number } | undefined) ?? {}
  const kernel = (data.kernel as { name?: string; tier?: string; maxAgents?: number } | undefined) ?? {}

  const onlineAgents = agents.filter((a) => a.status === 'online').length

  return (
    <div className="grid grid-cols-2 gap-2 text-xs">
      <Stat label="Kernel" value={kernel.name ?? '—'} />
      <Stat label="Tier" value={kernel.tier ?? '—'} />
      <Stat label="Agents" value={`${agents.length} (${onlineAgents} online)`} />
      <Stat label="Models" value={String(models.length)} />
      <Stat
        label="Gov. threshold"
        value={typeof governor.approvalThreshold === 'number' ? governor.approvalThreshold.toFixed(2) : '—'}
      />
      <Stat label="Max agents" value={kernel.maxAgents !== undefined ? String(kernel.maxAgents) : '—'} />
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col rounded bg-accent/40 px-2 py-1.5">
      <span className="text-[10px] uppercase text-muted-foreground tracking-wider">{label}</span>
      <span className="font-medium tabular-nums truncate">{value}</span>
    </div>
  )
}
