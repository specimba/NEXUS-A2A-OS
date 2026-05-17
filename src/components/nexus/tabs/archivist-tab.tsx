'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  BookMarked,
  Layers,
  Shield,
  CheckCircle2,
  AlertTriangle,
  ArrowUp,
  Archive,
  ArrowRight,
  Loader2,
  Hash,
  Clock,
  Activity,
  FileWarning,
  XCircle,
  ShieldCheck,
  FileCheck,
  GitBranch,
  Eye,
  Timer,
  User,
  AlertOctagon,
  Info,
  Zap,
  FileText,
} from 'lucide-react'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { toast } from 'sonner'

// ─── API Response Types ───

interface ArchivistAPIResponse {
  truthLayers: Record<string, number>
  authorityDistribution: Record<string, number>
  promotionQueue: { pending: number; underReview: number; promotedToday: number }
  curatorStats: { active: number; stale: number; archived: number }
  integrityFields: Record<string, { present: number; total: number }>
  contradictions: Array<{
    id: string
    nodeA: string
    nodeB: string
    field: string
    severity: string
    layerA: string
    layerB: string
  }>
  releaseReadiness: {
    governanceDocsClean: boolean
    coldStartUnified: boolean
    readmeRewritten: boolean
    pipelineCodeReleasable: boolean
    schemaMigrationComplete: boolean
    integrityGateConsolidated: boolean
  }
  source: string
}

// ─── Truth Layer Config ───

const TRUTH_LAYER_CONFIG: Record<string, {
  label: string
  description: string
  color: string
  bgColor: string
  borderColor: string
  textColor: string
  badge: string
}> = {
  SOURCE: {
    label: 'SOURCE',
    description: 'Directly from trusted origin. Highest authority.',
    color: '#10b981',
    bgColor: 'bg-emerald-600/15',
    borderColor: 'border-emerald-600/30',
    textColor: 'text-emerald-600 dark:text-emerald-400',
    badge: 'verified',
  },
  EXTRACTED: {
    label: 'EXTRACTED',
    description: 'Programmatically derived from source. Verified extraction.',
    color: '#3b82f6',
    bgColor: 'bg-blue-600/15',
    borderColor: 'border-blue-600/30',
    textColor: 'text-blue-600 dark:text-blue-400',
    badge: 'verified',
  },
  INFERRED: {
    label: 'INFERRED',
    description: 'Algorithmically deduced. Requires promotion gate for canon.',
    color: '#f59e0b',
    bgColor: 'bg-amber-600/15',
    borderColor: 'border-amber-600/30',
    textColor: 'text-amber-600 dark:text-amber-400',
    badge: 'pending verification',
  },
  CANONICAL: {
    label: 'CANONICAL',
    description: 'Promoted through governance gates. Immutable truth.',
    color: '#8b5cf6',
    bgColor: 'bg-purple-600/15',
    borderColor: 'border-purple-600/30',
    textColor: 'text-purple-600 dark:text-purple-400',
    badge: 'verified',
  },
}

const TRUTH_LAYER_ORDER = ['SOURCE', 'EXTRACTED', 'INFERRED', 'CANONICAL']

// ─── Authority Scope Config ───

