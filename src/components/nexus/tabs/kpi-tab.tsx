'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Target,
  TrendingUp,
  Shield,
  Zap,
  Users,
  Brain,
  Clock,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Gauge,
  ChevronDown,
  ChevronUp,
  Heart,
  BarChart3,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
  ReferenceLine,
  ReferenceArea,
} from 'recharts'

const kpiCategories = [
  {
    name: 'System Health',
    icon: Activity,
    kpis: [
      { label: 'Uptime', value: '99.7%', target: '99.9%', status: 'warning', trend: 'stable', trendData: [99.5, 99.6, 99.7, 99.8, 99.7, 99.6, 99.7], targetVal: 99.9 },
      { label: 'Error Rate', value: '0.3%', target: '<1%', status: 'ok', trend: 'down', trendData: [0.5, 0.4, 0.3, 0.4, 0.3, 0.2, 0.3], targetVal: 1.0 },
      { label: 'Avg Latency', value: '142ms', target: '<200ms', status: 'ok', trend: 'down', trendData: [180, 165, 150, 142, 138, 145, 142], targetVal: 200 },
      { label: 'P99 Latency', value: '387ms', target: '<500ms', status: 'ok', trend: 'up', trendData: [420, 410, 395, 387, 390, 385, 387], targetVal: 500 },
    ],
  },
  {
    name: 'Agent Performance',
    icon: Users,
    kpis: [
      { label: 'Active Agents', value: '4/5', target: '≤5', status: 'ok', trend: 'stable', trendData: [4, 4, 5, 4, 4, 4, 4], targetVal: 5 },
      { label: 'Avg Trust Score', value: '0.88', target: '>0.8', status: 'ok', trend: 'up', trendData: [0.82, 0.84, 0.85, 0.86, 0.87, 0.88, 0.88], targetVal: 0.8 },
      { label: 'Task Completion', value: '94.2%', target: '>90%', status: 'ok', trend: 'up', trendData: [92, 93, 93, 94, 93, 94, 94.2], targetVal: 90 },
      { label: 'Failed Tasks (24h)', value: '10', target: '<15', status: 'ok', trend: 'down', trendData: [14, 13, 12, 11, 10, 11, 10], targetVal: 15 },
    ],
  },
  {
    name: 'Governor Effectiveness',
    icon: Shield,
    kpis: [
      { label: 'Blocked Actions', value: '3', target: 'Track only', status: 'ok', trend: 'up', trendData: [1, 2, 2, 3, 2, 3, 3], targetVal: 0 },
      { label: 'False Positive Rate', value: '2.1%', target: '<5%', status: 'ok', trend: 'down', trendData: [3.5, 3.2, 2.8, 2.5, 2.3, 2.2, 2.1], targetVal: 5 },
      { label: 'Constitution Compliance', value: '100%', target: '100%', status: 'ok', trend: 'stable', trendData: [100, 100, 100, 100, 100, 100, 100], targetVal: 100 },
      { label: 'Danger Patterns Matched', value: '3', target: 'Track only', status: 'ok', trend: 'stable', trendData: [2, 3, 2, 3, 3, 3, 3], targetVal: 0 },
    ],
  },
  {
    name: 'Model & Token Efficiency',
    icon: Brain,
    kpis: [
      { label: 'Budget Utilization', value: '26.6%', target: '<80%', status: 'ok', trend: 'up', trendData: [15, 18, 20, 22, 24, 25, 26.6], targetVal: 80 },
      { label: 'Burn Rate', value: '142 tok/min', target: '<500', status: 'ok', trend: 'stable', trendData: [120, 130, 135, 140, 142, 141, 142], targetVal: 500 },
      { label: 'Model Availability', value: '7/7', target: '100%', status: 'ok', trend: 'stable', trendData: [7, 7, 7, 7, 7, 7, 7], targetVal: 7 },
      { label: 'Failover Time', value: '1.2s avg', target: '<3s', status: 'ok', trend: 'down', trendData: [2.1, 1.8, 1.6, 1.4, 1.3, 1.2, 1.2], targetVal: 3 },
    ],
  },
]

