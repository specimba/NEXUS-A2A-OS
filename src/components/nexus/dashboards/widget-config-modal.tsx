'use client'

import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  DATA_SOURCES, COLOR_PALETTE, getDataSource, WIDGET_TYPE_META, type WidgetType,
} from './widget-catalog'
import { parseConfig, type CustomWidgetDTO } from './types'

interface Props {
  widget: CustomWidgetDTO | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

export function WidgetConfigModal({ widget, open, onOpenChange, onSaved }: Props) {
  const [title, setTitle] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [type, setType] = useState<WidgetType>('kpi')
  const [dataSource, setDataSource] = useState('')
  const [color, setColor] = useState<string>(COLOR_PALETTE[0])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (widget) {
      setTitle(widget.title)
      setSubtitle(widget.subtitle ?? '')
      setType(widget.type as WidgetType)
      setDataSource(widget.dataSource)
      const cfg = parseConfig(widget.config)
      setColor((cfg.color as string) ?? COLOR_PALETTE[0])
    }
  }, [widget])

  const meta = getDataSource(dataSource)
  const compatibleTypes = meta?.compatibleTypes ?? (['kpi', 'line', 'bar', 'pie', 'table'] as WidgetType[])

  // If the current visualization type isn't compatible with the selected data
  // source (e.g. switching from a KPI-only source to a line/bar one), snap to
  // the first compatible type so the <Select> always has a matching item.
  useEffect(() => {
    if (compatibleTypes.length > 0 && !compatibleTypes.includes(type)) {
      setType(compatibleTypes[0])
    }
  }, [dataSource, compatibleTypes, type])

  async function handleSave() {
    if (!widget) return
    setSaving(true)
    try {
      const res = await fetch(`/api/widgets/${widget.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          subtitle: subtitle.trim() || null,
          type,
          dataSource,
          config: { color },
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Widget updated')
      onSaved()
      onOpenChange(false)
    } catch (e) {
      toast.error('Failed to save widget')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Configure Widget</DialogTitle>
          <DialogDescription>
            Adjust title, data source, visualization, and accent color.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="w-title">Title</Label>
            <Input
              id="w-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={64}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="w-sub">Subtitle (optional)</Label>
            <Input
              id="w-sub"
              value={subtitle}
              onChange={(e) => setSubtitle(e.target.value)}
              maxLength={120}
              placeholder="e.g. last 24 hours"
            />
          </div>

          <div className="grid gap-2">
            <Label>Data source</Label>
            <Select value={dataSource} onValueChange={setDataSource}>
              <SelectTrigger>
                <SelectValue placeholder="Pick a data source" />
              </SelectTrigger>
              <SelectContent>
                {DATA_SOURCES.map((s) => (
                  <SelectItem key={s.key} value={s.key}>
                    <span className="text-muted-foreground mr-1">{s.group}:</span>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label>Visualization</Label>
            <Select value={type} onValueChange={(v) => setType(v as WidgetType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {compatibleTypes.map((t) => (
                  <SelectItem key={t} value={t}>
                    {WIDGET_TYPE_META[t].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label>Accent color</Label>
            <div className="flex items-center gap-1.5 flex-wrap">
              {COLOR_PALETTE.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className="h-7 w-7 rounded-full border-2 transition-transform hover:scale-110"
                  style={{
                    background: c,
                    borderColor: color === c ? 'var(--foreground)' : 'transparent',
                  }}
                  aria-label={`Pick color ${c}`}
                />
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving || !title.trim() || !dataSource}>
            {saving ? 'Saving...' : 'Save changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
