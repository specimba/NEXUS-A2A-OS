'use client'

import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Sparkles, Loader2, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

interface AiSpec {
  type: string
  title: string
  subtitle: string | null
  dataSource: string
  width: number
  height: number
  config: Record<string, unknown>
}

const EXAMPLE_PROMPTS = [
  'Show me the governor approval rate as a KPI',
  'Plot token usage over the last 24 hours',
  'Pie chart of agents grouped by status',
  'Table of recent stress tests with status',
  'Top 10 agents by token consumption',
  'How many papers have we indexed?',
]

interface Props {
  dashboardId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onWidgetAdded: () => void
}

export function AiWidgetBuilder({ dashboardId, open, onOpenChange, onWidgetAdded }: Props) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<AiSpec | null>(null)

  async function handleBuild() {
    if (!prompt.trim()) return
    setLoading(true)
    setPreview(null)
    try {
      const res = await fetch('/api/dashboards/ai-build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'AI builder failed')
      setPreview(json as AiSpec)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'AI builder failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd() {
    if (!preview) return
    setLoading(true)
    try {
      const res = await fetch(`/api/dashboards/${dashboardId}/widgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preview),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Widget added')
      onWidgetAdded()
      onOpenChange(false)
      setPreview(null)
      setPrompt('')
    } catch {
      toast.error('Failed to add widget')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v)
        if (!v) {
          setPreview(null)
          setPrompt('')
        }
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            AI Widget Builder
          </DialogTitle>
          <DialogDescription>
            Describe what you want to see. The NEXUS AI will build the widget for you.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <Textarea
            placeholder="e.g. show me token burn rate last hour as a KPI"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="resize-none"
          />

          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => setPrompt(p)}
                className="text-[11px] px-2 py-1 rounded-md border border-border/60 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                {p}
              </button>
            ))}
          </div>

          {preview && (
            <div className="mt-4 p-3 rounded-lg border bg-card/60">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary" className="text-[10px]">
                  Preview
                </Badge>
                <span className="text-[11px] text-muted-foreground">
                  {preview.type.toUpperCase()} · {preview.width}×{preview.height}
                </span>
              </div>
              <div className="text-sm font-semibold">{preview.title}</div>
              {preview.subtitle && (
                <div className="text-xs text-muted-foreground">{preview.subtitle}</div>
              )}
              <div className="text-[11px] text-muted-foreground mt-1.5">
                Source: <code className="text-foreground">{preview.dataSource}</code>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          {preview ? (
            <>
              <Button variant="outline" onClick={handleBuild} disabled={loading}>
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Re-generate'}
              </Button>
              <Button onClick={handleAdd} disabled={loading}>
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Add to dashboard'}
              </Button>
            </>
          ) : (
            <Button onClick={handleBuild} disabled={loading || !prompt.trim()}>
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
              ) : (
                <Wand2 className="h-3.5 w-3.5 mr-1.5" />
              )}
              Generate
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
