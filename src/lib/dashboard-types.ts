// ─── Dashboard Types for NEXUS OS v3.1 Custom Dashboards ─────────────────

export type LayoutType = 'grid' | 'freeform'
export type WidgetType =
  | 'line_chart'
  | 'bar_chart'
  | 'area_chart'
  | 'gauge'
  | 'stat_card'
  | 'pie_chart'
  | 'table'
  | 'log_stream'
  | 'markdown'
  | 'heatmap'

export interface GridPosition {
  x: number
  y: number
  w: number
  h: number
}

export interface WidgetConfig {
  color?: string
  unit?: string
  decimals?: number
  thresholds?: { warning?: number; critical?: number }
  maxDataPoints?: number
  [key: string]: unknown
}

export interface DashboardWidget {
  id: string
  type: WidgetType
  title: string
  dataSource: string
  config: WidgetConfig
  gridPos: GridPosition
  refreshMs: number
  collapsed?: boolean
}

export interface Dashboard {
  id: string
  name: string
  description: string
  layout: LayoutType
  columns: number
  widgets: DashboardWidget[]
  tags: string[]
  isPublic: boolean
  shareId: string | null
  createdAt: string
  updatedAt: string
}

export interface DashboardListItem {
  id: string
  name: string
  description: string
  layout: LayoutType
  columns: number
  widgetCount: number
  tags: string[]
  isPublic: boolean
  updatedAt: string
}

export interface CreateDashboardRequest {
  name: string
  description?: string
  layout: LayoutType
  columns: number
  seedWithDefaults?: boolean
}

export interface UpdateDashboardRequest {
  name?: string
  description?: string
  layout?: LayoutType
  columns?: number
  widgets?: DashboardWidget[]
  tags?: string[]
}

export interface MetricDataPoint {
  timestamp: number
  value: number
  label?: string
}

export interface MetricSeries {
  key: string
  label: string
  data: MetricDataPoint[]
  unit?: string
}

export interface MetricsResponse {
  series: MetricSeries[]
  fetchedAt: number
}

export interface ShareResponse {
  shareId: string
  shareUrl: string
  isPublic: boolean
}

// Widget type metadata for the library
export interface WidgetTypeDefinition {
  type: WidgetType
  label: string
  description: string
  icon: string
  defaultW: number
  defaultH: number
  defaultRefreshMs: number
  category: 'chart' | 'display' | 'data'
}

export const WIDGET_TYPE_DEFINITIONS: WidgetTypeDefinition[] = [
  { type: 'line_chart', label: 'Line Chart', description: 'Time-series line chart with multiple series support', icon: 'TrendingUp', defaultW: 4, defaultH: 3, defaultRefreshMs: 30000, category: 'chart' },
  { type: 'bar_chart', label: 'Bar Chart', description: 'Categorical or time-series bar chart', icon: 'BarChart3', defaultW: 4, defaultH: 3, defaultRefreshMs: 30000, category: 'chart' },
  { type: 'area_chart', label: 'Area Chart', description: 'Filled area chart for volume visualization', icon: 'AreaChart', defaultW: 4, defaultH: 3, defaultRefreshMs: 30000, category: 'chart' },
  { type: 'gauge', label: 'Gauge', description: 'Radial gauge for single-value metrics', icon: 'Gauge', defaultW: 2, defaultH: 2, defaultRefreshMs: 15000, category: 'chart' },
  { type: 'stat_card', label: 'Stat Card', description: 'Large number display with trend indicator', icon: 'Hash', defaultW: 2, defaultH: 1, defaultRefreshMs: 15000, category: 'display' },
  { type: 'pie_chart', label: 'Pie Chart', description: 'Proportional distribution chart', icon: 'PieChart', defaultW: 3, defaultH: 3, defaultRefreshMs: 60000, category: 'chart' },
  { type: 'table', label: 'Data Table', description: 'Tabular data display with sorting', icon: 'Table', defaultW: 4, defaultH: 3, defaultRefreshMs: 30000, category: 'data' },
  { type: 'log_stream', label: 'Log Stream', description: 'Real-time scrolling log viewer', icon: 'ScrollText', defaultW: 4, defaultH: 3, defaultRefreshMs: 5000, category: 'data' },
  { type: 'markdown', label: 'Markdown', description: 'Rich text markdown content block', icon: 'FileText', defaultW: 4, defaultH: 2, defaultRefreshMs: 0, category: 'display' },
  { type: 'heatmap', label: 'Heatmap', description: 'Color-coded intensity matrix', icon: 'Grid3x3', defaultW: 4, defaultH: 3, defaultRefreshMs: 60000, category: 'chart' },
]