const statusConfig = {
  ok: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/20', gradient: 'from-emerald-600/10 to-emerald-600/5', chartColor: '#10b981' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/20', gradient: 'from-yellow-600/10 to-yellow-600/5', chartColor: '#eab308' },
  critical: { icon: AlertTriangle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/20', gradient: 'from-red-600/10 to-red-600/5', chartColor: '#ef4444' },
}

const trendConfig = {
  up: { icon: TrendingUp, label: 'Up' },
  down: { icon: TrendingUp, label: 'Down' },
  stable: { icon: Activity, label: 'Stable' },
}

// Sparkline data
const sparklineData = [
  { label: 'Uptime', values: [99.5, 99.6, 99.7, 99.8, 99.7, 99.6, 99.7, 99.8, 99.9, 99.7, 99.6, 99.7], color: '#10b981' },
  { label: 'Error Rate', values: [0.5, 0.4, 0.3, 0.4, 0.3, 0.2, 0.3, 0.4, 0.3, 0.2, 0.3, 0.3], color: '#ef4444' },
  { label: 'Latency', values: [180, 165, 150, 142, 138, 145, 152, 148, 142, 139, 145, 142], color: '#3b82f6' },
  { label: 'Trust Score', values: [0.82, 0.84, 0.85, 0.86, 0.87, 0.86, 0.87, 0.88, 0.87, 0.88, 0.88, 0.88], color: '#10b981' },
  { label: 'Budget Used', values: [15, 18, 20, 21, 22, 23, 24, 24.5, 25, 25.5, 26, 26.6], color: '#f97316' },
  { label: 'Task Success', values: [92, 93, 93, 94, 93, 94, 94, 95, 94, 94, 94, 94.2], color: '#10b981' },
]

// Radar chart data
const radarData = [
  { category: 'System Health', score: 91, fullMark: 100 },
  { category: 'Agent Perf', score: 94, fullMark: 100 },
  { category: 'Governor Eff.', score: 97, fullMark: 100 },
  { category: 'Model/Token Eff.', score: 93, fullMark: 100 },
]

// Trend comparison data (7 days)
const trendComparisonData = [
  { day: 'Mon', current: 90, target: 95 },
  { day: 'Tue', current: 92, target: 95 },
  { day: 'Wed', current: 89, target: 95 },
  { day: 'Thu', current: 93, target: 95 },
  { day: 'Fri', current: 94, target: 95 },
  { day: 'Sat', current: 92, target: 95 },
  { day: 'Sun', current: 95, target: 95 },
]

// Gauge data for overall system score
const gaugeData = [
  { name: 'Score', value: 95, fill: '#10b981' },
  { name: 'Remaining', value: 5, fill: '#1f2937' },
]

// KPI Score Breakdown donut data
const kpiBreakdownData = [
  { name: 'OK', value: 15, color: '#10b981' },
  { name: 'Warning', value: 1, color: '#eab308' },
  { name: 'Critical', value: 0, color: '#ef4444' },
]

// Historical Performance data (30 days) - stacked area chart
const generateHistoricalData = () => {
  const days = []
  for (let i = 29; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    const dayLabel = `${date.getMonth() + 1}/${date.getDate()}`
    days.push({
      day: dayLabel,
      systemHealth: 88 + Math.random() * 8,
      agentPerf: 90 + Math.random() * 7,
      governorEff: 94 + Math.random() * 5,
      modelTokenEff: 89 + Math.random() * 8,
    })
  }
  return days
}

const historicalData = generateHistoricalData()

// Health Score History (7 days)
const healthScoreHistory = [
  { day: 'Mon', score: 91 },
  { day: 'Tue', score: 93 },
  { day: 'Wed', score: 89 },
  { day: 'Thu', score: 94 },
  { day: 'Fri', score: 95 },
  { day: 'Sat', score: 92 },
  { day: 'Sun', score: 95 },
]

// Recharts-based sparkline component
function RechartsSparkLine({ values, color }: { values: number[]; color: string }) {
  const data = values.map((v, i) => ({ value: v, index: i }))

  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <defs>
          <linearGradient id={`sparkGrad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.4} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#sparkGrad-${color.replace('#', '')})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// Individual KPI card with hover expansion
function KpiCard({ kpi }: { kpi: typeof kpiCategories[0]['kpis'][0] }) {
  const [expanded, setExpanded] = useState(false)
  const status = statusConfig[kpi.status as keyof typeof statusConfig]
  const StatusIcon = status.icon

  const trendLabels = ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', '1d ago', 'Today']

  return (
    <motion.div
      layout
      className={cn('p-3 rounded-lg bg-gradient-to-br border border-border/30 cursor-pointer', status.gradient)}
      onClick={() => setExpanded(!expanded)}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{kpi.label}</span>
        <div className="flex items-center gap-1.5">
          <StatusIcon className={`h-3.5 w-3.5 ${status.color}`} />
          {expanded ? <ChevronUp className="h-3 w-3 text-muted-foreground" /> : <ChevronDown className="h-3 w-3 text-muted-foreground" />}
        </div>
      </div>
      <div className="text-lg font-bold mt-1">{kpi.value}</div>
      <div className="flex items-center justify-between mt-1">
        <span className="text-[10px] text-muted-foreground">Target: {kpi.target}</span>
        <Badge className={`text-[9px] h-4 border-0 ${status.bg} ${status.color}`}>
          {kpi.status.toUpperCase()}
        </Badge>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-border/30">
              <div className="text-[10px] text-muted-foreground mb-1">7-Day Trend</div>
              <div className="h-16">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={kpi.trendData.map((v, i) => ({ value: v, day: trendLabels[i] }))} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                    <defs>
                      <linearGradient id={`kpiTrend-${kpi.label.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={status.chartColor} stopOpacity={0.4} />
                        <stop offset="95%" stopColor={status.chartColor} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke={status.chartColor}
                      strokeWidth={1.5}
                      fill={`url(#kpiTrend-${kpi.label.replace(/\s/g, '')})`}
                      dot={{ r: 2, fill: status.chartColor }}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[9px] text-muted-foreground">Trend: {trendConfig[kpi.trend as keyof typeof trendConfig].label}</span>
                <span className="text-[9px] text-muted-foreground">Target: {kpi.target}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function KpiTab() {
  const okCount = kpiCategories.reduce((sum, cat) => sum + cat.kpis.filter(k => k.status === 'ok').length, 0)
  const warningCount = kpiCategories.reduce((sum, cat) => sum + cat.kpis.filter(k => k.status === 'warning').length, 0)
  const criticalCount = kpiCategories.reduce((sum, cat) => sum + cat.kpis.filter(k => k.status === 'critical').length, 0)
  const totalKpis = kpiCategories.reduce((sum, cat) => sum + cat.kpis.length, 0)
  const overallScore = Math.round((okCount / totalKpis) * 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Target className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">KPI Dashboard — Key Performance Indicators</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">{totalKpis} KPIs</Badge>
      </div>

      {/* Description */}
      <Card className="bg-muted/30 border-border/50">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Monitor system health, agent efficiency, governance effectiveness, and model resource utilization.{' '}
            Overall grade is calculated from the ratio of on-target KPIs across all categories.{' '}
            Grades are assigned as follows: <strong>A+</strong> ≥ 95% on-target,{' '}
            <strong>A</strong> ≥ 90%, <strong>B</strong> ≥ 80%, <strong>C</strong> ≥ 70%, <strong>D</strong> &lt; 70%.
          </p>
        </CardContent>
      </Card>

      {/* Top-level Score + Performance Gauge + KPI Score Breakdown Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top-level Score */}
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">{overallScore}%</div>
                <div className="text-xs text-muted-foreground mt-1">KPIs On Target</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">{okCount}</div>
                <div className="text-xs text-muted-foreground mt-1">OK</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-yellow-600 dark:text-yellow-400">{warningCount}</div>
                <div className="text-xs text-muted-foreground mt-1">Warning</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold">A+</div>
                <div className="text-xs text-muted-foreground mt-1">Overall Grade</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Gauge */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Gauge className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Performance Gauge
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 flex flex-col items-center">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={gaugeData}
                  cx="50%"
                  cy="100%"
                  startAngle={180}
                  endAngle={0}
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={0}
                  dataKey="value"
                  stroke="none"
                >
                  {gaugeData.map((entry, index) => (
                    <Cell key={`gauge-cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="text-center -mt-8">
              <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">95%</div>
              <div className="text-[10px] text-muted-foreground">Overall System Score</div>
            </div>
          </CardContent>
        </Card>

        {/* KPI Score Breakdown Donut */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              KPI Score Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 flex flex-col items-center">
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie
                  data={kpiBreakdownData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={65}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                  stroke="none"
                >
                  {kpiBreakdownData.map((entry, index) => (
                    <Cell key={`breakdown-cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex items-center gap-4 mt-2">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <span className="text-[10px] text-muted-foreground">OK ({okCount})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-yellow-500" />
                <span className="text-[10px] text-muted-foreground">Warning ({warningCount})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
                <span className="text-[10px] text-muted-foreground">Critical ({criticalCount})</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health Score History + KPI Radar Chart - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Health Score History with severity bands */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Heart className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Health Score History (7 Days)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={healthScoreHistory} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="healthScoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.5} />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="#6b7280" tickLine={false} axisLine={false} />
                <YAxis domain={[70, 100]} tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                {/* Severity bands */}
                <ReferenceArea y1={90} y2={100} fill="#10b981" fillOpacity={0.05} />
                <ReferenceArea y1={75} y2={90} fill="#eab308" fillOpacity={0.05} />
                <ReferenceArea y1={70} y2={75} fill="#ef4444" fillOpacity={0.05} />
                <ReferenceLine y={90} stroke="#10b981" strokeDasharray="4 4" strokeOpacity={0.4} label={{ value: 'A', position: 'right', fill: '#10b981', fontSize: 9 }} />
                <ReferenceLine y={75} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.4} label={{ value: 'B', position: 'right', fill: '#eab308', fontSize: 9 }} />
                <Area type="monotone" dataKey="score" name="Health Score" stroke="#10b981" strokeWidth={2.5} fill="url(#healthScoreGrad)" dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* KPI Radar Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Target className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              KPI Radar Chart
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9, fill: '#6b7280' }} />
                <Radar
                  name="Score"
                  dataKey="score"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.25}
                  strokeWidth={2}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Historical Performance - Stacked Area Chart (30 days) with severity bands */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Historical Performance (30 Days)
            <Badge variant="outline" className="text-[9px] ml-auto">4 Categories</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={historicalData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="histSystemHealth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="histAgentPerf" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="histGovernorEff" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="histModelToken" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.3} />
              <XAxis dataKey="day" tick={{ fontSize: 9 }} stroke="#6b7280" tickLine={false} axisLine={false} interval={4} />
              <YAxis domain={[80, 100]} tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              {/* Severity bands */}
              <ReferenceArea y1={90} y2={100} fill="#10b981" fillOpacity={0.04} />
              <ReferenceArea y1={80} y2={90} fill="#eab308" fillOpacity={0.04} />
              <ReferenceLine y={90} stroke="#10b981" strokeDasharray="4 4" strokeOpacity={0.3} />
              <Area type="monotone" dataKey="systemHealth" name="System Health" stroke="#10b981" strokeWidth={2} fill="url(#histSystemHealth)" dot={false} />
              <Area type="monotone" dataKey="agentPerf" name="Agent Perf" stroke="#f97316" strokeWidth={2} fill="url(#histAgentPerf)" dot={false} />
              <Area type="monotone" dataKey="governorEff" name="Governor Eff." stroke="#8b5cf6" strokeWidth={2} fill="url(#histGovernorEff)" dot={false} />
              <Area type="monotone" dataKey="modelTokenEff" name="Model/Token Eff." stroke="#06b6d4" strokeWidth={2} fill="url(#histModelToken)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Trend Comparison Line Chart with severity bands */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Trend Comparison (7 Days)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendComparisonData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.3} />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="#6b7280" tickLine={false} axisLine={false} />
              <YAxis domain={[80, 100]} tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              {/* Severity bands */}
              <ReferenceArea y1={95} y2={100} fill="#10b981" fillOpacity={0.06} />
              <ReferenceArea y1={85} y2={95} fill="#eab308" fillOpacity={0.04} />
              <ReferenceArea y1={80} y2={85} fill="#ef4444" fillOpacity={0.04} />
              <ReferenceLine y={95} stroke="#10b981" strokeDasharray="4 4" strokeOpacity={0.3} label={{ value: 'A+', position: 'right', fill: '#10b981', fontSize: 9 }} />
              <ReferenceLine y={85} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.3} label={{ value: 'B', position: 'right', fill: '#eab308', fontSize: 9 }} />
              <Line type="monotone" dataKey="current" name="Current" stroke="#10b981" strokeWidth={2.5} dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="target" name="Target" stroke="#f97316" strokeWidth={2} strokeDasharray="5 5" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* KPI Categories with expandable KPI cards */}
      {kpiCategories.map((category) => {
        const categoryOkCount = category.kpis.filter(k => k.status === 'ok').length
        const hasWarning = category.kpis.some(k => k.status === 'warning')
        const hasCritical = category.kpis.some(k => k.status === 'critical')
        const gradientClass = hasCritical ? 'from-red-600/5 to-transparent' : hasWarning ? 'from-yellow-600/5 to-transparent' : 'from-emerald-600/5 to-transparent'

        return (
          <Card key={category.name} className={cn('bg-card/50 border-border/50 bg-gradient-to-br', gradientClass)}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <category.icon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                {category.name}
                <Badge variant="outline" className="text-[10px] ml-auto">
                  {categoryOkCount}/{category.kpis.length} OK
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {category.kpis.map((kpi) => (
                  <KpiCard key={kpi.label} kpi={kpi} />
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}

      {/* Trend Sparklines with Recharts AreaChart */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            24h Trend Sparklines
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {sparklineData.map((chart) => (
              <div key={chart.label} className="space-y-1">
                <div className="text-[10px] text-muted-foreground">{chart.label}</div>
                <RechartsSparkLine values={chart.values} color={chart.color} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
