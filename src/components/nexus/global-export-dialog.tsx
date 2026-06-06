'use client'

import { useState, useCallback } from 'react'
import { Download, FileJson, FileSpreadsheet, Clock, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { downloadFile, toCSV } from '@/components/nexus/export-button'
import { toast } from 'sonner'

// Comprehensive dashboard data for all 8 pillars
function getFullDashboardReport() {
  const now = new Date().toISOString()

  return {
    exportedAt: now,
    version: 'NEXUS OS v3.0',
    session: {
      uptime: '3d 14h 27m',
      availability: '99.94%',
      activeNodes: 3,
    },
    pillars: [
      { name: 'Bridge', status: 'operational', health: 100, uptime: '99.99%', description: 'HMAC auth · JSON-RPC' },
      { name: 'Engine', status: 'operational', health: 98, uptime: '99.94%', description: 'Hermes intent routing' },
      { name: 'Governor', status: 'operational', health: 95, uptime: '99.87%', description: 'Kaiju + TrustScorer' },
      { name: 'Vault', status: 'operational', health: 100, uptime: '100%', description: '5-Track memory' },
      { name: 'GMR', status: 'operational', health: 92, uptime: '99.71%', description: 'Model rotation' },
      { name: 'Swarm', status: 'degraded', health: 88, uptime: '98.44%', description: 'Worker pool' },
      { name: 'Monitor', status: 'operational', health: 96, uptime: '99.92%', description: 'Token budget + audit' },
      { name: 'Config', status: 'operational', health: 100, uptime: '100%', description: 'Constitution' },
    ],
    tokenBudget: {
      remaining: 73450,
      max: 100000,
      utilizationPct: 73.45,
      burnRate: '1,240 tok/min',
      estimatedTimeRemaining: '21m 12s',
    },
    agents: [
      { name: 'coordinator', trust: 0.91, status: 'active', decisions: 234, lane: 'impl' },
      { name: 'worker-1', trust: 0.73, status: 'busy', decisions: 189, lane: 'review' },
      { name: 'worker-2', trust: 0.45, status: 'error', decisions: 156, lane: 'research' },
      { name: 'worker-3', trust: 0.82, status: 'busy', decisions: 312, lane: 'audit' },
      { name: 'research-agent', trust: 0.62, status: 'active', decisions: 87, lane: 'research' },
    ],
    governor: {
      totalDecisions24h: 875,
      allow: 847,
      deny: 23,
      hold: 5,
      avgTrustScore: 0.73,
      activeConstitutionRules: 7,
      totalRuleTriggers: 123,
    },
    stresslab: {
      templatesLoaded: 84,
      totalRuns: 47,
      collapseRate: 23.4,
      collapseRateBaseline: 95.3,
      governorBlocks: 8,
      passCount: 24,
      failCount: 11,
      warningCount: 8,
    },
    gmr: {
      modelsOnline: 6,
      avgHealth: 91.3,
      activePool: 'PREMIUM',
      failoverEvents: 3,
      rotationCount24h: 53,
    },
    vault: {
      totalEntries: 1792,
      activeTracks: 5,
      vapChainLength: 1247,
      latestEntry: 'V-2047',
      avgScore: 0.73,
    },
    swarm: {
      totalWorkers: 5,
      busyWorkers: 2,
      idleWorkers: 2,
      errorWorkers: 1,
      tasksQueued: 4,
      tasksCompleted24h: 156,
    },
    research: {
      p0Papers: 3,
      p1Papers: 5,
      p2Papers: 4,
      totalPapers: 12,
      dailyPracticeActive: true,
    },
  }
}

// Individual tab data exports
function getTabData(tab: string): Record<string, unknown>[] {
  switch (tab) {
    case 'overview':
      return [
        { pillar: 'Bridge', status: 'operational', health: 100, uptime: '99.99%' },
        { pillar: 'Engine', status: 'operational', health: 98, uptime: '99.94%' },
        { pillar: 'Governor', status: 'operational', health: 95, uptime: '99.87%' },
        { pillar: 'Vault', status: 'operational', health: 100, uptime: '100%' },
        { pillar: 'GMR', status: 'operational', health: 92, uptime: '99.71%' },
        { pillar: 'Swarm', status: 'degraded', health: 88, uptime: '98.44%' },
        { pillar: 'Monitor', status: 'operational', health: 96, uptime: '99.92%' },
        { pillar: 'Config', status: 'operational', health: 100, uptime: '100%' },
      ]
    case 'governor':
      return [
        { time: '14:23:01', agent: 'worker-3', action: 'read file', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.82 },
        { time: '14:22:45', agent: 'coordinator', action: 'spawn sub-agent', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.91 },
        { time: '14:22:12', agent: 'worker-1', action: 'write config', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.73 },
        { time: '14:21:58', agent: 'worker-2', action: 'delete all vault entries', scope: 'SYSTEM', impact: 'CRIT', decision: 'DENY', trust: 0.45 },
        { time: '14:21:30', agent: 'research-agent', action: 'API call external', scope: 'CROSS', impact: 'MED', decision: 'HOLD', trust: 0.62 },
      ]
    case 'stresslab':
      return [
        { id: 'T-0847', template: 'ISC-001', model: 'qwen3-coder', mode: 'agentic', result: 'COLLAPSE', tokens: 3420, duration: '14s' },
        { id: 'T-0846', template: 'ISC-004', model: 'trinity-large', mode: 'single', result: 'PASS', tokens: 1280, duration: '8s' },
        { id: 'T-0845', template: 'ISC-002', model: 'nemotron', mode: 'icl', result: 'COLLAPSE', tokens: 2840, duration: '12s' },
        { id: 'T-0844', template: 'ISC-005', model: 'gemma-fast', mode: 'single', result: 'PASS', tokens: 640, duration: '3s' },
        { id: 'T-0843', template: 'ISC-001', model: 'dolphin-mistral', mode: 'agentic', result: 'COLLAPSE', tokens: 4100, duration: '18s' },
      ]
    case 'gmr':
      return [
        { model: 'trinity-large-preview', pool: 'PREMIUM', health: 97, latency: 1350, calls: 512, active: true },
        { model: 'qwen3-coder', pool: 'PREMIUM', health: 82, latency: 980, calls: 1024, active: true },
        { model: 'nemotron-3-super', pool: 'MID', health: 60, latency: 740, calls: 256, active: true },
        { model: 'gemma-fast', pool: 'FAST', health: 50, latency: 340, calls: 2048, active: true },
        { model: 'dolphin-mistral-venice', pool: 'HERETIC', health: 15, latency: 2200, calls: 128, active: false },
        { model: 'kimi-k2.5', pool: 'FREE_RESEARCH', health: 88, latency: 1600, calls: 64, active: true },
      ]
    case 'vault':
      return [
        { id: 'V-2047', track: 'EVENT', agent: 'coordinator', key: 'session.start', score: 1.0, timestamp: '2025-01-15T14:23:01Z' },
        { id: 'V-2046', track: 'TRUST', agent: 'worker-3', key: 'trust.update', score: 0.82, timestamp: '2025-01-15T14:22:45Z' },
        { id: 'V-2045', track: 'CAP', agent: 'worker-1', key: 'skill.registered', score: 0.73, timestamp: '2025-01-15T14:22:12Z' },
        { id: 'V-2044', track: 'FAIL', agent: 'worker-2', key: 'action.denied', score: 0.45, timestamp: '2025-01-15T14:21:58Z' },
        { id: 'V-2043', track: 'GOV', agent: 'governor', key: 'constitution.check', score: 0.91, timestamp: '2025-01-15T14:21:30Z' },
      ]
    case 'research':
      return [
        { id: 'P-001', title: 'Constitutional AI Safety', priority: 'P0', status: 'in_progress', relevance: 0.94 },
        { id: 'P-002', title: 'Multi-Agent Orchestration', priority: 'P0', status: 'active', relevance: 0.91 },
        { id: 'P-003', title: 'Red-Team Benchmarking', priority: 'P0', status: 'pending', relevance: 0.88 },
        { id: 'P-004', title: 'Chain-of-Thought Elicitation', priority: 'P1', status: 'active', relevance: 0.85 },
        { id: 'P-005', title: 'Tool Use Robustness', priority: 'P1', status: 'pending', relevance: 0.82 },
      ]
    case 'swarm':
      return [
        { id: 'worker-1', status: 'busy', task: 'T-0848', domain: 'code', progress: 67, tokens: 12400, uptime: '2h 34m' },
        { id: 'worker-2', status: 'error', task: 'T-0846', domain: 'research', progress: 34, tokens: 8200, uptime: '1h 12m' },
        { id: 'worker-3', status: 'busy', task: 'T-0849', domain: 'cyber', progress: 89, tokens: 18600, uptime: '3h 01m' },
        { id: 'worker-4', status: 'idle', task: '—', domain: '—', progress: 0, tokens: 0, uptime: '0h 45m' },
        { id: 'worker-5', status: 'idle', task: '—', domain: '—', progress: 0, tokens: 0, uptime: '0h 22m' },
      ]
    case 'tokens':
      return [
        { model: 'gemma-fast', tokens: 22400, calls: 1024, avgLatency: 340, cost: 0 },
        { model: 'trinity-large', tokens: 18200, calls: 512, avgLatency: 1350, cost: 0 },
        { model: 'qwen3-coder', tokens: 15800, calls: 384, avgLatency: 980, cost: 0 },
        { model: 'nemotron-3', tokens: 8400, calls: 256, avgLatency: 740, cost: 0 },
        { model: 'kimi-k2.5', tokens: 5100, calls: 64, avgLatency: 1600, cost: 0 },
        { model: 'dolphin-mistral', tokens: 3550, calls: 128, avgLatency: 2200, cost: 0 },
      ]
    default:
      return []
  }
}

const tabNames: Record<string, string> = {
  overview: 'Overview (System Status)',
  governor: 'Governor (Decision Log)',
  stresslab: 'StressLab (Test Results)',
  gmr: 'GMR (Model Registry)',
  vault: 'Vault (Entry Data)',
  research: 'Research (Paper Queue)',
  swarm: 'Swarm (Worker Status)',
  tokens: 'Tokens (Usage Data)',
}

interface GlobalExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function GlobalExportDialog({ open, onOpenChange }: GlobalExportDialogProps) {
  const [scope, setScope] = useState<'full' | 'individual'>('full')
  const [selectedTab, setSelectedTab] = useState('overview')
  const [format, setFormat] = useState<'json' | 'csv'>('json')
  const [dateRange, setDateRange] = useState<'session' | '24h' | 'all'>('session')
  const [exporting, setExporting] = useState(false)

  const handleExport = useCallback(() => {
    setExporting(true)

    // Simulate brief processing
    setTimeout(() => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const dateRangeLabel = dateRange === 'session' ? 'session' : dateRange === '24h' ? 'last-24h' : 'all-time'

      if (scope === 'full') {
        const report = getFullDashboardReport()
        // Add date range label to report
        const enrichedReport = { ...report, dateRange: dateRangeLabel }

        if (format === 'json') {
          const content = JSON.stringify(enrichedReport, null, 2)
          downloadFile(content, `nexus-dashboard-report-${timestamp}.json`, 'application/json;charset=utf-8;')
        } else {
          // For CSV, flatten the report into a summary table
          const pillarData = report.pillars
          const csv = toCSV(pillarData)
          downloadFile(csv, `nexus-dashboard-report-${timestamp}.csv`, 'text/csv;charset=utf-8;')
        }

        toast.success('Dashboard report exported', {
          description: `Full NEXUS OS report (${format.toUpperCase()}) — ${dateRangeLabel}`,
        })
      } else {
        const data = getTabData(selectedTab)
        const tabLabel = tabNames[selectedTab] || selectedTab
        const filename = `nexus-${selectedTab}-${dateRangeLabel}-${timestamp}`

        if (format === 'json') {
          const content = JSON.stringify({
            exportedAt: new Date().toISOString(),
            source: tabLabel,
            dateRange: dateRangeLabel,
            data,
          }, null, 2)
          downloadFile(content, `${filename}.json`, 'application/json;charset=utf-8;')
        } else {
          const csv = toCSV(data)
          downloadFile(csv, `${filename}.csv`, 'text/csv;charset=utf-8;')
        }

        toast.success(`${tabLabel} data exported`, {
          description: `${data.length} rows exported as ${format.toUpperCase()} — ${dateRangeLabel}`,
        })
      }

      setExporting(false)
      onOpenChange(false)
    }, 300)
  }, [scope, selectedTab, format, dateRange, onOpenChange])

  const estimatedRows = scope === 'full' ? 8 : getTabData(selectedTab).length

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Export Dashboard
          </DialogTitle>
          <DialogDescription>
            Choose what data to export from the NEXUS OS Command Center
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Export Scope */}
          <div className="space-y-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">What to Export</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setScope('full')}
                className={`relative rounded-lg border p-3 text-left transition-all duration-200 ${
                  scope === 'full'
                    ? 'border-emerald-600/40 bg-emerald-600/5 shadow-sm shadow-emerald-600/10'
                    : 'border-border/60 bg-card hover:border-emerald-600/20 hover:bg-emerald-600/3'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div className={`flex h-6 w-6 items-center justify-center rounded-md ${
                    scope === 'full' ? 'bg-emerald-600/15' : 'bg-muted'
                  }`}>
                    <FileJson className={`h-3.5 w-3.5 ${scope === 'full' ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`} />
                  </div>
                  <span className="text-xs font-semibold">Full Dashboard</span>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Comprehensive report combining key metrics from all 8 pillars
                </p>
                {scope === 'full' && (
                  <div className="absolute top-2 right-2">
                    <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[8px] px-1.5 py-0">8 pillars</Badge>
                  </div>
                )}
              </button>
              <button
                onClick={() => setScope('individual')}
                className={`relative rounded-lg border p-3 text-left transition-all duration-200 ${
                  scope === 'individual'
                    ? 'border-emerald-600/40 bg-emerald-600/5 shadow-sm shadow-emerald-600/10'
                    : 'border-border/60 bg-card hover:border-emerald-600/20 hover:bg-emerald-600/3'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div className={`flex h-6 w-6 items-center justify-center rounded-md ${
                    scope === 'individual' ? 'bg-emerald-600/15' : 'bg-muted'
                  }`}>
                    <FileSpreadsheet className={`h-3.5 w-3.5 ${scope === 'individual' ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`} />
                  </div>
                  <span className="text-xs font-semibold">Individual Tab</span>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Export data from a specific tab or module
                </p>
                {scope === 'individual' && (
                  <div className="absolute top-2 right-2">
                    <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[8px] px-1.5 py-0">{estimatedRows} rows</Badge>
                  </div>
                )}
              </button>
            </div>
          </div>

          {/* Tab Selection (only for individual) */}
          {scope === 'individual' && (
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Select Tab</label>
              <Select value={selectedTab} onValueChange={setSelectedTab}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(tabNames).map(([key, name]) => (
                    <SelectItem key={key} value={key}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <Separator className="bg-border/50" />

          {/* Format Selection */}
          <div className="space-y-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Format</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setFormat('json')}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 transition-all duration-200 ${
                  format === 'json'
                    ? 'border-blue-600/40 bg-blue-600/5 shadow-sm'
                    : 'border-border/60 hover:border-blue-600/20'
                }`}
              >
                <FileJson className={`h-4 w-4 ${format === 'json' ? 'text-blue-600 dark:text-blue-400' : 'text-muted-foreground'}`} />
                <div>
                  <p className="text-xs font-medium">JSON</p>
                  <p className="text-[9px] text-muted-foreground">Structured data</p>
                </div>
              </button>
              <button
                onClick={() => setFormat('csv')}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 transition-all duration-200 ${
                  format === 'csv'
                    ? 'border-emerald-600/40 bg-emerald-600/5 shadow-sm'
                    : 'border-border/60 hover:border-emerald-600/20'
                }`}
              >
                <FileSpreadsheet className={`h-4 w-4 ${format === 'csv' ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`} />
                <div>
                  <p className="text-xs font-medium">CSV</p>
                  <p className="text-[9px] text-muted-foreground">Spreadsheet-ready</p>
                </div>
              </button>
            </div>
          </div>

          {/* Date Range */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Date Range</label>
            <div className="flex gap-2">
              {([
                { value: 'session' as const, label: 'Current Session' },
                { value: '24h' as const, label: 'Last 24h' },
                { value: 'all' as const, label: 'All Time' },
              ]).map((option) => (
                <button
                  key={option.value}
                  onClick={() => setDateRange(option.value)}
                  className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-[11px] font-medium transition-all duration-200 ${
                    dateRange === option.value
                      ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30'
                      : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                >
                  <Clock className="h-3 w-3" />
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Export Summary */}
          <div className="rounded-lg bg-accent/30 border border-border/50 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Export summary</span>
              <Badge variant="outline" className="text-[9px]">
                {scope === 'full' ? '8 pillars' : `${estimatedRows} rows`}
              </Badge>
            </div>
            <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
              <span>{scope === 'full' ? 'Full Dashboard Report' : tabNames[selectedTab]}</span>
              <span className="text-muted-foreground/40">·</span>
              <span>{format.toUpperCase()}</span>
              <span className="text-muted-foreground/40">·</span>
              <span>{dateRange === 'session' ? 'Current Session' : dateRange === '24h' ? 'Last 24h' : 'All Time'}</span>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? (
              <>
                <Download className="h-3.5 w-3.5 animate-pulse" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-3.5 w-3.5" />
                Export {format.toUpperCase()}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