const AUTHORITY_CONFIG: Record<string, { label: string; color: string; bgColor: string; textColor: string }> = {
  'local-canonical': { label: 'Local Canonical', color: '#10b981', bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-600 dark:text-emerald-400' },
  'external-official': { label: 'External Official', color: '#3b82f6', bgColor: 'bg-blue-600/15', textColor: 'text-blue-600 dark:text-blue-400' },
  'mirror-derived': { label: 'Mirror Derived', color: '#f59e0b', bgColor: 'bg-amber-600/15', textColor: 'text-amber-600 dark:text-amber-400' },
  experimental: { label: 'Experimental', color: '#f97316', bgColor: 'bg-orange-600/15', textColor: 'text-orange-600 dark:text-orange-400' },
  'historical-import': { label: 'Historical Import', color: '#6b7280', bgColor: 'bg-gray-600/15', textColor: 'text-gray-600 dark:text-gray-400' },
}

// ─── Severity Config ───

const SEVERITY_CONFIG: Record<string, { bgColor: string; textColor: string; icon: React.ElementType }> = {
  CRITICAL: { bgColor: 'bg-red-600/15', textColor: 'text-red-600 dark:text-red-400', icon: AlertOctagon },
  WARNING: { bgColor: 'bg-amber-600/15', textColor: 'text-amber-600 dark:text-amber-400', icon: AlertTriangle },
  INFO: { bgColor: 'bg-cyan-600/15', textColor: 'text-cyan-600 dark:text-cyan-400', icon: Info },
}

// ─── Promotion Pipeline Stages ───

const PROMOTION_STAGES = [
  { label: 'Request', icon: FileText },
  { label: 'Schema Check', icon: ShieldCheck },
  { label: 'Provenance Verify', icon: GitBranch },
  { label: 'Authority Review', icon: Eye },
  { label: 'Integrity Hash', icon: Hash },
  { label: 'Promoted', icon: CheckCircle2 },
]

// ─── Curator Timeline (deterministic) ───

const CURATOR_TIMELINE = [
  { action: "Skill 'network-diagnostic' transitioned ACTIVE → STALE", reason: '30d inactivity', type: 'transition' },
  { action: "Artifact 'cache-invalidator' archived", reason: '90d inactivity', type: 'archive' },
  { action: "Skill 'log-rotator' promoted to CANONICAL", reason: 'governance gate passed', type: 'promote' },
  { action: "Artifact 'legacy-parser' transitioned ACTIVE → STALE", reason: '30d inactivity', type: 'transition' },
  { action: "Skill 'health-check' re-activated", reason: 'manual override', type: 'reactivate' },
  { action: "Artifact 'old-migration-helper' archived", reason: '90d inactivity', type: 'archive' },
  { action: "Skill 'auth-validator' stale warning issued", reason: '25d inactivity', type: 'warning' },
  { action: "Artifact 'temp-file-cleaner' transitioned ACTIVE → STALE", reason: '30d inactivity', type: 'transition' },
  { action: "Skill 'rate-limiter-v2' promoted to CANONICAL", reason: 'governance gate passed', type: 'promote' },
  { action: "Artifact 'deprecated-api-wrapper' archived", reason: '180d inactivity', type: 'archive' },
]

// ─── Promotion Queue (deterministic) ───

const PROMOTION_QUEUE = [
  { nodeId: 'INF-0142', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Schema Check', requestedBy: 'agent-governor', age: '2h 14m' },
  { nodeId: 'INF-0078', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Authority Review', requestedBy: 'agent-archivist', age: '4h 32m' },
  { nodeId: 'INF-0231', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Pending', requestedBy: 'agent-curator', age: '1h 05m' },
  { nodeId: 'EXT-0045', currentLayer: 'EXTRACTED', targetLayer: 'INFERRED', gateStatus: 'Provenance Verify', requestedBy: 'agent-bridge', age: '3h 18m' },
  { nodeId: 'INF-0119', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Integrity Hash', requestedBy: 'agent-governor', age: '6h 45m' },
  { nodeId: 'EXT-0089', currentLayer: 'EXTRACTED', targetLayer: 'INFERRED', gateStatus: 'Pending', requestedBy: 'agent-curator', age: '0h 42m' },
  { nodeId: 'SRC-0312', currentLayer: 'SOURCE', targetLayer: 'EXTRACTED', gateStatus: 'Schema Check', requestedBy: 'agent-extractor', age: '1h 28m' },
  { nodeId: 'INF-0056', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Authority Review', requestedBy: 'agent-archivist', age: '5h 10m' },
  { nodeId: 'EXT-0123', currentLayer: 'EXTRACTED', targetLayer: 'INFERRED', gateStatus: 'Pending', requestedBy: 'agent-bridge', age: '0h 15m' },
  { nodeId: 'INF-0187', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Promoted', requestedBy: 'agent-governor', age: '8h 02m' },
  { nodeId: 'INF-0199', currentLayer: 'INFERRED', targetLayer: 'CANONICAL', gateStatus: 'Promoted', requestedBy: 'agent-archivist', age: '7h 55m' },
  { nodeId: 'EXT-0067', currentLayer: 'EXTRACTED', targetLayer: 'INFERRED', gateStatus: 'Schema Check', requestedBy: 'agent-extractor', age: '2h 41m' },
]

// ─── Release Readiness Config ───

const RELEASE_ITEMS = [
  { key: 'governanceDocsClean', label: 'Governance docs clean (AGENTS.md, CONTRIBUTING.md)', icon: FileCheck },
  { key: 'coldStartUnified', label: 'Cold-start docs need unification', icon: FileText },
  { key: 'readmeRewritten', label: 'README needs complete rewrite (currently Chimera-focused)', icon: FileText },
  { key: 'pipelineCodeReleasable', label: 'Pipeline code releasable', icon: GitBranch },
  { key: 'schemaMigrationComplete', label: 'Schema node frontmatter migration incomplete', icon: Layers },
  { key: 'integrityGateConsolidated', label: 'Integrity gate consolidated', icon: ShieldCheck },
]

// ─── Main Component ───

export function ArchivistTab() {
  const { data: apiData, loading, error: apiError, refetch } = useApiData<ArchivistAPIResponse>('/api/archivist', 30000)
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; checkedNodes: number; issues: string[] } | null>(null)

  const truthLayers = useMemo(() => apiData?.truthLayers ?? { SOURCE: 0, EXTRACTED: 0, INFERRED: 0, CANONICAL: 0 }, [apiData?.truthLayers])
  const authorityDistribution = useMemo(() => apiData?.authorityDistribution ?? {}, [apiData?.authorityDistribution])
  const promotionQueue = useMemo(() => apiData?.promotionQueue ?? { pending: 0, underReview: 0, promotedToday: 0 }, [apiData?.promotionQueue])
  const curatorStats = useMemo(() => apiData?.curatorStats ?? { active: 0, stale: 0, archived: 0 }, [apiData?.curatorStats])
  const integrityFields = useMemo(() => apiData?.integrityFields ?? {}, [apiData?.integrityFields])
  const contradictions = useMemo(() => apiData?.contradictions ?? [], [apiData?.contradictions])
  const releaseReadiness = useMemo(() => apiData?.releaseReadiness ?? {
    governanceDocsClean: false,
    coldStartUnified: false,
    readmeRewritten: false,
    pipelineCodeReleasable: false,
    schemaMigrationComplete: false,
    integrityGateConsolidated: false,
  }, [apiData?.releaseReadiness])

  const totalAuthorityNodes = useMemo(() => {
    return Object.values(authorityDistribution).reduce((sum, v) => sum + v, 0)
  }, [authorityDistribution])

  const migrationCompleteness = useMemo(() => {
    const fields = Object.values(integrityFields)
    if (fields.length === 0) return 0
    const totalPresent = fields.reduce((sum, f) => sum + f.present, 0)
    const totalPossible = fields.reduce((sum, f) => sum + f.total, 0)
    return totalPossible > 0 ? Math.round((totalPresent / totalPossible) * 100) : 0
  }, [integrityFields])

  const releaseCompleteCount = useMemo(() => {
    return RELEASE_ITEMS.filter((item) => releaseReadiness[item.key as keyof typeof releaseReadiness]).length
  }, [releaseReadiness])

  const releasePercentage = useMemo(() => {
    return Math.round((releaseCompleteCount / RELEASE_ITEMS.length) * 100)
  }, [releaseCompleteCount])

  const handleVerifyIntegrity = async () => {
    setVerifying(true)
    setVerifyResult(null)
    try {
      const res = await globalThis.fetch('/api/archivist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'verify_integrity' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Verification failed')
      }
      const result = await res.json()
      setVerifyResult(result)
      if (result.valid) {
        toast.success('Integrity verification passed', {
          description: `All ${result.checkedNodes} canonical nodes verified — no issues found.`,
        })
      } else {
        toast.error('Integrity verification failed', {
          description: `${result.issues.length} issue(s) found across ${result.checkedNodes} nodes.`,
        })
      }
    } catch (err) {
      toast.error('Verification failed', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    } finally {
      setVerifying(false)
    }
  }

  if (loading && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-teal-600/20 bg-gradient-to-r from-teal-600/5 via-transparent to-teal-600/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-teal-600 dark:text-teal-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading Archivist Truth Layer data...</span>
          </div>
        </div>
      </div>
    )
  }

  if (apiError && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-red-600/20 bg-gradient-to-r from-red-600/5 via-transparent to-red-600/5 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <div>
              <span className="text-sm font-medium text-red-600 dark:text-red-400">Failed to load Archivist data</span>
              <p className="text-xs text-muted-foreground mt-1">{apiError}</p>
            </div>
            <Button variant="outline" size="sm" className="ml-auto gap-1.5" onClick={() => refetch()}>
              <Loader2 className="h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 grid-pattern animate-fade-in">
      {/* ── Header Banner ── */}
      <div className="relative overflow-hidden rounded-xl border border-teal-600/20 bg-gradient-to-r from-teal-600/5 via-transparent to-cyan-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 shadow-md">
              <BookMarked className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">Archivist Truth Layer</h2>
              <p className="text-xs text-muted-foreground">DERDDRE-01 · 4-layer truth engine · Mythos Mapping authority</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DataSourceBadge source="archivist" />
            <Badge className="border-0 text-[10px] gap-1 bg-teal-600/15 text-teal-600 dark:text-teal-400">
              <Layers className="h-2.5 w-2.5" />
              4 LAYERS
            </Badge>
          </div>
        </div>
      </div>

      {/* ── A. Truth Layer Pyramid ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Layers className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            Truth Layer Pyramid
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0">
          <div className="flex flex-col items-center gap-2">
            {[...TRUTH_LAYER_ORDER].reverse().map((layer, idx) => {
              const config = TRUTH_LAYER_CONFIG[layer]
              const count = truthLayers[layer] ?? 0
              const widthPct = 40 + (idx * 20)
              const isVerified = config.badge === 'verified'
              return (
                <div key={layer} className="flex flex-col items-center w-full">
                  <div
                    className={`relative rounded-lg border ${config.borderColor} ${config.bgColor} p-3 transition-all hover:shadow-md`}
                    style={{ width: `${widthPct}%`, minWidth: '200px' }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-bold ${config.textColor}`}>{config.label}</span>
                        <Badge className={`text-[8px] border-0 gap-0.5 ${
                          isVerified
                            ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                            : 'bg-amber-600/15 text-amber-600 dark:text-amber-400'
                        }`}>
                          {isVerified ? <CheckCircle2 className="h-2 w-2" /> : <Clock className="h-2 w-2" />}
                          {config.badge}
                        </Badge>
                      </div>
                      <span className={`text-lg font-bold tabular-nums ${config.textColor}`}>{count.toLocaleString()}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1">{config.description}</p>
                  </div>
                  {idx < TRUTH_LAYER_ORDER.length - 1 && (
                    <ArrowUp className="h-3.5 w-3.5 text-teal-600/30 my-0.5" />
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* ── B. Authority Scope Distribution ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            Authority Scope Distribution
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0">
          <div className="space-y-3">
            {Object.entries(authorityDistribution).map(([scope, count]) => {
              const config = AUTHORITY_CONFIG[scope] ?? { label: scope, color: '#6b7280', bgColor: 'bg-gray-600/15', textColor: 'text-gray-600 dark:text-gray-400' }
              const pct = totalAuthorityNodes > 0 ? Math.round((count / totalAuthorityNodes) * 100) : 0
              return (
                <div key={scope} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: config.color }} />
                      <span className="text-xs font-medium">{config.label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold tabular-nums ${config.textColor}`}>{count}</span>
                      <span className="text-[10px] text-muted-foreground tabular-nums">({pct}%)</span>
                    </div>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted/50 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: config.color }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-3 pt-3 border-t border-border/30 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>Total nodes across all scopes</span>
            <span className="font-bold text-teal-600 dark:text-teal-400">{totalAuthorityNodes.toLocaleString()}</span>
          </div>
        </CardContent>
      </Card>

      {/* ── C. Promotion Gate Tracker ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <ArrowUp className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            Promotion Gate Tracker
            <Badge className="bg-teal-600/15 text-teal-600 dark:text-teal-400 border-0 text-[9px] gap-1">
              <Clock className="h-2.5 w-2.5" />
              {promotionQueue.pending} pending
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-4">
          {/* Pipeline visualization */}
          <div className="flex items-center justify-between gap-1 p-3 rounded-lg bg-muted/30 border border-border/30 overflow-x-auto custom-scrollbar">
            {PROMOTION_STAGES.map((stage, idx) => {
              const StageIcon = stage.icon
              return (
                <div key={stage.label} className="flex items-center gap-1 shrink-0">
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-600/10 border border-teal-600/20">
                      <StageIcon className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
                    </div>
                    <span className="text-[8px] text-muted-foreground whitespace-nowrap">{stage.label}</span>
                  </div>
                  {idx < PROMOTION_STAGES.length - 1 && (
                    <ArrowRight className="h-3 w-3 text-teal-600/30 shrink-0 mx-0.5" />
                  )}
                </div>
              )
            })}
          </div>

          {/* Queue stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-amber-600/20 bg-amber-600/5 p-3 text-center">
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400 tabular-nums">{promotionQueue.pending}</p>
              <p className="text-[10px] text-muted-foreground">Pending</p>
            </div>
            <div className="rounded-lg border border-blue-600/20 bg-blue-600/5 p-3 text-center">
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400 tabular-nums">{promotionQueue.underReview}</p>
              <p className="text-[10px] text-muted-foreground">Under Review</p>
            </div>
            <div className="rounded-lg border border-emerald-600/20 bg-emerald-600/5 p-3 text-center">
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{promotionQueue.promotedToday}</p>
              <p className="text-[10px] text-muted-foreground">Promoted Today</p>
            </div>
          </div>

          {/* Queue table */}
          <div className="max-h-64 overflow-y-auto custom-scrollbar rounded-lg border border-border/30">
            <table className="w-full text-xs">
              <thead className="bg-muted/30 sticky top-0">
                <tr>
                  <th className="text-left p-2 text-muted-foreground font-medium">Node ID</th>
                  <th className="text-left p-2 text-muted-foreground font-medium">Current</th>
                  <th className="text-left p-2 text-muted-foreground font-medium">Target</th>
                  <th className="text-left p-2 text-muted-foreground font-medium">Gate Status</th>
                  <th className="text-left p-2 text-muted-foreground font-medium">Requested By</th>
                  <th className="text-left p-2 text-muted-foreground font-medium">Age</th>
                </tr>
              </thead>
              <tbody>
                {PROMOTION_QUEUE.map((item) => (
                  <tr key={item.nodeId} className="border-t border-border/20 hover:bg-muted/20 transition-colors">
                    <td className="p-2 font-mono text-teal-600 dark:text-teal-400">{item.nodeId}</td>
                    <td className="p-2">
                      <Badge className={`text-[8px] border-0 ${TRUTH_LAYER_CONFIG[item.currentLayer]?.bgColor ?? ''} ${TRUTH_LAYER_CONFIG[item.currentLayer]?.textColor ?? ''}`}>
                        {item.currentLayer}
                      </Badge>
                    </td>
                    <td className="p-2">
                      <Badge className={`text-[8px] border-0 ${TRUTH_LAYER_CONFIG[item.targetLayer]?.bgColor ?? ''} ${TRUTH_LAYER_CONFIG[item.targetLayer]?.textColor ?? ''}`}>
                        {item.targetLayer}
                      </Badge>
                    </td>
                    <td className="p-2">
                      <Badge className={`text-[8px] border-0 ${
                        item.gateStatus === 'Promoted'
                          ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                          : item.gateStatus === 'Pending'
                            ? 'bg-amber-600/15 text-amber-600 dark:text-amber-400'
                            : 'bg-blue-600/15 text-blue-600 dark:text-blue-400'
                      }`}>
                        {item.gateStatus}
                      </Badge>
                    </td>
                    <td className="p-2 text-muted-foreground">{item.requestedBy}</td>
                    <td className="p-2 text-muted-foreground font-mono">{item.age}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── D. Curator Lifecycle Visualization ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Archive className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            Curator Lifecycle
            <DataSourceBadge source="api" />
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-4">
          {/* Lifecycle states */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-emerald-600/20 bg-emerald-600/5 p-3 text-center">
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{curatorStats.active.toLocaleString()}</p>
              <div className="flex items-center justify-center gap-1 mt-1">
                <Zap className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[10px] text-muted-foreground">Active</span>
              </div>
            </div>
            <div className="rounded-lg border border-amber-600/20 bg-amber-600/5 p-3 text-center">
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 tabular-nums">{curatorStats.stale}</p>
              <div className="flex items-center justify-center gap-1 mt-1">
                <Timer className="h-3 w-3 text-amber-600 dark:text-amber-400" />
                <span className="text-[10px] text-muted-foreground">Stale</span>
              </div>
            </div>
            <div className="rounded-lg border border-gray-600/20 bg-gray-600/5 p-3 text-center">
              <p className="text-2xl font-bold text-gray-600 dark:text-gray-400 tabular-nums">{curatorStats.archived}</p>
              <div className="flex items-center justify-center gap-1 mt-1">
                <Archive className="h-3 w-3 text-gray-600 dark:text-gray-400" />
                <span className="text-[10px] text-muted-foreground">Archived</span>
              </div>
            </div>
          </div>

          {/* Lifecycle pipeline */}
          <div className="flex items-center justify-center gap-2 text-[10px]">
            <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 gap-1">
              <Zap className="h-2.5 w-2.5" />
              ACTIVE
            </Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge className="bg-amber-600/15 text-amber-600 dark:text-amber-400 border-0 gap-1">
              <Timer className="h-2.5 w-2.5" />
              STALE
            </Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge className="bg-gray-600/15 text-gray-600 dark:text-gray-400 border-0 gap-1">
              <Archive className="h-2.5 w-2.5" />
              ARCHIVED
            </Badge>
          </div>

          {/* Timeline */}
          <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-2">
            {CURATOR_TIMELINE.map((item, idx) => {
              const typeConfig: Record<string, { color: string; bgColor: string; icon: React.ElementType }> = {
                transition: { color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-600/10', icon: Timer },
                archive: { color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-600/10', icon: Archive },
                promote: { color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-600/10', icon: ArrowUp },
                reactivate: { color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-600/10', icon: Zap },
                warning: { color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-600/10', icon: AlertTriangle },
              }
              const cfg = typeConfig[item.type] ?? typeConfig.transition
              const TypeIcon = cfg.icon
              return (
                <div key={idx} className={`flex items-start gap-2 rounded-md border border-border/30 p-2 hover:bg-muted/20 transition-colors`}>
                  <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded ${cfg.bgColor}`}>
                    <TypeIcon className={`h-3 w-3 ${cfg.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] leading-tight">{item.action}</p>
                    <p className="text-[9px] text-muted-foreground mt-0.5">{item.reason}</p>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex items-center gap-2 text-[9px] text-muted-foreground bg-muted/20 rounded-md p-2">
            <Shield className="h-3 w-3 text-teal-600/50" />
            <span>Curator cannot modify kernel-bundled or admin-signed artifacts</span>
          </div>
        </CardContent>
      </Card>

      {/* ── E. Integrity Fields Status ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-teal-600 dark:text-teal-400" />
              Integrity Fields Status
              <DataSourceBadge source="api" />
            </CardTitle>
            {migrationCompleteness < 100 && (
              <Badge className="bg-amber-600/15 text-amber-600 dark:text-amber-400 border-0 text-[9px] gap-1">
                <AlertTriangle className="h-2.5 w-2.5" />
                Migration Required
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-3">
          {Object.entries(integrityFields).map(([field, data]) => {
            const isComplete = data.present === data.total
            const missing = data.total - data.present
            return (
              <div key={field} className="flex items-center gap-3">
                <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded ${
                  isComplete ? 'bg-emerald-600/15' : 'bg-amber-600/15'
                }`}>
                  {isComplete
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    : <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <code className="text-xs font-mono">{field}</code>
                    <span className={`text-[10px] tabular-nums ${
                      isComplete
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-amber-600 dark:text-amber-400'
                    }`}>
                      {data.present}/{data.total} nodes
                      {!isComplete && ` (${missing} missing)`}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isComplete ? 'bg-emerald-600' : 'bg-amber-600'
                      }`}
                      style={{ width: `${data.total > 0 ? (data.present / data.total) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            )
          })}

          {/* Overall migration progress */}
          <div className="pt-3 border-t border-border/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">Overall Migration Completeness</span>
              <span className="text-xs font-bold text-teal-600 dark:text-teal-400 tabular-nums">{migrationCompleteness}%</span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-muted/50 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  migrationCompleteness === 100 ? 'bg-emerald-600' : migrationCompleteness >= 75 ? 'bg-teal-600' : 'bg-amber-600'
                }`}
                style={{ width: `${migrationCompleteness}%` }}
              />
            </div>
          </div>

          {/* Verify button */}
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs border-teal-600/30 text-teal-600 dark:text-teal-400 hover:bg-teal-600/10"
              onClick={handleVerifyIntegrity}
              disabled={verifying}
            >
              {verifying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              {verifying ? 'Verifying...' : 'Verify Integrity'}
            </Button>
            {verifyResult && (
              <div className={`flex items-center gap-1.5 text-[10px] ${
                verifyResult.valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
              }`}>
                {verifyResult.valid ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                {verifyResult.valid
                  ? `${verifyResult.checkedNodes} nodes verified`
                  : `${verifyResult.issues.length} issues found`
                }
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ── F. Contradiction Detection ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            Contradiction Detection
            <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] gap-1">
              <AlertOctagon className="h-2.5 w-2.5" />
              {contradictions.length} detected
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-3">
          {/* Summary */}
          <div className="flex items-center gap-4 text-[10px] text-muted-foreground bg-muted/20 rounded-md p-2">
            <Activity className="h-3.5 w-3.5 text-teal-600/50" />
            <span>
              {contradictions.length} contradictions detected —{' '}
              {contradictions.filter((c) => c.severity === 'CRITICAL').length} critical,{' '}
              {contradictions.filter((c) => c.severity === 'WARNING').length} warning,{' '}
              {contradictions.filter((c) => c.severity === 'INFO').length} info
            </span>
          </div>

          {/* Contradiction items */}
          <div className="space-y-2">
            {contradictions.map((contradiction) => {
              const severityCfg = SEVERITY_CONFIG[contradiction.severity] ?? SEVERITY_CONFIG.INFO
              const SeverityIcon = severityCfg.icon
              return (
                <div key={contradiction.id} className="rounded-lg border border-border/30 p-3 hover:bg-muted/20 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded ${severityCfg.bgColor}`}>
                        <SeverityIcon className={`h-3 w-3 ${severityCfg.textColor}`} />
                      </div>
                      <div>
                        <p className="text-[11px] leading-tight">
                          Node <code className="font-mono text-teal-600 dark:text-teal-400">{contradiction.nodeA}</code> conflicts with{' '}
                          <code className="font-mono text-teal-600 dark:text-teal-400">{contradiction.nodeB}</code> on{' '}
                          <code className="font-mono">{contradiction.field}</code>
                        </p>
                        <p className="text-[9px] text-muted-foreground mt-0.5">
                          {contradiction.layerA} vs {contradiction.layerB}
                        </p>
                      </div>
                    </div>
                    <Badge className={`text-[8px] border-0 shrink-0 ${severityCfg.bgColor} ${severityCfg.textColor}`}>
                      {contradiction.severity}
                    </Badge>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* ── G. Release Hygiene Panel ── */}
      <Card className="relative overflow-hidden border-teal-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-teal-600 dark:text-teal-400" />
              Release Hygiene Panel
              <DataSourceBadge source="api" />
            </CardTitle>
            <Badge className={`text-[10px] border-0 gap-1 ${
              releasePercentage >= 80
                ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                : releasePercentage >= 50
                  ? 'bg-amber-600/15 text-amber-600 dark:text-amber-400'
                  : 'bg-red-600/15 text-red-600 dark:text-red-400'
            }`}>
              {releasePercentage}% Ready
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-3">
          {RELEASE_ITEMS.map((item) => {
            const isComplete = releaseReadiness[item.key as keyof typeof releaseReadiness]
            const ItemIcon = item.icon
            return (
              <div key={item.key} className="flex items-center gap-3">
                <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded ${
                  isComplete ? 'bg-emerald-600/15' : 'bg-red-600/15'
                }`}>
                  {isComplete
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    : <XCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                  }
                </div>
                <ItemIcon className={`h-3.5 w-3.5 shrink-0 ${isComplete ? 'text-emerald-600/50 dark:text-emerald-400/50' : 'text-red-600/50 dark:text-red-400/50'}`} />
                <span className={`text-xs ${isComplete ? 'text-foreground' : 'text-muted-foreground'}`}>
                  {item.label}
                </span>
              </div>
            )
          })}

          {/* Overall progress */}
          <div className="pt-3 border-t border-border/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">Overall Readiness</span>
              <span className="text-xs font-bold text-teal-600 dark:text-teal-400 tabular-nums">
                {releaseCompleteCount}/{RELEASE_ITEMS.length} complete ({releasePercentage}%)
              </span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-muted/50 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  releasePercentage >= 80 ? 'bg-emerald-600' : releasePercentage >= 50 ? 'bg-amber-600' : 'bg-red-600'
                }`}
                style={{ width: `${releasePercentage}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
