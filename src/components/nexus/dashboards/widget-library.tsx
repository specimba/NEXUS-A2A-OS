'use client'

import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  BarChart3, LineChart, PieChart, Table as TableIcon, Gauge, Search, Plus,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { DATA_SOURCES, WIDGET_TYPE_META, type WidgetType } from './widget-catalog'

function typeIcon(t: WidgetType) {
  switch (t) {
    case 'kpi':   return <Gauge className="h-3.5 w-3.5" />
    case 'line':  return <LineChart className="h-3.5 w-3.5" />
    case 'bar':   return <BarChart3 className="h-3.5 w-3.5" />
    case 'pie':   return <PieChart className="h-3.5 w-3.5" />
    case 'table': return <TableIcon className="h-3.5 w-3.5" />
  }
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (sourceKey: string, type: WidgetType) => Promise<void> | void
}

export function WidgetLibrary({ open, onOpenChange, onAdd }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return DATA_SOURCES
    return DATA_SOURCES.filter(
      (s) =>
        s.label.toLowerCase().includes(q) ||
        s.group.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q),
    )
  }, [query])

  const grouped = useMemo(() => {
    const map = new Map<string, typeof DATA_SOURCES>()
    filtered.forEach((s) => {
      const list = map.get(s.group) ?? []
      list.push(s)
      map.set(s.group, list)
    })
    return Array.from(map.entries())
  }, [filtered])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        <SheetHeader className="p-6 pb-3 border-b">
          <SheetTitle>Widget Library</SheetTitle>
          <SheetDescription>
            Pick a NEXUS data source. We&apos;ll add it to your dashboard.
          </SheetDescription>
          <div className="relative mt-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents, tokens, governor..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="p-6 pt-3 space-y-5">
            {grouped.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-12">
                No data sources match &ldquo;{query}&rdquo;.
              </p>
            )}
            {grouped.map(([group, items]) => (
              <div key={group}>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  {group}
                </div>
                <div className="space-y-1.5">
                  {items.map((s) => (
                    <div
                      key={s.key}
                      className="group p-3 rounded-lg border border-border/60 hover:border-primary/40 hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{s.label}</div>
                          <div className="text-[11px] text-muted-foreground leading-snug mt-0.5">
                            {s.description}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {s.compatibleTypes.map((t) => (
                          <Button
                            key={t}
                            size="sm"
                            variant={t === s.defaultType ? 'default' : 'outline'}
                            className="h-7 px-2.5 text-[11px] gap-1"
                            onClick={() => {
                              onAdd(s.key, t)
                            }}
                          >
                            {typeIcon(t)}
                            {WIDGET_TYPE_META[t].label}
                            {t === s.defaultType && (
                              <Badge
                                variant="secondary"
                                className="ml-0.5 h-3.5 px-1 text-[8px] font-normal"
                              >
                                rec
                              </Badge>
                            )}
                          </Button>
                        ))}
                        <Plus className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity ml-auto" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
