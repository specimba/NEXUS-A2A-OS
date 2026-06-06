// Catalog of available data sources & widget templates for Custom Dashboards.

export type WidgetType = 'kpi' | 'line' | 'bar' | 'pie' | 'table'

export interface DataSourceMeta {
  key: string                 // metrics API source key
  label: string               // human label
  group: string               // group / pillar (Agents, Tokens, Governor, ...)
  description: string
  defaultType: WidgetType     // suggested widget type
  compatibleTypes: WidgetType[]
}

export const DATA_SOURCES: DataSourceMeta[] = [
  // Agents
  { key: 'agents.totalCount',   label: 'Total Agents',          group: 'Agents',    description: 'Total active agent count.',                  defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'agents.byStatus',     label: 'Agents by Status',      group: 'Agents',    description: 'Idle / busy / error / offline breakdown.',   defaultType: 'pie',   compatibleTypes: ['pie', 'bar'] },
  { key: 'agents.byDomain',     label: 'Agents by Domain',      group: 'Agents',    description: 'Code / reason / research / fast / sec.',     defaultType: 'pie',   compatibleTypes: ['pie', 'bar'] },
  { key: 'agents.tokenLeaders', label: 'Top Agents by Tokens',  group: 'Agents',    description: 'Top 10 agents by total token usage.',        defaultType: 'bar',   compatibleTypes: ['bar', 'table'] },
  { key: 'agents.list',         label: 'Agent Roster',          group: 'Agents',    description: 'Full table of agents and status.',           defaultType: 'table', compatibleTypes: ['table'] },

  // Tokens
  { key: 'tokens.budget',       label: 'Session Token Budget',  group: 'Tokens',    description: 'Used vs. total session token budget.',       defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'tokens.burnRate',     label: 'Token Burn Rate',       group: 'Tokens',    description: 'Current tokens per minute.',                 defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'tokens.lastHour',     label: 'Tokens Last Hour',      group: 'Tokens',    description: 'Total tokens consumed in the past hour.',    defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'tokens.history',      label: 'Token Usage (24h)',     group: 'Tokens',    description: 'Hourly token consumption time-series.',      defaultType: 'line',  compatibleTypes: ['line', 'bar'] },
  { key: 'tokens.byModel',      label: 'Tokens by Model',       group: 'Tokens',    description: 'Token consumption grouped by LLM model.',    defaultType: 'pie',   compatibleTypes: ['pie', 'bar'] },

  // Governor
  { key: 'governor.approvalRate', label: 'Governor ALLOW Rate', group: 'Governor',  description: 'Percentage of decisions that were ALLOW.',   defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'governor.byDecision',   label: 'Decisions Breakdown', group: 'Governor',  description: 'ALLOW / DENY / HOLD distribution.',          defaultType: 'pie',   compatibleTypes: ['pie', 'bar'] },
  { key: 'governor.decisions',    label: 'Recent Decisions',    group: 'Governor',  description: 'Latest governor decisions.',                 defaultType: 'table', compatibleTypes: ['table'] },

  // Vault
  { key: 'vault.size',    label: 'Vault Size',          group: 'Vault',    description: 'Total entries across all tracks.',           defaultType: 'kpi',  compatibleTypes: ['kpi'] },
  { key: 'vault.byTrack', label: 'Vault by Track',      group: 'Vault',    description: 'EVENT / TRUST / CAP / FAIL / GOV split.',    defaultType: 'pie',  compatibleTypes: ['pie', 'bar'] },

  // Swarm
  { key: 'swarm.byStatus',     label: 'Swarm Status',        group: 'Swarm',   description: 'Worker status distribution.',                defaultType: 'bar',   compatibleTypes: ['bar', 'pie'] },
  { key: 'swarm.trustAverage', label: 'Avg Swarm Trust',     group: 'Swarm',   description: 'Mean trust score across the swarm.',         defaultType: 'kpi',   compatibleTypes: ['kpi'] },

  // Models
  { key: 'models.byProvider', label: 'Models by Provider', group: 'Models',  description: 'Distribution across providers.',             defaultType: 'pie',   compatibleTypes: ['pie', 'bar'] },
  { key: 'models.health',     label: 'Model Health Table', group: 'Models',  description: 'Health, latency, provider per model.',       defaultType: 'table', compatibleTypes: ['table'] },

  // Tests
  { key: 'tests.passRate',  label: 'Test Pass Rate',  group: 'StressLab', description: 'Percentage of passing tests.',               defaultType: 'kpi',   compatibleTypes: ['kpi'] },
  { key: 'tests.byStatus',  label: 'Tests by Status', group: 'StressLab', description: 'Passed / failed / pending counts.',          defaultType: 'bar',   compatibleTypes: ['bar', 'pie'] },
  { key: 'tests.recent',    label: 'Recent Tests',    group: 'StressLab', description: 'Latest stress test runs.',                   defaultType: 'table', compatibleTypes: ['table'] },

  // Research
  { key: 'research.papers',     label: 'Papers Indexed',    group: 'Research', description: 'Total papers in the research vault.',       defaultType: 'kpi',  compatibleTypes: ['kpi'] },
  { key: 'research.byCategory', label: 'Papers by Category', group: 'Research', description: 'Top arXiv categories.',                     defaultType: 'pie',  compatibleTypes: ['pie', 'bar'] },

  // Rate Limit
  { key: 'rateLimit.recent', label: 'Rate-Limit Log', group: 'API', description: 'Most recent rate-limited API calls.', defaultType: 'table', compatibleTypes: ['table'] },
]

export function getDataSource(key: string) {
  return DATA_SOURCES.find((s) => s.key === key)
}

export const WIDGET_TYPE_META: Record<WidgetType, { label: string; defaultSize: { width: number; height: number } }> = {
  kpi:   { label: 'KPI Card',   defaultSize: { width: 4,  height: 2 } },
  line:  { label: 'Line Chart', defaultSize: { width: 6,  height: 3 } },
  bar:   { label: 'Bar Chart',  defaultSize: { width: 6,  height: 3 } },
  pie:   { label: 'Pie Chart',  defaultSize: { width: 6,  height: 3 } },
  table: { label: 'Table',      defaultSize: { width: 12, height: 4 } },
}

export const COLOR_PALETTE = [
  '#34d399', // emerald
  '#60a5fa', // blue
  '#fb923c', // orange
  '#facc15', // yellow
  '#f472b6', // pink
  '#a78bfa', // purple
  '#22d3ee', // cyan
  '#f87171', // red
] as const

export const DASHBOARD_ACCENTS = {
  emerald: { from: '#10b981', to: '#34d399', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10' },
  blue:    { from: '#2563eb', to: '#60a5fa', text: 'text-blue-600 dark:text-blue-400',       bg: 'bg-blue-500/10' },
  orange:  { from: '#ea580c', to: '#fb923c', text: 'text-orange-600 dark:text-orange-400',   bg: 'bg-orange-500/10' },
  pink:    { from: '#db2777', to: '#f472b6', text: 'text-pink-600 dark:text-pink-400',       bg: 'bg-pink-500/10' },
  purple:  { from: '#7c3aed', to: '#a78bfa', text: 'text-purple-600 dark:text-purple-400',   bg: 'bg-purple-500/10' },
  cyan:    { from: '#0891b2', to: '#22d3ee', text: 'text-cyan-600 dark:text-cyan-400',       bg: 'bg-cyan-500/10' },
} as const

export type AccentColor = keyof typeof DASHBOARD_ACCENTS
