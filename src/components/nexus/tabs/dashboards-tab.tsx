'use client'

import { useState, useCallback } from 'react'
import {
  LayoutGrid,
  Plus,
  Grid3X3,
  List,
  Sparkles,
  TrendingUp,
  BarChart3,
  PieChart,
  Table2,
  Activity,
  Gauge,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Pencil,
  Share2,
  Send,
  Loader2,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { MiniAreaChart, NexusGauge, COLORS } from '@/components/nexus/charts'

// ─── Types ───────────────────────────────────────────────────────────────────

interface Dashboard {
  id: string
  name: string
  description: string
  status: 'active' | 'draft' | 'archived'
  widgets: string[]
  lastUpdated: string
  template?: string
}

type WidgetType = 'kpi' | 'line' | 'bar' | 'pie' | 'table' | 'gauge'

interface WidgetDef {
  id: WidgetType
  name: string
  icon: React.ReactNode
  description: string
}

// ─── Data ────────────────────────────────────────────────────────────────────

const defaultDashboards: Dashboard[] = [
  {
    id: 'dsh-001',
    name: 'System Health Overview',
    description: 'Real-time system metrics and agent health monitoring',
    status: 'active',
    widgets: ['CPU', 'Memory', 'Latency', 'Agent Status'],
    lastUpdated: 'just now',
    template: 'system-health',
  },
  {
    id: 'dsh-002',
    name: 'Token Economics',
    description: 'Token budget, burn rate, and provider cost analysis',
    status: 'active',
    widgets: ['Budget Gauge', 'Burn Chart', 'Cost Table', 'Provider Split'],
    lastUpdated: '5m ago',
    template: 'token-economics',
  },
  {
    id: 'dsh-003',
    name: 'Provider Performance',
    description: 'Provider health, latency comparison, and quota tracking',
    status: 'draft',
    widgets: ['Health Grid', 'Latency Chart', 'Quota Bars'],
    lastUpdated: '1h ago',
    template: 'provider-performance',
  },
]

const widgetTypes: WidgetDef[] = [
  {
    id: 'kpi',
    name: 'KPI Card',
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Single metric with trend indicator',
  },
  {
    id: 'line',
    name: 'Line Chart',
    icon: <Activity className="h-5 w-5" />,
    description: 'Time series data visualization',
  },
  {
    id: 'bar',
    name: 'Bar Chart',
    icon: <BarChart3 className="h-5 w-5" />,
    description: 'Comparative data display',
  },
  {
    id: 'pie',
    name: 'Pie Chart',
    icon: <PieChart className="h-5 w-5" />,
    description: 'Distribution data breakdown',
  },
  {
    id: 'table',
    name: 'Table',
    icon: <Table2 className="h-5 w-5" />,
    description: 'Structured data grid view',
  },
  {
    id: 'gauge',
    name: 'Gauge',
    icon: <Gauge className="h-5 w-5" />,
    description: 'Radial progress indicator',
  },
]

// Sparkline mock data
const requestSparkData = Array.from({ length: 12 }, (_, i) => ({
  name: `${i}h`,
  value: 1200 + Math.sin(i / 2) * 400 + Math.random() * 200,
}))

const latencySparkData = Array.from({ length: 12 }, (_, i) => ({
  name: `${i}h`,
  value: 45 + Math.sin(i / 3) * 15 + Math.random() * 10,
}))

const providerSparkData = Array.from({ length: 12 }, (_, i) => ({
  name: `${i}h`,
  value: 10 + Math.sin(i / 4) * 2 + Math.random() * 1,
}))

const tokenSparkData = Array.from({ length: 12 }, (_, i) => ({
  name: `${i}h`,
  value: 50000 + Math.sin(i / 2) * 15000 + Math.random() * 5000,
}))

// ─── Sub-components ──────────────────────────────────────────────────────────

function DashboardCard({
  dashboard,
  viewMode,
  onOpen,
  onEdit,
  onShare,
}: {
  dashboard: Dashboard
  viewMode: 'grid' | 'list'
  onOpen: () => void
  onEdit: () => void
  onShare: () => void
}) {
  const borderColor =
    dashboard.status === 'active'
      ? 'border-l-emerald-500'
      : dashboard.status === 'draft'
        ? 'border-l-muted-foreground/40'
        : 'border-l-muted-foreground/20'

  if (viewMode === 'list') {
    return (
      <Card
        className={cn(
          'border-l-4 bg-card/50 border-border/50 transition-all hover:shadow-md hover:bg-card/70',
          borderColor
        )}
      >
        <div className="flex items-center gap-4 p-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-sm truncate">{dashboard.name}</h3>
              <span
                className={cn(
                  'flex h-2 w-2 shrink-0 rounded-full',
                  dashboard.status === 'active' ? 'bg-emerald-500' : 'bg-muted-foreground/40'
                )}
              />
              <Badge
                variant="secondary"
                className="text-[10px] h-4 px-1.5 border-0 bg-muted"
              >
                {dashboard.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground truncate">{dashboard.description}</p>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {dashboard.widgets.map((w) => (
              <Badge
                key={w}
                variant="secondary"
                className="text-[10px] h-5 px-1.5 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0"
              >
                {w}
              </Badge>
            ))}
          </div>
          <span className="text-[10px] text-muted-foreground shrink-0 w-16 text-right">
            {dashboard.lastUpdated}
          </span>
          <div className="flex items-center gap-1 shrink-0">
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onOpen}>
              Open
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onEdit}>
              <Pencil className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onShare}>
              <Share2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card
      className={cn(
        'border-l-4 bg-card/50 border-border/50 transition-all hover:shadow-md hover:bg-card/70',
        borderColor
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1 min-w-0">
            <CardTitle className="text-sm font-semibold truncate">{dashboard.name}</CardTitle>
            <CardDescription className="text-xs line-clamp-2">
              {dashboard.description}
            </CardDescription>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 ml-2">
            <span
              className={cn(
                'flex h-2 w-2 rounded-full',
                dashboard.status === 'active' ? 'bg-emerald-500' : 'bg-muted-foreground/40'
              )}
            />
            <Badge
              variant="secondary"
              className="text-[10px] h-4 px-1.5 border-0 bg-muted"
            >
              {dashboard.status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Widget preview chips */}
        <div className="flex flex-wrap gap-1.5">
          {dashboard.widgets.map((w) => (
            <Badge
              key={w}
              variant="secondary"
              className="text-[10px] h-5 px-1.5 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0"
            >
              {w}
            </Badge>
          ))}
        </div>

        {/* Last updated */}
        <p className="text-[10px] text-muted-foreground">
          Last updated: {dashboard.lastUpdated}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            size="sm"
            className="h-7 px-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={onOpen}
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            Open
          </Button>
          <Button variant="outline" size="sm" className="h-7 px-3 text-xs" onClick={onEdit}>
            <Pencil className="h-3 w-3 mr-1" />
            Edit
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-3 text-xs" onClick={onShare}>
            <Share2 className="h-3 w-3 mr-1" />
            Share
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function MetricsAggregator({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const metrics = [
    {
      label: 'Total Requests',
      value: '1.24M',
      change: '+12.3%',
      changeType: 'positive' as const,
      sparkData: requestSparkData,
      color: COLORS.emerald,
    },
    {
      label: 'Average Latency',
      value: '48ms',
      change: '-5.2%',
      changeType: 'positive' as const,
      sparkData: latencySparkData,
      color: COLORS.blue,
    },
    {
      label: 'Active Providers',
      value: '11',
      change: '+2',
      changeType: 'positive' as const,
      sparkData: providerSparkData,
      color: COLORS.purple,
    },
    {
      label: 'Token Usage Today',
      value: '67.4K',
      change: '+8.7%',
      changeType: 'neutral' as const,
      sparkData: tokenSparkData,
      color: COLORS.orange,
    },
  ]

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="pb-2">
        <button
          onClick={onToggle}
          className="flex items-center justify-between w-full text-left"
        >
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-500" />
            <CardTitle className="text-sm font-semibold">Metrics Aggregator</CardTitle>
            <Badge variant="secondary" className="text-[10px] h-4 px-1.5 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0">
              Live
            </Badge>
          </div>
          {collapsed ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
      </CardHeader>
      {!collapsed && (
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="rounded-lg border border-border/50 bg-background/50 p-3 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{metric.label}</span>
                  <span
                    className={cn(
                      'text-[10px] font-medium',
                      metric.changeType === 'positive'
                        ? 'text-emerald-500'
                        : 'text-muted-foreground'
                    )}
                  >
                    {metric.change}
                  </span>
                </div>
                <div className="text-lg font-bold">{metric.value}</div>
                <MiniAreaChart data={metric.sparkData} height={32} color={metric.color} />
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

function WidgetBuilderPanel({
  onAddWidget,
}: {
  onAddWidget: (type: WidgetType) => void
}) {
  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <LayoutGrid className="h-4 w-4 text-emerald-500" />
          Widget Library
        </CardTitle>
        <CardDescription className="text-xs">
          Click a widget type to add it to your dashboard
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {widgetTypes.map((wt) => (
            <button
              key={wt.id}
              onClick={() => onAddWidget(wt.id)}
              className="flex flex-col items-center gap-2 rounded-lg border border-border/50 bg-background/50 p-4 text-center transition-all hover:border-emerald-500/50 hover:bg-emerald-500/5 hover:shadow-sm"
            >
              <span className="text-emerald-500">{wt.icon}</span>
              <span className="text-xs font-medium">{wt.name}</span>
              <span className="text-[10px] text-muted-foreground leading-tight">
                {wt.description}
              </span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function AIWidgetBuilder({
  onGenerate,
  isLoading,
}: {
  onGenerate: (prompt: string) => void
  isLoading: boolean
}) {
  const [prompt, setPrompt] = useState('')

  const handleSubmit = () => {
    if (prompt.trim() && !isLoading) {
      onGenerate(prompt.trim())
      setPrompt('')
    }
  }

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-500" />
          AI Widget Builder
        </CardTitle>
        <CardDescription className="text-xs">
          Describe what you want to visualize and AI will create a widget for you
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          <Input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Show me a chart of API latency over the last hour"
            className="text-xs h-9 flex-1"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSubmit()
            }}
            disabled={isLoading}
          />
          <Button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isLoading}
            size="sm"
            className="h-9 px-3 bg-emerald-600 hover:bg-emerald-700 text-white shrink-0"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
        {isLoading && (
          <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
            <span className="flex gap-1">
              <span className="animate-bounce" style={{ animationDelay: '0ms' }}>●</span>
              <span className="animate-bounce" style={{ animationDelay: '150ms' }}>●</span>
              <span className="animate-bounce" style={{ animationDelay: '300ms' }}>●</span>
            </span>
            Generating widget from description...
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function EditDashboardPanel({
  dashboard,
  onClose,
  onAddWidget,
}: {
  dashboard: Dashboard
  onClose: () => void
  onAddWidget: (type: WidgetType) => void
}) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">{dashboard.name}</h3>
          <Badge variant="secondary" className="text-[10px] h-4 px-1.5 border-0 bg-muted">
            Editing
          </Badge>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Current widgets */}
      {dashboard.widgets.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
            Current Widgets
          </p>
          <div className="flex flex-wrap gap-1.5">
            {dashboard.widgets.map((w) => (
              <Badge
                key={w}
                variant="secondary"
                className="text-[10px] h-5 px-1.5 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0"
              >
                {w}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <Separator />

      {/* Widget Builder */}
      <WidgetBuilderPanel onAddWidget={onAddWidget} />
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function DashboardsTab() {
  const [dashboards, setDashboards] = useState<Dashboard[]>(defaultDashboards)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newTemplate, setNewTemplate] = useState('blank')
  const [metricsCollapsed, setMetricsCollapsed] = useState(false)
  const [editingDashboard, setEditingDashboard] = useState<Dashboard | null>(null)
  const [shareDialogOpen, setShareDialogOpen] = useState(false)
  const [shareDashboard, setShareDashboard] = useState<Dashboard | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [addedWidgets, setAddedWidgets] = useState<string[]>([])

  const handleCreate = useCallback(() => {
    if (!newName.trim()) return
    const d: Dashboard = {
      id: `dsh-${String(dashboards.length + 1).padStart(3, '0')}`,
      name: newName.trim(),
      description: newDescription.trim(),
      status: 'draft',
      widgets: [],
      lastUpdated: 'just now',
      template: newTemplate,
    }
    setDashboards((prev) => [...prev, d])
    setNewName('')
    setNewDescription('')
    setNewTemplate('blank')
    setCreateOpen(false)
  }, [newName, newDescription, newTemplate, dashboards.length])

  const handleAddWidget = useCallback(
    (type: WidgetType) => {
      const widgetName =
        widgetTypes.find((w) => w.id === type)?.name || type
      if (editingDashboard) {
        setDashboards((prev) =>
          prev.map((d) =>
            d.id === editingDashboard.id
              ? { ...d, widgets: [...d.widgets, widgetName], lastUpdated: 'just now' }
              : d
          )
        )
        setEditingDashboard((prev) =>
          prev
            ? { ...prev, widgets: [...prev.widgets, widgetName], lastUpdated: 'just now' }
            : null
        )
      }
      setAddedWidgets((prev) => [...prev, widgetName])
    },
    [editingDashboard]
  )

  const handleAIGenerate = useCallback(
    (prompt: string) => {
      setAiLoading(true)
      // Client-side data — no API call needed — simulated AI widget generation
      setTimeout(() => {
        // Simulate AI widget type detection from prompt
        const lowerPrompt = prompt.toLowerCase()
        let widgetType: WidgetType = 'kpi'
        let widgetName = 'AI Widget'

        if (/chart|graph|trend|over time|timeline|history/.test(lowerPrompt)) {
          widgetType = 'line'
          widgetName = 'AI: Trend Chart'
        } else if (/compare|comparison|bar|versus|vs/.test(lowerPrompt)) {
          widgetType = 'bar'
          widgetName = 'AI: Comparison Chart'
        } else if (/distribut|breakdown|split|proportion|percent/.test(lowerPrompt)) {
          widgetType = 'pie'
          widgetName = 'AI: Distribution Chart'
        } else if (/metric|gauge|progress|score|rating|health/.test(lowerPrompt)) {
          widgetType = 'gauge'
          widgetName = 'AI: Metric Gauge'
        } else if (/table|list|grid|data|rows/.test(lowerPrompt)) {
          widgetType = 'table'
          widgetName = 'AI: Data Table'
        } else if (/kpi|key|indicator|number|count|total/.test(lowerPrompt)) {
          widgetType = 'kpi'
          widgetName = 'AI: KPI Card'
        } else {
          widgetType = 'kpi'
          widgetName = `AI: ${prompt.slice(0, 30)}${prompt.length > 30 ? '...' : ''}`
        }

        if (editingDashboard) {
          setDashboards((prev) =>
            prev.map((d) =>
              d.id === editingDashboard.id
                ? { ...d, widgets: [...d.widgets, widgetName], lastUpdated: 'just now' }
                : d
            )
          )
          setEditingDashboard((prev) =>
            prev
              ? { ...prev, widgets: [...prev.widgets, widgetName], lastUpdated: 'just now' }
              : null
          )
        }
        setAddedWidgets((prev) => [...prev, widgetName])
        setAiLoading(false)
      }, 1200 + Math.random() * 800)
    },
    [editingDashboard]
  )

  const handleOpen = useCallback((d: Dashboard) => {
    // Visual feedback: could navigate to a dedicated view, for now just a no-op
  }, [])

  const handleEdit = useCallback((d: Dashboard) => {
    setEditingDashboard(d)
  }, [])

  const handleShare = useCallback((d: Dashboard) => {
    setShareDashboard(d)
    setShareDialogOpen(true)
  }, [])

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-600/10">
            <LayoutGrid className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              Custom Dashboards
              <Badge
                variant="secondary"
                className="text-[10px] h-4 px-1.5 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0"
              >
                Live
              </Badge>
            </h2>
            <p className="text-xs text-muted-foreground">
              Build and customize dashboards with widgets and AI assistance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Grid / List toggle */}
          <div className="flex items-center rounded-lg border border-border/50 p-0.5">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-7 w-7"
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-7 w-7"
              onClick={() => setViewMode('list')}
            >
              <List className="h-3.5 w-3.5" />
            </Button>
          </div>

          <Button
            size="sm"
            className="h-8 px-3 bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            New Dashboard
          </Button>
        </div>
      </div>

      {/* ── Metrics Aggregator ── */}
      <MetricsAggregator
        collapsed={metricsCollapsed}
        onToggle={() => setMetricsCollapsed((c) => !c)}
      />

      {/* ── Edit Dashboard Panel ── */}
      {editingDashboard && (
        <Card className="bg-card/50 border-emerald-500/30 border">
          <CardContent className="p-4 space-y-4">
            <EditDashboardPanel
              dashboard={editingDashboard}
              onClose={() => setEditingDashboard(null)}
              onAddWidget={handleAddWidget}
            />

            <Separator />

            {/* AI Widget Builder */}
            <AIWidgetBuilder onGenerate={handleAIGenerate} isLoading={aiLoading} />

            {/* Added widgets notification */}
            {addedWidgets.length > 0 && (
              <div className="rounded-lg bg-emerald-600/10 p-3 text-xs text-emerald-600 dark:text-emerald-400">
                Added {addedWidgets.length} widget{addedWidgets.length > 1 ? 's' : ''}:{' '}
                {addedWidgets.slice(-3).join(', ')}
                {addedWidgets.length > 3 && ` +${addedWidgets.length - 3} more`}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Dashboard Cards ── */}
      <div
        className={cn(
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'flex flex-col gap-3'
        )}
      >
        {dashboards.map((d) => (
          <DashboardCard
            key={d.id}
            dashboard={d}
            viewMode={viewMode}
            onOpen={() => handleOpen(d)}
            onEdit={() => handleEdit(d)}
            onShare={() => handleShare(d)}
          />
        ))}
      </div>

      {/* ── Create Dashboard Dialog ── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-4 w-4 text-emerald-500" />
              Create Dashboard
            </DialogTitle>
            <DialogDescription>
              Create a new custom dashboard. Choose a template to get started quickly.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-xs font-medium">Name</label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Dashboard"
                className="text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Description</label>
              <Textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What this dashboard is for..."
                className="text-sm min-h-[80px]"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Template</label>
              <Select value={newTemplate} onValueChange={setNewTemplate}>
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="blank">Blank</SelectItem>
                  <SelectItem value="system-health">System Health</SelectItem>
                  <SelectItem value="token-economics">Token Economics</SelectItem>
                  <SelectItem value="provider-performance">Provider Performance</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={handleCreate}
              disabled={!newName.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Share Dialog ── */}
      <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-4 w-4 text-emerald-500" />
              Share Dashboard
            </DialogTitle>
            <DialogDescription>
              Share &quot;{shareDashboard?.name}&quot; with your team
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-xs font-medium">Share Link</label>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={`https://nexus.os/dashboards/${shareDashboard?.id}`}
                  className="text-xs"
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `https://nexus.os/dashboards/${shareDashboard?.id}`
                    )
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Access</label>
              <Select defaultValue="view">
                <SelectTrigger className="text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="view">View Only</SelectItem>
                  <SelectItem value="edit">Can Edit</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShareDialogOpen(false)}>
              Close
            </Button>
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => setShareDialogOpen(false)}
            >
              Share
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
