'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import {
  ArrowLeft,
  Settings,
  Plus,
  Share2,
  Save,
  Check,
  Loader2,
  Pencil,
  Trash2,
  Maximize2,
  Minimize2,
  GripVertical,
  LayoutDashboard,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { WidgetRenderer, type NexusMetrics } from './widget-renderer'
import { WidgetLibrary } from './widget-library'
import { ShareDialog } from './share-dialog'
import type {
  Dashboard,
  DashboardWidget,
  MetricSeries,
  LayoutType,
  GridPosition,
  WidgetType,
} from '@/lib/dashboard-types'
import { generateMockSeries, DATA_SOURCES } from '@/lib/dashboard-types'

// ─── Mock Dashboard Data ──────────────────────────────────────────────────

const MOCK_DASHBOARD: Dashboard = {
  id: 'dash-1',
  name: 'System Overview',
  description: 'High-level system health and resource utilization.',
  layout: 'grid',
  columns: 12,
  widgets: [
    {
      id: 'w-1',
      type: 'stat_card',
      title: 'CPU Usage',
      dataSource: 'system.cpu',
      config: { unit: '%' },
      gridPos: { x: 0, y: 0, w: 3, h: 1 },
      refreshMs: 15000,
    },
    {
      id: 'w-2',
      type: 'stat_card',
      title: 'Memory',
      dataSource: 'system.memory',
      config: { unit: '%' },
      gridPos: { x: 3, y: 0, w: 3, h: 1 },
      refreshMs: 15000,
    },
    {
      id: 'w-3',
      type: 'stat_card',
      title: 'Disk Usage',
      dataSource: 'system.disk',
      config: { unit: '%' },
      gridPos: { x: 6, y: 0, w: 3, h: 1 },
      refreshMs: 15000,
    },
    {
      id: 'w-4',
      type: 'stat_card',
      title: 'Network I/O',
      dataSource: 'system.network',
      config: { unit: 'KB/s' },
      gridPos: { x: 9, y: 0, w: 3, h: 1 },
      refreshMs: 15000,
    },
    {
      id: 'w-5',
      type: 'area_chart',
      title: 'CPU Trend',
      dataSource: 'system.cpu',
      config: { unit: '%' },
      gridPos: { x: 0, y: 1, w: 6, h: 3 },
      refreshMs: 30000,
    },
    {
      id: 'w-6',
      type: 'bar_chart',
      title: 'Agent Tasks',
      dataSource: 'agents.tasks',
      config: { unit: 'tasks' },
      gridPos: { x: 6, y: 1, w: 6, h: 3 },
      refreshMs: 30000,
    },
    {
      id: 'w-7',
      type: 'gauge',
      title: 'Constitution Compliance',
      dataSource: 'governor.compliance',
      config: { unit: '%' },
      gridPos: { x: 0, y: 4, w: 3, h: 2 },
      refreshMs: 30000,
    },
    {
      id: 'w-8',
      type: 'line_chart',
      title: 'Token Burn Rate',
      dataSource: 'tokens.burn_rate',
      config: { unit: 'tok/min' },
      gridPos: { x: 3, y: 4, w: 9, h: 3 },
      refreshMs: 30000,
    },
  ],
  tags: ['system', 'health', 'monitoring'],
  isPublic: false,
  shareId: null,
  createdAt: new Date(Date.now() - 86400000).toISOString(),
  updatedAt: new Date().toISOString(),
}

// ─── Sortable Widget Item ──────────────────────────────────────────────────

