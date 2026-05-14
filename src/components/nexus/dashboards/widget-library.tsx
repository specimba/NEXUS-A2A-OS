'use client'

import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  TrendingUp,
  BarChart3,
  Activity,
  Gauge,
  Hash,
  PieChart,
  Table,
  ScrollText,
  FileText,
  Grid3x3,
  Search,
  Plus,
} from 'lucide-react'
import type { DashboardWidget, WidgetType, GridPosition } from '@/lib/dashboard-types'
import { WIDGET_TYPE_DEFINITIONS, DATA_SOURCES } from '@/lib/dashboard-types'

const ICON_MAP: Record<string, React.ElementType> = {
  TrendingUp,
  BarChart3,
  Activity,
  Gauge,
  Hash,
  PieChart,
  Table,
  ScrollText,
  FileText,
  Grid3x3,
}

interface WidgetLibraryProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  columns: number
  existingWidgets: DashboardWidget[]
  onAddWidget: (widget: DashboardWidget) => void
}

export function WidgetLibrary({
  open,
  onOpenChange,
  columns,
  existingWidgets,
  onAddWidget,
}: WidgetLibraryProps) {
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState<WidgetType | null>(null)
  const [widgetTitle, setWidgetTitle] = useState('')
  const [widgetDataSource, setWidgetDataSource] = useState('')
  const [widgetRefreshMs, setWidgetRefreshMs] = useState('30000')

  const filteredTypes = WIDGET_TYPE_DEFINITIONS.filter(
    (def) =>
      def.label.toLowerCase().includes(search.toLowerCase()) ||
      def.description.toLowerCase().includes(search.toLowerCase()) ||
      def.type.toLowerCase().includes(search.toLowerCase()),
  )

  const categories = ['chart', 'display', 'data'] as const
  const selectedDef = WIDGET_TYPE_DEFINITIONS.find((d) => d.type === selectedType)

  const getNextGridPos = (): GridPosition => {
    const maxY = existingWidgets.reduce((max, w) => Math.max(max, w.gridPos.y + w.gridPos.h), 0)
    const maxRowY = existingWidgets
      .filter((w) => w.gridPos.y + w.gridPos.h === maxY)
      .reduce((maxX, w) => Math.max(maxX, w.gridPos.x + w.gridPos.w), 0)

    const w = selectedDef?.defaultW ?? 2
    const h = selectedDef?.defaultH ?? 2

    if (maxRowY + w <= columns) {
      return { x: maxRowY, y: maxY, w, h }
    }
    return { x: 0, y: maxY, w, h }
  }

  const handleAdd = () => {
    if (!selectedType) return
    const def = WIDGET_TYPE_DEFINITIONS.find((d) => d.type === selectedType)
    if (!def) return

    const widget: DashboardWidget = {
      id: `w-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      type: selectedType,
      title: widgetTitle || def.label,
      dataSource: widgetDataSource || DATA_SOURCES[0].key,
      config: {},
      gridPos: getNextGridPos(),
      refreshMs: parseInt(widgetRefreshMs) || def.defaultRefreshMs,
    }

    onAddWidget(widget)
    handleReset()
    onOpenChange(false)
  }

  const handleReset = () => {
    setSelectedType(null)
    setWidgetTitle('')
    setWidgetDataSource('')
    setWidgetRefreshMs('30000')
    setSearch('')
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            Widget Library
          </SheetTitle>
          <SheetDescription>
            Choose a widget type and configure it for your dashboard.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 mt-4 px-4 pb-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search widgets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>

          {!selectedType ? (
            /* Widget Type Grid by Category */
            <div className="space-y-4">
              {categories.map((category) => {
                const items = filteredTypes.filter((d) => d.category === category)
                if (items.length === 0) return null
                return (
                  <div key={category}>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      {category === 'chart' ? 'Charts' : category === 'display' ? 'Display' : 'Data'}
                    </h3>
                    <div className="grid grid-cols-2 gap-2">
                      {items.map((def) => {
                        const Icon = ICON_MAP[def.icon] || Activity
                        return (
                          <button
                            key={def.type}
                            onClick={() => {
                              setSelectedType(def.type)
                              setWidgetTitle(def.label)
                              setWidgetRefreshMs(String(def.defaultRefreshMs))
                            }}
                            className="flex flex-col items-start gap-1.5 p-3 rounded-lg border border-border/50 hover:border-emerald-600/30 hover:bg-emerald-600/5 transition-all text-left"
                          >
                            <div className="flex items-center gap-2 w-full">
                              <div className="p-1.5 rounded bg-emerald-600/10">
                                <Icon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                              </div>
                              <span className="text-xs font-medium">{def.label}</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground leading-tight line-clamp-2">
                              {def.description}
                            </span>
                            <div className="flex gap-1">
                              <Badge variant="outline" className="text-[8px] h-3 px-1">
                                {def.defaultW}×{def.defaultH}
                              </Badge>
                              {def.defaultRefreshMs > 0 && (
                                <Badge variant="outline" className="text-[8px] h-3 px-1">
                                  {def.defaultRefreshMs / 1000}s
                                </Badge>
                              )}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            /* Widget Configuration Form */
            <div className="space-y-4">
              <button
                onClick={() => setSelectedType(null)}
                className="text-xs text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 flex items-center gap-1"
              >
                ← Back to widget types
              </button>

              <div className="p-3 rounded-lg border border-emerald-600/20 bg-emerald-600/5">
                <div className="flex items-center gap-2">
                  {(() => {
                    const Icon = ICON_MAP[selectedDef?.icon || 'Activity'] || Activity
                    return <Icon className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  })()}
                  <div>
                    <div className="text-sm font-semibold">{selectedDef?.label}</div>
                    <div className="text-[11px] text-muted-foreground">{selectedDef?.description}</div>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Title</Label>
                  <Input
                    value={widgetTitle}
                    onChange={(e) => setWidgetTitle(e.target.value)}
                    placeholder="Widget title"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Data Source</Label>
                  <Select value={widgetDataSource} onValueChange={setWidgetDataSource}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Select data source" />
                    </SelectTrigger>
                    <SelectContent>
                      {DATA_SOURCES.map((ds) => (
                        <SelectItem key={ds.key} value={ds.key} className="text-xs">
                          {ds.label}
                          <span className="text-muted-foreground ml-1">({ds.unit})</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Refresh Interval</Label>
                  <Select value={widgetRefreshMs} onValueChange={setWidgetRefreshMs}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5000" className="text-xs">5 seconds</SelectItem>
                      <SelectItem value="10000" className="text-xs">10 seconds</SelectItem>
                      <SelectItem value="15000" className="text-xs">15 seconds</SelectItem>
                      <SelectItem value="30000" className="text-xs">30 seconds</SelectItem>
                      <SelectItem value="60000" className="text-xs">1 minute</SelectItem>
                      <SelectItem value="300000" className="text-xs">5 minutes</SelectItem>
                      <SelectItem value="0" className="text-xs">Manual only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="p-2 rounded bg-muted/30 text-[10px] text-muted-foreground">
                  Grid position: {getNextGridPos().x},{getNextGridPos().y} —
                  Size: {selectedDef?.defaultW}×{selectedDef?.defaultH}
                </div>
              </div>

              <Button
                onClick={handleAdd}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Widget
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
