'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Link2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
  Activity,
  Hash,
  Clock,
  Copy,
  Database,
  Users,
  FileWarning,
  Fingerprint,
  Shield,
  KeyRound,
  FileCheck,
  Sparkles,
} from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { toast } from 'sonner'

// ─── API Response Types ───

interface ChainEntryAPI {
  entryId: string
  entryIndex: number
  eventType: 'gate_decision' | 'agent_action' | 'trust_update' | 'violation' | 'config_change'
  agentId: string
  actionHash: string
  previousHash: string
  currentHash: string
  timestamp: string
  metadata: Record<string, unknown>
  // Mythos Mapping authority fields
  authorityScope: 'local-canonical' | 'external-official' | 'mirror-derived' | 'experimental' | 'historical-import'
  originSha256: string
  policyHash: string
  sandboxProfile: string
  approvalId: string | null
  slsaAttestation: boolean
  ed25519Signature: string | null
}

interface AttestationStats {
  slsaAttestedCount: number
  ed25519SignedCount: number
  totalEntries: number
}

interface VapChainAPIResponse {
  chainLength: number
  chainIntegrity: boolean
  genesisHash: string
  latestHash: string
  recentEntries: ChainEntryAPI[]
  eventBreakdown: Record<string, number>
  authorityScopeDistribution: Record<string, number>
  attestationStats: AttestationStats
  auditSummary: {
    totalEntries: number
    integrityVerified: boolean
    violationCount: number
    uniqueAgents: number
  }
}

// ─── Verify Integrity Response ───

interface VerifyResponse {
  valid: boolean
  chainLength: number
  issues: string[]
  verifiedAt?: string
  message?: string
}

// ─── Attest Entry Response ───

interface AttestResponse {
  attestation: {
    entryId: string
    entryIndex: number
    eventType: string
    agentId: string
    attestationHash: string
    ed25519Signature: string
    attestationTimestamp: string
    authorityScope: string
    originSha256: string
    policyHash: string
    sandboxProfile: string
    approvalId: string | null
    slsaAttestation: boolean
    chainIntegrity: boolean
  }
}

// ─── Event Type Config ───

const EVENT_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  gate_decision: { label: 'Gate Decision', color: '#fb923c', bgColor: 'bg-orange-600/15 text-orange-600 dark:text-orange-400' },
  agent_action: { label: 'Agent Action', color: '#34d399', bgColor: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' },
  trust_update: { label: 'Trust Update', color: '#a78bfa', bgColor: 'bg-purple-600/15 text-purple-600 dark:text-purple-400' },
  violation: { label: 'Violation', color: '#f87171', bgColor: 'bg-red-600/15 text-red-600 dark:text-red-400' },
  config_change: { label: 'Config Change', color: '#94a3b8', bgColor: 'bg-slate-600/15 text-slate-600 dark:text-slate-400' },
}

// ─── Authority Scope Config ───