// Default data sources available for widgets
export const DATA_SOURCES = [
  { key: 'system.cpu', label: 'CPU Usage', unit: '%' },
  { key: 'system.memory', label: 'Memory Usage', unit: '%' },
  { key: 'system.disk', label: 'Disk Usage', unit: '%' },
  { key: 'system.network', label: 'Network I/O', unit: 'KB/s' },
  { key: 'agents.uptime', label: 'Agent Uptime', unit: '%' },
  { key: 'agents.tasks', label: 'Agent Tasks', unit: 'tasks' },
  { key: 'agents.trust', label: 'Agent Trust Score', unit: 'score' },
  { key: 'tokens.usage', label: 'Token Usage', unit: 'tokens' },
  { key: 'tokens.burn_rate', label: 'Token Burn Rate', unit: 'tok/min' },
  { key: 'tokens.cost', label: 'Token Cost', unit: '$' },
  { key: 'governor.blocks', label: 'Governor Blocks', unit: 'blocks' },
  { key: 'governor.compliance', label: 'Constitution Compliance', unit: '%' },
  { key: 'modelrelay.requests', label: 'Model Relay Requests', unit: 'req/min' },
  { key: 'modelrelay.latency', label: 'Model Relay Latency', unit: 'ms' },
  { key: 'gmr.pool_health', label: 'GMR Pool Health', unit: '%' },
  { key: 'kpi.overall', label: 'KPI Overall Score', unit: '%' },
]

// Generate mock metric data for a given data source key
export function generateMockMetricData(sourceKey: string, points: number = 24): MetricDataPoint {
  const source = DATA_SOURCES.find(s => s.key === sourceKey)
  const now = Date.now()

  const baseValues: Record<string, () => number> = {
    'system.cpu': () => 30 + Math.random() * 50,
    'system.memory': () => 50 + Math.random() * 30,
    'system.disk': () => 40 + Math.random() * 35,
    'system.network': () => 100 + Math.random() * 900,
    'agents.uptime': () => 95 + Math.random() * 5,
    'agents.tasks': () => Math.floor(5 + Math.random() * 30),
    'agents.trust': () => 0.7 + Math.random() * 0.3,
    'tokens.usage': () => Math.floor(1000 + Math.random() * 9000),
    'tokens.burn_rate': () => 50 + Math.random() * 200,
    'tokens.cost': () => 0.01 + Math.random() * 0.5,
    'governor.blocks': () => Math.floor(Math.random() * 5),
    'governor.compliance': () => 95 + Math.random() * 5,
    'modelrelay.requests': () => 10 + Math.random() * 90,
    'modelrelay.latency': () => 80 + Math.random() * 300,
    'gmr.pool_health': () => 85 + Math.random() * 15,
    'kpi.overall': () => 80 + Math.random() * 20,
  }

  const generator = baseValues[sourceKey] || (() => Math.random() * 100)
  const value = Math.round(generator() * 1000) / 1000

  return {
    timestamp: now,
    value,
    label: source?.label || sourceKey,
  }
}

export function generateMockSeries(sourceKey: string, points: number = 24): MetricDataPoint[] {
  const now = Date.now()
  const interval = 300000 // 5 minutes
  const result: MetricDataPoint[] = []

  for (let i = points - 1; i >= 0; i--) {
    result.push(generateMockMetricData(sourceKey, points))
    result[result.length - 1].timestamp = now - i * interval
  }

  return result
}