function SortableWidget({
  widget,
  metrics,
  nexusMetrics,
  isEditing,
  onEdit,
  onDelete,
  onToggleCollapse,
  dashboardColumns,
}: {
  widget: DashboardWidget
  metrics: MetricSeries[]
  nexusMetrics: NexusMetrics | null
  isEditing: boolean
  onEdit: () => void
  onDelete: () => void
  onToggleCollapse: () => void
  dashboardColumns: number
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id, disabled: !isEditing })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    gridColumn: `${widget.gridPos.x + 1} / span ${widget.gridPos.w}`,
    gridRow: `${widget.gridPos.y + 1} / span ${widget.gridPos.h}`,
    zIndex: isDragging ? 50 : undefined,
    opacity: isDragging ? 0.8 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} className="min-h-0">
      <div className="relative h-full">
        {isEditing && (
          <div
            {...attributes}
            {...listeners}
            className="absolute top-1 left-1 z-10 p-0.5 rounded bg-background/80 border border-border/50 cursor-move opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <GripVertical className="h-3 w-3 text-muted-foreground" />
          </div>
        )}
        <div className="group h-full">
          <WidgetRenderer
            widget={widget}
            metrics={metrics}
            nexusMetrics={nexusMetrics}
            isEditing={isEditing}
            onEdit={onEdit}
            onDelete={onDelete}
            className="h-full"
          />
        </div>
        {/* Collapse/Expand overlay button */}
        {isEditing && (
          <button
            onClick={onToggleCollapse}
            className="absolute top-1 right-1 z-10 p-0.5 rounded bg-background/80 border border-border/50 opacity-0 group-hover:opacity-100 transition-opacity"
            aria-label={widget.collapsed ? 'Expand widget' : 'Collapse widget'}
          >
            {widget.collapsed ? (
              <Maximize2 className="h-3 w-3 text-muted-foreground" />
            ) : (
              <Minimize2 className="h-3 w-3 text-muted-foreground" />
            )}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Main Dashboard Editor ────────────────────────────────────────────────

interface DashboardEditorProps {
  dashboardId: string
  onBack: () => void
  onShare: (id: string) => void
}

export function DashboardEditor({ dashboardId, onBack, onShare }: DashboardEditorProps) {
  // Initialize with mock data to avoid synchronous setState in effects
  const initialDashboard = { ...MOCK_DASHBOARD, id: dashboardId }

  const [dashboard, setDashboard] = useState<Dashboard>(initialDashboard)
  const [metrics, setMetrics] = useState<MetricSeries[]>(() => {
    // Pre-generate mock metrics for initial dashboard
    const sources = [...new Set(initialDashboard.widgets.map((w) => w.dataSource))]
    return sources.map((key) => ({
      key,
      label: DATA_SOURCES.find((s) => s.key === key)?.label || key,
      data: generateMockSeries(key, 24).map((dp, i) => ({
        timestamp: dp.timestamp,
        value: dp.value,
        label: String(i),
      })),
      unit: DATA_SOURCES.find((s) => s.key === key)?.unit,
    }))
  })
  const [nexusMetrics, setNexusMetrics] = useState<NexusMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  // UI states
  const [isEditing, setIsEditing] = useState(true)
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [shareDialogOpen, setShareDialogOpen] = useState(false)
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null)
  const [widgetConfigOpen, setWidgetConfigOpen] = useState(false)

  // Widget config form state
  const [configTitle, setConfigTitle] = useState('')
  const [configType, setConfigType] = useState<WidgetType>('stat_card')
  const [configDataSource, setConfigDataSource] = useState('')
  const [configRefreshMs, setConfigRefreshMs] = useState('30000')
  const [configGridX, setConfigGridX] = useState('0')
  const [configGridY, setConfigGridY] = useState('0')
  const [configGridW, setConfigGridW] = useState('2')
  const [configGridH, setConfigGridH] = useState('2')
  const [configJson, setConfigJson] = useState('{}')

  // Dashboard settings form
  const [settingsName, setSettingsName] = useState(initialDashboard.name)
  const [settingsDescription, setSettingsDescription] = useState(initialDashboard.description)
  const [settingsLayout, setSettingsLayout] = useState<LayoutType>(initialDashboard.layout)
  const [settingsColumns, setSettingsColumns] = useState(String(initialDashboard.columns))

  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
  )

  // Async fetch dashboard data from API — only updates state on success
  useEffect(() => {
    let cancelled = false
    const loadDashboard = async () => {
      try {
        const res = await fetch(`/api/dashboards/${dashboardId}`)
        if (res.ok && !cancelled) {
          const data = await res.json()
          setDashboard(data)
          setSettingsName(data.name)
          setSettingsDescription(data.description)
          setSettingsLayout(data.layout)
          setSettingsColumns(String(data.columns))
        }
      } catch {
        // API unavailable — keep mock data already in state
      }
      if (!cancelled) {
        setLoading(false)
      }
    }
    loadDashboard()
    return () => { cancelled = true }
  }, [dashboardId])

  // Async fetch metrics — only updates state on success, auto-refresh interval
  useEffect(() => {
    let cancelled = false

    const loadMetrics = async () => {
      try {
        const res = await fetch('/api/dashboards/metrics')
        if (res.ok && !cancelled) {
          const data = await res.json()
          // Store the full nexus metrics object
          setNexusMetrics(data as NexusMetrics)
          // Also convert time series data into MetricSeries format for chart widgets
          const seriesFromApi: MetricSeries[] = []
          if (data.timeSeries) {
            for (const [key, ts] of Object.entries(data.timeSeries)) {
              const t = ts as { labels: string[]; values: number[] }
              seriesFromApi.push({
                key: `timeSeries.${key}`,
                label: key.charAt(0).toUpperCase() + key.slice(1),
                data: t.labels.map((label, i) => ({
                  timestamp: Date.now() - (t.labels.length - i) * 300000,
                  value: t.values[i] || 0,
                  label,
                })),
              })
            }
          }
          setMetrics(seriesFromApi.length > 0 ? seriesFromApi : metrics)
        }
      } catch {
        // API unavailable — keep mock data already in state
      }
    }

    loadMetrics()

    // Auto-refresh based on shortest widget refreshMs
    const minRefresh = Math.min(
      ...dashboard.widgets
        .filter((w) => w.refreshMs > 0)
        .map((w) => w.refreshMs),
      60000, // default 60s
    )

    const interval = setInterval(loadMetrics, minRefresh)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [dashboard])

  // Auto-save with debounce
  const triggerAutoSave = useCallback(() => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current)
    }
    setSaveStatus('saving')
    autoSaveTimerRef.current = setTimeout(async () => {
      setSaving(true)
      try {
        const res = await fetch(`/api/dashboards/${dashboardId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: settingsName,
            description: settingsDescription,
            layout: settingsLayout,
            columns: parseInt(settingsColumns),
            widgets: dashboard?.widgets,
          }),
        })
        if (res.ok) {
          setSaveStatus('saved')
          setTimeout(() => setSaveStatus('idle'), 2000)
        }
      } catch {
        // Mock: just mark as saved
        setSaveStatus('saved')
        setTimeout(() => setSaveStatus('idle'), 2000)
      }
      setSaving(false)
    }, 1500)
  }, [dashboardId, dashboard, settingsName, settingsDescription, settingsLayout, settingsColumns])

  // Handle drag end for widget reordering
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      if (!dashboard) return
      const { active, over } = event
      if (!over || active.id === over.id) return

      const activeWidget = dashboard.widgets.find((w) => w.id === active.id)
      const overWidget = dashboard.widgets.find((w) => w.id === over.id)
      if (!activeWidget || !overWidget) return

      // Swap grid positions
      const updatedWidgets = dashboard.widgets.map((w) => {
        if (w.id === active.id) {
          return { ...w, gridPos: { ...overWidget.gridPos } }
        }
        if (w.id === over.id) {
          return { ...w, gridPos: { ...activeWidget.gridPos } }
        }
        return w
      })

      setDashboard({ ...dashboard, widgets: updatedWidgets })
      triggerAutoSave()
    },
    [dashboard, triggerAutoSave],
  )

  // Widget operations
  const handleAddWidget = useCallback(
    (widget: DashboardWidget) => {
      if (!dashboard) return
      setDashboard({ ...dashboard, widgets: [...dashboard.widgets, widget] })
      triggerAutoSave()
    },
    [dashboard, triggerAutoSave],
  )

  const handleDeleteWidget = useCallback(
    (widgetId: string) => {
      if (!dashboard) return
      setDashboard({
        ...dashboard,
        widgets: dashboard.widgets.filter((w) => w.id !== widgetId),
      })
      triggerAutoSave()
    },
    [dashboard, triggerAutoSave],
  )

  const handleToggleCollapse = useCallback(
    (widgetId: string) => {
      if (!dashboard) return
      setDashboard({
        ...dashboard,
        widgets: dashboard.widgets.map((w) =>
          w.id === widgetId ? { ...w, collapsed: !w.collapsed } : w,
        ),
      })
      triggerAutoSave()
    },
    [dashboard, triggerAutoSave],
  )

  // Open widget config panel
  const openWidgetConfig = useCallback((widget: DashboardWidget) => {
    setEditingWidget(widget)
    setConfigTitle(widget.title)
    setConfigType(widget.type)
    setConfigDataSource(widget.dataSource)
    setConfigRefreshMs(String(widget.refreshMs))
    setConfigGridX(String(widget.gridPos.x))
    setConfigGridY(String(widget.gridPos.y))
    setConfigGridW(String(widget.gridPos.w))
    setConfigGridH(String(widget.gridPos.h))
    setConfigJson(JSON.stringify(widget.config, null, 2))
    setWidgetConfigOpen(true)
  }, [])

  // Save widget config
  const handleSaveWidgetConfig = useCallback(() => {
    if (!dashboard || !editingWidget) return
    try {
      const parsedConfig = JSON.parse(configJson || '{}')
      const updatedWidget: DashboardWidget = {
        ...editingWidget,
        title: configTitle,
        type: configType,
        dataSource: configDataSource,
        refreshMs: parseInt(configRefreshMs) || 30000,
        gridPos: {
          x: parseInt(configGridX) || 0,
          y: parseInt(configGridY) || 0,
          w: parseInt(configGridW) || 2,
          h: parseInt(configGridH) || 2,
        },
        config: parsedConfig,
      }
      setDashboard({
        ...dashboard,
        widgets: dashboard.widgets.map((w) =>
          w.id === editingWidget.id ? updatedWidget : w,
        ),
      })
      setWidgetConfigOpen(false)
      setEditingWidget(null)
      triggerAutoSave()
    } catch {
      // Invalid JSON — don't save
    }
  }, [
    dashboard,
    editingWidget,
    configTitle,
    configType,
    configDataSource,
    configRefreshMs,
    configGridX,
    configGridY,
    configGridW,
    configGridH,
    configJson,
    triggerAutoSave,
  ])

  // Save dashboard settings
  const handleSaveSettings = useCallback(() => {
    if (!dashboard) return
    setDashboard({
      ...dashboard,
      name: settingsName,
      description: settingsDescription,
      layout: settingsLayout,
      columns: parseInt(settingsColumns),
    })
    setSettingsOpen(false)
    triggerAutoSave()
  }, [dashboard, settingsName, settingsDescription, settingsLayout, settingsColumns, triggerAutoSave])

  // Compute grid row count for CSS grid
  const maxRow = Math.max(...dashboard.widgets.map((w) => w.gridPos.y + w.gridPos.h), 1)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        <span className="ml-3 text-sm text-muted-foreground">Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Top Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={onBack}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Button>

        <div className="flex items-center gap-2 flex-1 min-w-0">
          <LayoutDashboard className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <Input
            value={settingsName}
            onChange={(e) => {
              setSettingsName(e.target.value)
              triggerAutoSave()
            }}
            className="h-8 text-sm font-semibold border-transparent bg-transparent hover:border-border focus:border-border px-1 max-w-[300px]"
          />
        </div>

        <div className="flex items-center gap-1.5">
          {/* Save indicator */}
          {saveStatus === 'saving' && (
            <Badge variant="outline" className="text-[9px] h-5 gap-1 text-yellow-600 border-yellow-600/30">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              Saving...
            </Badge>
          )}
          {saveStatus === 'saved' && (
            <Badge variant="outline" className="text-[9px] h-5 gap-1 text-emerald-600 border-emerald-600/30">
              <Check className="h-2.5 w-2.5" />
              Saved
            </Badge>
          )}

          <Button
            size="sm"
            variant="outline"
            className="h-7 w-7 p-0"
            onClick={() => setSettingsOpen(true)}
            aria-label="Dashboard settings"
          >
            <Settings className="h-3.5 w-3.5" />
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-7 gap-1 text-[10px]"
            onClick={() => setIsEditing(!isEditing)}
          >
            <Pencil className="h-3 w-3" />
            {isEditing ? 'Preview' : 'Edit'}
          </Button>

          <Button
            size="sm"
            className="h-7 gap-1 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={() => setLibraryOpen(true)}
          >
            <Plus className="h-3 w-3" />
            Add Widget
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-7 gap-1 text-[10px]"
            onClick={() => {
              setShareDialogOpen(true)
              onShare(dashboardId)
            }}
          >
            <Share2 className="h-3 w-3" />
            Share
          </Button>
        </div>
      </div>

      {/* Dashboard Info Bar */}
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <span>{dashboard.widgets.length} widgets</span>
        <span>•</span>
        <span>{dashboard.columns} columns</span>
        <span>•</span>
        <span>{dashboard.layout === 'grid' ? 'Grid layout' : 'Freeform layout'}</span>
        <span>•</span>
        <span>Updated {new Date(dashboard.updatedAt).toLocaleString()}</span>
        {dashboard.isPublic && (
          <>
            <span>•</span>
            <Badge className="text-[8px] h-3.5 px-1 bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
              PUBLIC
            </Badge>
          </>
        )}
      </div>

      {/* Main Grid Area */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={dashboard.widgets.map((w) => w.id)}
          strategy={rectSortingStrategy}
        >
          <div
            className="grid gap-3 auto-rows-[minmax(120px,auto)]"
            style={{
              gridTemplateColumns: `repeat(${dashboard.columns}, 1fr)`,
              gridTemplateRows: `repeat(${maxRow}, minmax(120px, auto))`,
            }}
          >
            {dashboard.widgets.map((widget) => (
              <SortableWidget
                key={widget.id}
                widget={widget}
                metrics={metrics}
                nexusMetrics={nexusMetrics}
                isEditing={isEditing}
                onEdit={() => openWidgetConfig(widget)}
                onDelete={() => handleDeleteWidget(widget.id)}
                onToggleCollapse={() => handleToggleCollapse(widget.id)}
                dashboardColumns={dashboard.columns}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Empty state when no widgets */}
      {dashboard.widgets.length === 0 && (
        <Card className="bg-card/50 border-border/50 border-dashed">
          <CardContent className="p-8 text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-emerald-600/10 flex items-center justify-center mb-3">
              <Plus className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h3 className="text-sm font-semibold mb-1">No widgets yet</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Add widgets to build your dashboard
            </p>
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
              onClick={() => setLibraryOpen(true)}
            >
              <Plus className="h-3.5 w-3.5" />
              Add Widget
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Widget Library Drawer */}
      <WidgetLibrary
        open={libraryOpen}
        onOpenChange={setLibraryOpen}
        columns={dashboard.columns}
        existingWidgets={dashboard.widgets}
        onAddWidget={handleAddWidget}
      />

      {/* Share Dialog */}
      <ShareDialog
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        dashboard={dashboard}
      />

      {/* Dashboard Settings Sheet */}
      <Sheet open={settingsOpen} onOpenChange={setSettingsOpen}>
        <SheetContent side="right" className="w-full sm:max-w-sm overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              Dashboard Settings
            </SheetTitle>
            <SheetDescription>
              Configure the dashboard name, layout, and display options.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 mt-4 px-4 pb-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Name</Label>
              <Input
                value={settingsName}
                onChange={(e) => setSettingsName(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Description</Label>
              <Textarea
                value={settingsDescription}
                onChange={(e) => setSettingsDescription(e.target.value)}
                className="text-xs min-h-[60px] resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Layout</Label>
                <Select value={settingsLayout} onValueChange={(v: LayoutType) => setSettingsLayout(v)}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="grid" className="text-xs">Grid</SelectItem>
                    <SelectItem value="freeform" className="text-xs">Freeform</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Columns</Label>
                <Select value={settingsColumns} onValueChange={setSettingsColumns}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="6" className="text-xs">6 columns</SelectItem>
                    <SelectItem value="8" className="text-xs">8 columns</SelectItem>
                    <SelectItem value="12" className="text-xs">12 columns</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/30 text-[10px] text-muted-foreground space-y-1">
              <div>Dashboard ID: <span className="font-mono">{dashboard.id}</span></div>
              <div>Created: {new Date(dashboard.createdAt).toLocaleString()}</div>
              <div>Widgets: {dashboard.widgets.length}</div>
              <div>Tags: {dashboard.tags.length > 0 ? dashboard.tags.join(', ') : 'None'}</div>
            </div>

            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
              onClick={handleSaveSettings}
            >
              <Save className="h-4 w-4" />
              Save Settings
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Widget Config Sheet */}
      <Sheet open={widgetConfigOpen} onOpenChange={setWidgetConfigOpen}>
        <SheetContent side="right" className="w-full sm:max-w-sm overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Pencil className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              Widget Configuration
            </SheetTitle>
            <SheetDescription>
              Edit the widget type, data source, position, and settings.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 mt-4 px-4 pb-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Title</Label>
              <Input
                value={configTitle}
                onChange={(e) => setConfigTitle(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Widget Type</Label>
              <Select value={configType} onValueChange={(v: WidgetType) => setConfigType(v)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="line_chart" className="text-xs">Line Chart</SelectItem>
                  <SelectItem value="bar_chart" className="text-xs">Bar Chart</SelectItem>
                  <SelectItem value="area_chart" className="text-xs">Area Chart</SelectItem>
                  <SelectItem value="gauge" className="text-xs">Gauge</SelectItem>
                  <SelectItem value="stat_card" className="text-xs">Stat Card</SelectItem>
                  <SelectItem value="pie_chart" className="text-xs">Pie Chart</SelectItem>
                  <SelectItem value="table" className="text-xs">Data Table</SelectItem>
                  <SelectItem value="log_stream" className="text-xs">Log Stream</SelectItem>
                  <SelectItem value="markdown" className="text-xs">Markdown</SelectItem>
                  <SelectItem value="heatmap" className="text-xs">Heatmap</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Data Source</Label>
              <Select value={configDataSource} onValueChange={setConfigDataSource}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select data source" />
                </SelectTrigger>
                <SelectContent>
                  {DATA_SOURCES.map((ds) => (
                    <SelectItem key={ds.key} value={ds.key} className="text-xs">
                      {ds.label} ({ds.unit})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Refresh Interval</Label>
              <Select value={configRefreshMs} onValueChange={setConfigRefreshMs}>
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

            <div className="space-y-1.5">
              <Label className="text-xs">Grid Position</Label>
              <div className="grid grid-cols-4 gap-2">
                <div>
                  <Label className="text-[10px] text-muted-foreground">X</Label>
                  <Input
                    type="number"
                    value={configGridX}
                    onChange={(e) => setConfigGridX(e.target.value)}
                    className="h-7 text-xs"
                    min={0}
                  />
                </div>
                <div>
                  <Label className="text-[10px] text-muted-foreground">Y</Label>
                  <Input
                    type="number"
                    value={configGridY}
                    onChange={(e) => setConfigGridY(e.target.value)}
                    className="h-7 text-xs"
                    min={0}
                  />
                </div>
                <div>
                  <Label className="text-[10px] text-muted-foreground">W</Label>
                  <Input
                    type="number"
                    value={configGridW}
                    onChange={(e) => setConfigGridW(e.target.value)}
                    className="h-7 text-xs"
                    min={1}
                  />
                </div>
                <div>
                  <Label className="text-[10px] text-muted-foreground">H</Label>
                  <Input
                    type="number"
                    value={configGridH}
                    onChange={(e) => setConfigGridH(e.target.value)}
                    className="h-7 text-xs"
                    min={1}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Config JSON</Label>
              <Textarea
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                className="text-[10px] font-mono min-h-[80px] resize-none"
                placeholder="{}"
              />
            </div>

            <div className="flex gap-2">
              <Button
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                onClick={handleSaveWidgetConfig}
              >
                <Save className="h-3.5 w-3.5" />
                Save Widget
              </Button>
              <Button
                variant="outline"
                className="gap-1.5 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                onClick={() => {
                  if (editingWidget) {
                    handleDeleteWidget(editingWidget.id)
                    setWidgetConfigOpen(false)
                    setEditingWidget(null)
                  }
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