const AUTHORITY_SCOPE_CONFIG: Record<string, { label: string; color: string; bgColor: string; barColor: string }> = {
  'local-canonical': { label: 'Local Canonical', color: '#a855f7', bgColor: 'bg-purple-600/15 text-purple-600 dark:text-purple-400', barColor: 'bg-purple-500' },
  'external-official': { label: 'External Official', color: '#10b981', bgColor: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400', barColor: 'bg-emerald-500' },
  'mirror-derived': { label: 'Mirror Derived', color: '#f59e0b', bgColor: 'bg-amber-600/15 text-amber-600 dark:text-amber-400', barColor: 'bg-amber-500' },
  'experimental': { label: 'Experimental', color: '#f97316', bgColor: 'bg-orange-600/15 text-orange-600 dark:text-orange-400', barColor: 'bg-orange-500' },
  'historical-import': { label: 'Historical Import', color: '#6b7280', bgColor: 'bg-gray-600/15 text-gray-600 dark:text-gray-400', barColor: 'bg-gray-500' },
}

function getEventBadge(eventType: string) {
  const config = EVENT_CONFIG[eventType] ?? { label: eventType, color: '#a3a3a3', bgColor: 'bg-muted text-muted-foreground' }
  return <Badge className={`text-[8px] border-0 ${config.bgColor}`}>{config.label}</Badge>
}

function getAuthorityScopeBadge(scope: string) {
  const config = AUTHORITY_SCOPE_CONFIG[scope] ?? { label: scope, color: '#a3a3a3', bgColor: 'bg-muted text-muted-foreground', barColor: 'bg-gray-500' }
  return <Badge className={`text-[8px] border-0 ${config.bgColor}`}>{config.label}</Badge>
}

function getSandboxProfileBadge(profile: string) {
  const configs: Record<string, { bgColor: string; icon: string }> = {
    'openshell-reviewground': { bgColor: 'bg-cyan-600/15 text-cyan-600 dark:text-cyan-400', icon: '🛡️' },
    'kaiju-governor': { bgColor: 'bg-orange-600/15 text-orange-600 dark:text-orange-400', icon: '🐲' },
    'native-kernel': { bgColor: 'bg-slate-600/15 text-slate-600 dark:text-slate-400', icon: '⚙️' },
  }
  const config = configs[profile] ?? { bgColor: 'bg-muted text-muted-foreground', icon: '📦' }
  return <Badge className={`text-[8px] border-0 ${config.bgColor}`}>{config.icon} {profile}</Badge>
}

// ─── Expandable Chain Entry ───

function ChainEntryRow({ entry, onAttest }: { entry: ChainEntryAPI; onAttest: (entryId: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const [attesting, setAttesting] = useState(false)
  const [attestResult, setAttestResult] = useState<AttestResponse['attestation'] | null>(null)

  const handleAttest = async () => {
    setAttesting(true)
    try {
      const res = await globalThis.fetch('/api/vap-chain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'attest_entry', entryId: entry.entryId }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Attestation failed')
      }
      const result: AttestResponse = await res.json()
      setAttestResult(result.attestation)
      toast.success('Entry attested', {
        description: `${entry.entryId.slice(-6).toUpperCase()} signed with Ed25519`,
      })
      onAttest(entry.entryId)
    } catch (err) {
      toast.error('Attestation failed', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    } finally {
      setAttesting(false)
    }
  }

  return (
    <div className="rounded-md border border-border/50 hover:border-purple-600/30 transition-colors">
      <button
        className="w-full px-3 py-2.5 flex items-center gap-2 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Entry ID */}
        <span className="font-mono text-[10px] text-muted-foreground w-16 shrink-0 truncate" title={entry.entryId}>
          {entry.entryId.slice(-6).toUpperCase().padStart(6, '0')}
        </span>

        {/* Event Type Badge */}
        <div className="shrink-0">{getEventBadge(entry.eventType)}</div>

        {/* Agent ID */}
        <span className="text-[10px] text-muted-foreground shrink-0 max-w-[80px] truncate">{entry.agentId}</span>

        {/* Hash linkage */}
        <div className="flex items-center gap-1 text-[9px] font-mono text-muted-foreground/60 shrink-0 overflow-hidden">
          <span className="truncate max-w-[60px]" title={entry.previousHash}>{entry.previousHash.slice(0, 8)}...</span>
          <ArrowRight className="h-3 w-3 text-purple-600/50 shrink-0" />
          <span className="truncate max-w-[60px] text-purple-600 dark:text-purple-400 font-medium" title={entry.currentHash}>{entry.currentHash.slice(0, 8)}...</span>
        </div>

        {/* Authority scope indicator dot */}
        <span
          className="h-2 w-2 rounded-full shrink-0"
          style={{ backgroundColor: AUTHORITY_SCOPE_CONFIG[entry.authorityScope]?.color ?? '#a3a3a3' }}
          title={entry.authorityScope}
        />

        {/* SLSA badge */}
        {entry.slsaAttestation && (
          <FileCheck className="h-3 w-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
        )}

        {/* Timestamp */}
        <span className="ml-auto text-[9px] font-mono text-muted-foreground shrink-0">
          {new Date(entry.timestamp).toLocaleTimeString('en-US', { hour12: false })}
        </span>

        {/* Expand toggle */}
        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground shrink-0" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-border/30 space-y-2">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="rounded bg-accent/30 p-2">
              <p className="text-muted-foreground uppercase tracking-wider text-[8px]">Full Hash</p>
              <p className="font-mono mt-0.5 break-all">{entry.currentHash}</p>
            </div>
            <div className="rounded bg-accent/30 p-2">
              <p className="text-muted-foreground uppercase tracking-wider text-[8px]">Previous Hash</p>
              <p className="font-mono mt-0.5 break-all">{entry.previousHash}</p>
            </div>
          </div>

          {/* Authority Fields Section */}
          <div className="rounded bg-purple-600/5 border border-purple-600/10 p-2">
            <p className="text-purple-600 dark:text-purple-400 uppercase tracking-wider text-[8px] font-semibold mb-2 flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Mythos Authority Fields
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div>
                <span className="text-muted-foreground">Authority Scope:</span>{' '}
                {getAuthorityScopeBadge(entry.authorityScope)}
              </div>
              <div>
                <span className="text-muted-foreground">Sandbox Profile:</span>{' '}
                {getSandboxProfileBadge(entry.sandboxProfile)}
              </div>
              <div>
                <span className="text-muted-foreground">Origin SHA256:</span>{' '}
                <span className="font-mono text-[9px]" title={entry.originSha256}>{entry.originSha256.slice(0, 16)}...</span>
              </div>
              <div>
                <span className="text-muted-foreground">Policy Hash:</span>{' '}
                <span className="font-mono text-[9px]" title={entry.policyHash}>{entry.policyHash.slice(0, 16)}...</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">SLSA Attestation:</span>{' '}
                {entry.slsaAttestation ? (
                  <span className="flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
                    <FileCheck className="h-3 w-3" /> Yes
                  </span>
                ) : (
                  <span className="flex items-center gap-0.5 text-muted-foreground">
                    <XCircle className="h-3 w-3" /> No
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Ed25519:</span>{' '}
                {entry.ed25519Signature ? (
                  <span className="flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
                    <Fingerprint className="h-3 w-3" /> Signed
                  </span>
                ) : (
                  <span className="flex items-center gap-0.5 text-muted-foreground">
                    <KeyRound className="h-3 w-3" /> Unsigned
                  </span>
                )}
              </div>
              {entry.approvalId && (
                <div className="col-span-2">
                  <span className="text-muted-foreground">Approval ID:</span>{' '}
                  <Badge className="bg-orange-600/15 text-orange-600 dark:text-orange-400 border-0 text-[8px]">{entry.approvalId}</Badge>
                </div>
              )}
            </div>
            {entry.ed25519Signature && (
              <div className="mt-2">
                <span className="text-muted-foreground text-[9px]">Signature:</span>
                <pre className="mt-0.5 text-[8px] font-mono bg-background/50 rounded p-1.5 break-all whitespace-pre-wrap">
                  {entry.ed25519Signature}
                </pre>
              </div>
            )}
          </div>

          {/* Metadata Section */}
          <div className="rounded bg-accent/30 p-2">
            <p className="text-muted-foreground uppercase tracking-wider text-[8px] mb-1">Metadata</p>
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div>
                <span className="text-muted-foreground">Index:</span>{' '}
                <span className="font-mono">{entry.entryIndex}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Action:</span>{' '}
                <span className="font-mono">{entry.actionHash}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Agent:</span>{' '}
                <span>{entry.agentId}</span>
              </div>
            </div>
            {Object.keys(entry.metadata).length > 0 && (
              <div className="mt-2">
                <span className="text-muted-foreground">Value:</span>
                <pre className="mt-0.5 text-[9px] font-mono bg-background/50 rounded p-1.5 max-h-24 overflow-auto whitespace-pre-wrap break-all">
                  {JSON.stringify(entry.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Attestation Result */}
          {attestResult && (
            <div className="rounded border border-emerald-600/20 bg-emerald-600/5 p-2">
              <p className="text-emerald-600 dark:text-emerald-400 uppercase tracking-wider text-[8px] font-semibold mb-1 flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                Attestation Result
              </p>
              <div className="text-[9px] space-y-1">
                <div><span className="text-muted-foreground">Attestation Hash:</span> <span className="font-mono">{attestResult.attestationHash.slice(0, 24)}...</span></div>
                <div><span className="text-muted-foreground">Signed At:</span> <span className="font-mono">{new Date(attestResult.attestationTimestamp).toLocaleTimeString('en-US', { hour12: false })}</span></div>
                <div><span className="text-muted-foreground">Chain Integrity:</span> <span className={attestResult.chainIntegrity ? 'text-emerald-600' : 'text-red-600'}>{attestResult.chainIntegrity ? '✓ Valid' : '✗ Invalid'}</span></div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[9px] gap-1"
              onClick={handleAttest}
              disabled={attesting}
            >
              {attesting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Fingerprint className="h-3 w-3" />}
              {attesting ? 'Attesting...' : 'Attest Entry'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[9px] gap-1"
              onClick={() => {
                navigator.clipboard.writeText(entry.currentHash)
                toast.success('Hash copied to clipboard')
              }}
            >
              <Copy className="h-3 w-3" />
              Copy Hash
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Component ───

export function VapChainTab() {
  const { data: apiData, loading, error: apiError, refetch } = useApiData<VapChainAPIResponse>('/api/vap-chain', 15000)

  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<VerifyResponse | null>(null)

  const recentEntries = useMemo(() => apiData?.recentEntries ?? [], [apiData?.recentEntries])
  const eventBreakdown = useMemo(() => apiData?.eventBreakdown ?? {}, [apiData?.eventBreakdown])
  const authorityScopeDistribution = useMemo(() => apiData?.authorityScopeDistribution ?? {}, [apiData?.authorityScopeDistribution])
  const attestationStats = useMemo(() => apiData?.attestationStats ?? { slsaAttestedCount: 0, ed25519SignedCount: 0, totalEntries: 0 }, [apiData?.attestationStats])
  const auditSummary = useMemo(() => apiData?.auditSummary ?? { totalEntries: 0, integrityVerified: true, violationCount: 0, uniqueAgents: 0 }, [apiData?.auditSummary])
  const chainIntegrity = useMemo(() => apiData?.chainIntegrity ?? true, [apiData?.chainIntegrity])
  const genesisHash = useMemo(() => apiData?.genesisHash ?? '0'.repeat(12) + '...', [apiData?.genesisHash])
  const latestHash = useMemo(() => apiData?.latestHash ?? '0'.repeat(12) + '...', [apiData?.latestHash])
  const chainLength = useMemo(() => apiData?.chainLength ?? 0, [apiData?.chainLength])

  // Pie chart data for event breakdown
  const pieData = useMemo(() => {
    return Object.entries(eventBreakdown).map(([name, value]) => ({
      name,
      value,
      color: EVENT_CONFIG[name]?.color ?? '#a3a3a3',
    }))
  }, [eventBreakdown])

  // Authority scope distribution data for bar chart
  const scopeBarData = useMemo(() => {
    const total = Object.values(authorityScopeDistribution).reduce((sum, v) => sum + v, 0)
    const scopeOrder = ['local-canonical', 'external-official', 'mirror-derived', 'experimental', 'historical-import'] as const
    return scopeOrder
      .filter((scope) => (authorityScopeDistribution[scope] ?? 0) > 0)
      .map((scope) => ({
        scope,
        label: AUTHORITY_SCOPE_CONFIG[scope].label,
        count: authorityScopeDistribution[scope] ?? 0,
        percentage: total > 0 ? ((authorityScopeDistribution[scope] ?? 0) / total) * 100 : 0,
        config: AUTHORITY_SCOPE_CONFIG[scope],
      }))
  }, [authorityScopeDistribution])

  // Agent identity breakdown (derived from entries)
  const agentIdentityBreakdown = useMemo(() => {
    const entries = recentEntries
    const signedAgents = new Set(entries.filter((e) => e.ed25519Signature).map((e) => e.agentId))
    const slsaAgents = new Set(entries.filter((e) => e.slsaAttestation).map((e) => e.agentId))
    const allAgents = new Set(entries.map((e) => e.agentId))
    const pendingAgents = new Set([...slsaAgents].filter((a) => !signedAgents.has(a)))
    const unknownAgents = new Set([...allAgents].filter((a) => !signedAgents.has(a) && !slsaAgents.has(a)))
    return {
      ed25519Verified: signedAgents.size,
      pendingVerification: pendingAgents.size,
      unknownIdentity: unknownAgents.size,
      totalAgents: allAgents.size,
    }
  }, [recentEntries])

  const handleVerify = async () => {
    setVerifying(true)
    setVerifyResult(null)
    try {
      const res = await globalThis.fetch('/api/vap-chain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'verify_integrity' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Verification failed')
      }
      const result = await res.json()
      const verifyResp: VerifyResponse = {
        valid: result.verification.valid,
        chainLength: result.verification.totalEntries,
        issues: result.verification.issues ?? [],
        verifiedAt: result.verification.verifiedAt,
      }
      setVerifyResult(verifyResp)
      if (verifyResp.valid) {
        toast.success('Chain integrity verified', {
          description: `All ${verifyResp.chainLength} entries verified — no tampering detected.`,
        })
      } else {
        toast.error('Chain integrity check failed', {
          description: `${verifyResp.issues.length} issue(s) found across ${verifyResp.chainLength} entries.`,
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

  const handleAttest = (_entryId: string) => {
    // Refresh data after attestation to reflect any changes
    refetch()
  }

  if (loading && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-purple-600/20 bg-gradient-to-r from-purple-600/5 via-transparent to-purple-600/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-purple-600 dark:text-purple-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading VAP Audit Chain data...</span>
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
              <span className="text-sm font-medium text-red-600 dark:text-red-400">Failed to load VAP Chain data</span>
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
      {/* VAP Chain Header Banner */}
      <div className="relative overflow-hidden rounded-xl border border-purple-600/20 bg-gradient-to-r from-purple-600/5 via-transparent to-violet-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 shadow-md">
              <Link2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">VAP Audit Chain</h2>
              <p className="text-xs text-muted-foreground">Cryptographic audit trail · {chainLength} entries · SHA-256 linked</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DataSourceBadge source="api" />
            <Badge className={`border-0 text-[10px] gap-1 ${
              chainIntegrity
                ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                : 'bg-red-600/15 text-red-600 dark:text-red-400'
            }`}>
              {chainIntegrity ? <CheckCircle2 className="h-2.5 w-2.5" /> : <XCircle className="h-2.5 w-2.5" />}
              {chainIntegrity ? 'VERIFIED' : 'COMPROMISED'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Chain Status Banner */}
      <Card className="relative overflow-hidden border-purple-600/20">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
        <CardContent className="relative p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
                chainIntegrity
                  ? 'bg-emerald-600/15 shadow-lg shadow-emerald-600/10'
                  : 'bg-red-600/15 shadow-lg shadow-red-600/10'
              }`}>
                {chainIntegrity
                  ? <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                  : <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                }
              </div>
              <div>
                <p className="text-sm font-semibold">
                  Chain Integrity: {chainIntegrity ? 'Verified' : 'Compromised'}
                </p>
                <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1"><Hash className="h-3 w-3" />Length: {chainLength}</span>
                  <span className="flex items-center gap-1 font-mono">Genesis: {genesisHash.slice(0, 10)}...</span>
                  <span className="flex items-center gap-1 font-mono">Latest: {latestHash.slice(0, 10)}...</span>
                </div>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs border-purple-600/30 text-purple-600 dark:text-purple-400 hover:bg-purple-600/10"
              onClick={handleVerify}
              disabled={verifying}
            >
              {verifying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              {verifying ? 'Verifying...' : 'Verify Integrity'}
            </Button>
          </div>
          {verifyResult && (
            <div className={`mt-3 rounded-lg border p-3 ${
              verifyResult.valid
                ? 'border-emerald-600/20 bg-emerald-600/5'
                : 'border-red-600/20 bg-red-600/5'
            }`}>
              <div className="flex items-center gap-2 text-xs">
                {verifyResult.valid
                  ? <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  : <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                }
                <span className="font-medium">
                  {verifyResult.valid
                    ? `All ${verifyResult.chainLength} entries verified — no tampering detected`
                    : `${verifyResult.issues.length} issue(s) found`
                  }
                </span>
                {verifyResult.verifiedAt && (
                  <span className="ml-auto text-[9px] text-muted-foreground font-mono">
                    Verified: {new Date(verifyResult.verifiedAt).toLocaleTimeString('en-US', { hour12: false })}
                  </span>
                )}
              </div>
              {verifyResult.issues.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {verifyResult.issues.map((issue, i) => (
                    <li key={i} className="text-[10px] text-red-600 dark:text-red-400 flex items-start gap-1">
                      <FileWarning className="h-3 w-3 mt-0.5 shrink-0" />
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Audit Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-purple-600/20 hover-lift">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Entries</p>
                <p className="mt-1 text-3xl font-bold text-purple-600 dark:text-purple-400 tabular-nums">{auditSummary.totalEntries.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground">in audit chain</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15">
                <Database className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className={`${chainIntegrity ? 'border-emerald-600/20' : 'border-red-600/20'} hover-lift`}>
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Integrity Status</p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${chainIntegrity ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {chainIntegrity ? 'OK' : 'FAIL'}
                </p>
                <p className="text-[10px] text-muted-foreground">{chainIntegrity ? 'SHA-256 verified' : 'Chain compromised'}</p>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${chainIntegrity ? 'bg-emerald-600/15' : 'bg-red-600/15'}`}>
                <ShieldCheck className={`h-5 w-5 ${chainIntegrity ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-600/20 hover-lift">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Violation Count</p>
                <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums">{auditSummary.violationCount}</p>
                <p className="text-[10px] text-muted-foreground">policy violations</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-violet-600/20 hover-lift">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Unique Agents</p>
                <p className="mt-1 text-3xl font-bold text-violet-600 dark:text-violet-400 tabular-nums">{auditSummary.uniqueAgents}</p>
                <p className="text-[10px] text-muted-foreground">tracked in chain</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15">
                <Users className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Event Breakdown + Recent Chain Entries */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Event Breakdown */}
        <Card className="border-purple-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              Event Breakdown
              <DataSourceBadge source="computed" />
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {pieData.length > 0 ? (
              <div className="flex flex-col items-center gap-4">
                <div className="h-[140px] w-[140px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={35}
                        outerRadius={60}
                        paddingAngle={3}
                        dataKey="value"
                        stroke="none"
                      >
                        {pieData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: 'var(--card)',
                          border: '1px solid var(--border)',
                          borderRadius: '8px',
                          fontSize: '11px',
                          color: 'var(--foreground)',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="w-full space-y-2">
                  {pieData.map((d) => (
                    <div key={d.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                        <span className="text-xs">{EVENT_CONFIG[d.name]?.label ?? d.name}</span>
                      </div>
                      <span className="text-xs font-bold tabular-nums">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
                No events recorded
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Chain Entries */}
        <Card className="lg:col-span-2 border-purple-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Link2 className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              Recent Chain Entries
              <Badge className="bg-purple-600/15 text-purple-600 dark:text-purple-400 border-0 text-[9px]">{recentEntries.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {recentEntries.length > 0 ? (
              <div className="max-h-96 space-y-1.5 overflow-y-auto custom-scrollbar">
                {recentEntries.slice(0, 25).map((entry) => (
                  <ChainEntryRow key={entry.entryId} entry={entry} onAttest={handleAttest} />
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
                No chain entries recorded
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ─── NEW: Authority Scope Distribution Card ─── */}
      <Card className="border-purple-600/15">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            Authority Scope Distribution
            <Badge className="bg-purple-600/10 text-purple-600 dark:text-purple-400 border-0 text-[8px]">Mythos Mapping</Badge>
            <DataSourceBadge source="computed" />
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {scopeBarData.length > 0 ? (
            <div className="space-y-3">
              {scopeBarData.map((item) => (
                <div key={item.scope} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: item.config.color }} />
                      <span className="text-xs font-medium">{item.label}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="font-bold tabular-nums">{item.count}</span>
                      <span className="text-muted-foreground">({item.percentage.toFixed(1)}%)</span>
                    </div>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full ${item.config.barColor} transition-all duration-500`}
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-20 text-xs text-muted-foreground">
              No authority scope data
            </div>
          )}
        </CardContent>
      </Card>

      {/* ─── NEW: Attestation & Identity Panel ─── */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* SLSA/in-toto Attestation Coverage */}
        <Card className="border-emerald-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              SLSA/in-toto Attestation
              <Badge className="bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0 text-[8px]">DERDDRE-01</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-4">
            <div>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span>SLSA Attestation Coverage</span>
                <span className="font-bold tabular-nums">
                  {attestationStats.slsaAttestedCount}/{attestationStats.totalEntries} entries
                </span>
              </div>
              <Progress
                value={attestationStats.totalEntries > 0 ? (attestationStats.slsaAttestedCount / attestationStats.totalEntries) * 100 : 0}
                className="h-2"
              />
              <p className="text-[10px] text-muted-foreground mt-1">
                {attestationStats.slsaAttestedCount}/{attestationStats.totalEntries} entries carry SLSA attestations
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span>Ed25519 Signature Coverage</span>
                <span className="font-bold tabular-nums">
                  {attestationStats.ed25519SignedCount}/{attestationStats.totalEntries} entries
                </span>
              </div>
              <Progress
                value={attestationStats.totalEntries > 0 ? (attestationStats.ed25519SignedCount / attestationStats.totalEntries) * 100 : 0}
                className="h-2"
              />
              <p className="text-[10px] text-muted-foreground mt-1">
                {attestationStats.ed25519SignedCount}/{attestationStats.totalEntries} entries have Ed25519 signatures
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Agent Identity Breakdown */}
        <Card className="border-violet-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Fingerprint className="h-4 w-4 text-violet-600 dark:text-violet-400" />
              Agent Identity Breakdown
              <Badge className="bg-violet-600/10 text-violet-600 dark:text-violet-400 border-0 text-[8px]">Crypto ID</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-600/5 border border-emerald-600/10">
              <div className="flex items-center gap-2">
                <Fingerprint className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium">Ed25519 Verified</span>
              </div>
              <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {agentIdentityBreakdown.ed25519Verified} agents
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-amber-600/5 border border-amber-600/10">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span className="text-xs font-medium">Pending Verification</span>
              </div>
              <span className="text-sm font-bold text-amber-600 dark:text-amber-400 tabular-nums">
                {agentIdentityBreakdown.pendingVerification} agents
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-600/5 border border-slate-600/10">
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                <span className="text-xs font-medium">Unknown Identity</span>
              </div>
              <span className="text-sm font-bold text-slate-600 dark:text-slate-400 tabular-nums">
                {agentIdentityBreakdown.unknownIdentity} agents
              </span>
            </div>
            <div className="pt-1 border-t border-border/30">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Total unique agents in recent entries</span>
                <span className="font-bold tabular-nums">{agentIdentityBreakdown.totalAgents}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
