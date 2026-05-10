'use client'

import { useState, useMemo, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Shield,
  ShieldCheck,
  Link2,
  CheckCircle2,
  XCircle,
  Clock,
  Box,
  Activity,
  Fingerprint,
  Lock,
  Unlock,
  ChevronRight,
  Copy,
  Play,
  FileCheck,
  AlertTriangle,
  Loader2,
  ArrowRight,
  BarChart3,
  Users,
  TrendingUp,
  Hash,
  Zap,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { MiniAreaChart } from '@/components/nexus/charts'

// ─── Types ───

type VapAction = 'GOVERNANCE' | 'BRIDGE' | 'VAULT' | 'SWARM' | 'GMR'

interface VapBlock {
  index: number
  hash: string
  previousHash: string
  action: VapAction
  agentId: string
  timestamp: string
  evidenceHash: string
  verified: boolean
  l1Valid: boolean
  l2Valid: boolean
  metadata?: Record<string, string>
}

interface VerificationEvent {
  id: string
  type: 'L1' | 'L2'
  status: 'PASS' | 'FAIL'
  timestamp: string
  details: string
  blocksChecked: number
  duration: string
}

// ─── Action Color Config ───

const actionColors: Record<VapAction, { bg: string; text: string; border: string; glow: string; badge: string; icon: typeof Shield }> = {
  GOVERNANCE: {
    bg: 'bg-emerald-600/15',
    text: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-600/30',
    glow: 'shadow-emerald-600/10',
    badge: 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-emerald-600/30',
    icon: Shield,
  },
  BRIDGE: {
    bg: 'bg-blue-600/15',
    text: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-600/30',
    glow: 'shadow-blue-600/10',
    badge: 'bg-blue-600/20 text-blue-600 dark:text-blue-400 border-blue-600/30',
    icon: Link2,
  },
  VAULT: {
    bg: 'bg-purple-600/15',
    text: 'text-purple-600 dark:text-purple-400',
    border: 'border-purple-600/30',
    glow: 'shadow-purple-600/10',
    badge: 'bg-purple-600/20 text-purple-600 dark:text-purple-400 border-purple-600/30',
    icon: Lock,
  },
  SWARM: {
    bg: 'bg-amber-600/15',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-600/30',
    glow: 'shadow-amber-600/10',
    badge: 'bg-amber-600/20 text-amber-600 dark:text-amber-400 border-amber-600/30',
    icon: Activity,
  },
  GMR: {
    bg: 'bg-cyan-600/15',
    text: 'text-cyan-600 dark:text-cyan-400',
    border: 'border-cyan-600/30',
    glow: 'shadow-cyan-600/10',
    badge: 'bg-cyan-600/20 text-cyan-600 dark:text-cyan-400 border-cyan-600/30',
    icon: Zap,
  },
}

// ─── Mock VAP Chain Data ───

function generateMockChain(): VapBlock[] {
  const actions: VapAction[] = ['GOVERNANCE', 'BRIDGE', 'VAULT', 'SWARM', 'GMR']
  const agents: Record<VapAction, string[]> = {
    GOVERNANCE: ['governor-1', 'governor-2'],
    BRIDGE: ['bridge-hmac', 'bridge-sync'],
    VAULT: ['vault-writer', 'vault-auditor'],
    SWARM: ['swarm-coord', 'worker-3', 'worker-1'],
    GMR: ['gmr-router', 'gmr-failover'],
  }
  const metadataTemplates: Record<VapAction, Record<string, string>> = {
    GOVERNANCE: { rule: 'constitution-check', scope: 'CRIT', outcome: 'blocked' },
    BRIDGE: { protocol: 'hmac-sha256', endpoint: '/sync/state', status: 'acknowledged' },
    VAULT: { track: 'EVENT', operation: 'write', score: '0.87' },
    SWARM: { task: 'T-0847', domain: 'code-review', result: 'completed' },
    GMR: { from: 'dolphin-mistral', to: 'trinity-large', reason: 'failover' },
  }

  const blocks: VapBlock[] = []
  const baseTime = new Date('2026-04-30T18:00:00Z').getTime()

  for (let i = 0; i < 18; i++) {
    const action = actions[i % actions.length]
    const agentList = agents[action]
    const agentId = agentList[i % agentList.length]
    const prevHash = i === 0
      ? '0000000000000000000000000000000000000000000000000000000000000000'
      : blocks[i - 1].hash

    // Simulate SHA-256 hash derivation
    const hashSeed = `block-${i}-${action}-${agentId}-${prevHash.slice(0, 8)}`
    const hash = sha256Mock(hashSeed)
    const evidenceSeed = `evidence-${i}-${action}`
    const evidenceHash = sha256Mock(evidenceSeed)

    const timestamp = new Date(baseTime + i * 5 * 60 * 1000).toISOString()

    blocks.push({
      index: i + 1,
      hash,
      previousHash: prevHash,
      action,
      agentId,
      timestamp,
      evidenceHash,
      verified: true,
      l1Valid: true,
      l2Valid: i > 2, // First 3 blocks don't have L2 yet
      metadata: { ...metadataTemplates[action], blockIndex: String(i + 1) },
    })
  }
  return blocks
}

// Simple deterministic hash simulator for display purposes
function sha256Mock(input: string): string {
  let h = 0x6a09e667
  for (let i = 0; i < input.length; i++) {
    h = ((h << 5) - h + input.charCodeAt(i)) | 0
  }
  const hex = Math.abs(h).toString(16).padStart(8, '0')
  const parts = [hex]
  let seed = h
  for (let i = 0; i < 7; i++) {
    seed = ((seed << 5) - seed + 0x5be0cd19) | 0
    parts.push(Math.abs(seed).toString(16).padStart(8, '0'))
  }
  return parts.join('')
}

const mockChain = generateMockChain()

// ─── Initial Verification Events ───

const initialVerificationEvents: VerificationEvent[] = [
  { id: 've-1', type: 'L1', status: 'PASS', timestamp: '2026-04-30T19:45:00Z', details: 'Full hash chain integrity verified', blocksChecked: 18, duration: '0.23s' },
  { id: 've-2', type: 'L2', status: 'PASS', timestamp: '2026-04-30T19:40:00Z', details: 'Cross-attestation from 3 witnesses', blocksChecked: 15, duration: '1.42s' },
  { id: 've-3', type: 'L1', status: 'PASS', timestamp: '2026-04-30T19:30:00Z', details: 'Full hash chain integrity verified', blocksChecked: 18, duration: '0.21s' },
  { id: 've-4', type: 'L2', status: 'PASS', timestamp: '2026-04-30T19:15:00Z', details: 'Cross-attestation from 3 witnesses', blocksChecked: 12, duration: '1.38s' },
  { id: 've-5', type: 'L1', status: 'PASS', timestamp: '2026-04-30T19:00:00Z', details: 'Full hash chain integrity verified', blocksChecked: 18, duration: '0.19s' },
]

// ─── Agent Activity Data ───

const agentActivityData = [
  { name: 'governor-1', blocks: 5, color: '#34d399' },
  { name: 'bridge-hmac', blocks: 4, color: '#60a5fa' },
  { name: 'vault-writer', blocks: 4, color: '#a78bfa' },
  { name: 'swarm-coord', blocks: 3, color: '#fbbf24' },
  { name: 'gmr-router', blocks: 2, color: '#22d3ee' },
]

// ─── Chain Growth Timeline ───

const chainGrowthData = [
  { name: '18:00', blocks: 1 },
  { name: '18:15', blocks: 4 },
  { name: '18:30', blocks: 7 },
  { name: '18:45', blocks: 10 },
  { name: '19:00', blocks: 12 },
  { name: '19:15', blocks: 14 },
  { name: '19:30', blocks: 16 },
  { name: '19:45', blocks: 18 },
]

// ─── Helper ───

function truncateHash(hash: string, chars = 8): string {
  if (hash.length <= chars * 2 + 3) return hash
  return `${hash.slice(0, chars)}...${hash.slice(-chars)}`
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function timeAgo(iso: string): string {
  const now = new Date('2026-04-30T19:50:00Z')
  const then = new Date(iso)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  return `${diffHrs}h ago`
}

// ─── Component ───

export function VapTab() {
  const [chain] = useState<VapBlock[]>(mockChain)
  const [selectedBlock, setSelectedBlock] = useState<VapBlock | null>(null)
  const [blockDialogOpen, setBlockDialogOpen] = useState(false)
  const [verificationEvents, setVerificationEvents] = useState<VerificationEvent[]>(initialVerificationEvents)
  const [l1Verifying, setL1Verifying] = useState(false)
  const [l2Verifying, setL2Verifying] = useState(false)
  const [l1Result, setL1Result] = useState<'idle' | 'pass' | 'fail'>('idle')
  const [l2Result, setL2Result] = useState<'idle' | 'pass' | 'fail'>('idle')
  const [expandedBlock, setExpandedBlock] = useState<number | null>(null)

  // Chain statistics
  const totalBlocks = chain.length
  const genesisHash = chain[0]?.hash ?? 'N/A'
  const lastBlock = chain[chain.length - 1]
  const chainIntegrity = chain.every((b) => b.verified) ? 'Verified' : 'Compromised'
  const chainIntact = chainIntegrity === 'Verified'

  // Action distribution
  const actionDistribution = useMemo(() => {
    const dist: Record<VapAction, number> = { GOVERNANCE: 0, BRIDGE: 0, VAULT: 0, SWARM: 0, GMR: 0 }
    chain.forEach((b) => { dist[b.action]++ })
    return Object.entries(dist).map(([action, count]) => ({
      action: action as VapAction,
      count,
      pct: totalBlocks > 0 ? Math.round((count / totalBlocks) * 100) : 0,
    }))
  }, [chain, totalBlocks])

  // L1 Verification handler
  const runL1Verification = useCallback(() => {
    setL1Verifying(true)
    setL1Result('idle')
    setTimeout(() => {
      const allValid = chain.every((b) => b.l1Valid)
      setL1Result(allValid ? 'pass' : 'fail')
      setL1Verifying(false)
      const newEvent: VerificationEvent = {
        id: `ve-${Date.now()}`,
        type: 'L1',
        status: allValid ? 'PASS' : 'FAIL',
        timestamp: new Date().toISOString(),
        details: allValid ? 'Full hash chain integrity verified' : 'Hash chain break detected',
        blocksChecked: totalBlocks,
        duration: `${(Math.random() * 0.3 + 0.15).toFixed(2)}s`,
      }
      setVerificationEvents((prev) => [newEvent, ...prev].slice(0, 10))
      if (allValid) {
        toast.success('L1 Verification Passed', { description: `All ${totalBlocks} blocks verified — hash chain is consistent.` })
      } else {
        toast.error('L1 Verification Failed', { description: 'Hash chain integrity break detected!' })
      }
    }, 1500)
  }, [chain, totalBlocks])

  // L2 Verification handler
  const runL2Verification = useCallback(() => {
    setL2Verifying(true)
    setL2Result('idle')
    setTimeout(() => {
      const l2Blocks = chain.filter((b) => b.l2Valid)
      const allValid = l2Blocks.length === chain.length - 3 // First 3 blocks have no L2
      setL2Result(allValid ? 'pass' : 'fail')
      setL2Verifying(false)
      const newEvent: VerificationEvent = {
        id: `ve-${Date.now()}`,
        type: 'L2',
        status: allValid ? 'PASS' : 'FAIL',
        timestamp: new Date().toISOString(),
        details: allValid ? `Cross-attestation from 3 witnesses (${chain.length - 3} blocks)` : 'Attestation quorum not reached',
        blocksChecked: l2Blocks.length,
        duration: `${(Math.random() * 1.5 + 0.8).toFixed(2)}s`,
      }
      setVerificationEvents((prev) => [newEvent, ...prev].slice(0, 10))
      if (allValid) {
        toast.success('L2 Verification Passed', { description: `Cross-attestation confirmed for ${l2Blocks.length} blocks.` })
      } else {
        toast.error('L2 Verification Failed', { description: 'Attestation quorum not reached.' })
      }
    }, 2200)
  }, [chain])

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash).then(
      () => toast.success('Hash copied to clipboard'),
      () => toast.error('Failed to copy')
    )
  }

  const openBlockDetail = (block: VapBlock) => {
    setSelectedBlock(block)
    setBlockDialogOpen(true)
  }

  return (
    <div className="space-y-6 p-6 grid-pattern animate-fade-in">
      {/* ═══ Section 1: Chain Status Header ═══ */}
      <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-cyan-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-600/10">
              <Link2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">VAP Proof Chain</h2>
              <p className="text-xs text-muted-foreground">SHA-256 immutable audit trail · L1+L2 cryptographic verification</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`border-0 text-[10px] gap-1 ${chainIntact ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
              {chainIntact ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
              {chainIntegrity}
            </Badge>
          </div>
        </div>
      </div>

      {/* Status Cards Row */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {/* Total Blocks */}
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Blocks</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{totalBlocks}</p>
                <p className="text-[10px] text-muted-foreground">in chain</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Box className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Chain Integrity */}
        <Card className={`relative overflow-hidden hover-lift ${chainIntact ? 'border-emerald-600/20' : 'border-red-600/20'}`}>
          <div className={`absolute inset-0 bg-gradient-to-br ${chainIntact ? 'from-emerald-600/10 via-emerald-600/3 to-transparent' : 'from-red-600/10 via-red-600/3 to-transparent'}`} />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Chain Integrity</p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${chainIntact ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {chainIntegrity}
                </p>
                <p className="text-[10px] text-muted-foreground">{chainIntact ? 'no tampering' : 'BREACH DETECTED'}</p>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl shadow-lg ${chainIntact ? 'bg-emerald-600/15 shadow-emerald-600/10' : 'bg-red-600/15 shadow-red-600/10'}`}>
                {chainIntact ? <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" /> : <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* L1 Verification */}
        <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">L1 Verification</p>
                <p className={`mt-1 text-xl font-bold tabular-nums ${l1Result === 'fail' ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'}`}>
                  {l1Result === 'idle' ? 'Pending' : l1Result === 'pass' ? 'Passed' : 'Failed'}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {l1Result === 'idle' ? 'not yet run' : `checked ${totalBlocks} blocks`}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Fingerprint className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* L2 Verification */}
        <Card className="relative overflow-hidden border-cyan-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-600/10 via-cyan-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">L2 Attestation</p>
                <p className={`mt-1 text-xl font-bold tabular-nums ${l2Result === 'fail' ? 'text-red-600 dark:text-red-400' : 'text-cyan-600 dark:text-cyan-400'}`}>
                  {l2Result === 'idle' ? 'Pending' : l2Result === 'pass' ? 'Attested' : 'Failed'}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {l2Result === 'idle' ? 'not yet run' : `${chain.length - 3} blocks attested`}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-600/15 shadow-lg shadow-cyan-600/10">
                <FileCheck className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Genesis Hash */}
        <Card className="relative overflow-hidden border-purple-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Genesis Hash</p>
                <p className="mt-1 text-sm font-bold font-mono text-purple-600 dark:text-purple-400 truncate max-w-[140px]">
                  {truncateHash(genesisHash, 6)}
                </p>
                <p className="text-[10px] text-muted-foreground">block #1</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15 shadow-lg shadow-purple-600/10">
                <Hash className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ═══ Section 2: Visual Chain ═══ */}
      <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-cyan-600/3" />
        <CardHeader className="relative pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Link2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Visual Proof Chain
            </CardTitle>
            <div className="flex items-center gap-2">
              {(['GOVERNANCE', 'BRIDGE', 'VAULT', 'SWARM', 'GMR'] as VapAction[]).map((action) => {
                const cfg = actionColors[action]
                const IconComp = cfg.icon
                return (
                  <Badge key={action} variant="outline" className={`text-[9px] gap-1 ${cfg.badge} border`}>
                    <IconComp className="h-2.5 w-2.5" />
                    {action}
                  </Badge>
                )
              })}
            </div>
          </div>
        </CardHeader>
        <CardContent className="relative p-4 pt-2">
          <div className="max-h-[520px] overflow-y-auto custom-scrollbar space-y-0">
            {chain.map((block, i) => {
              const cfg = actionColors[block.action]
              const IconComp = cfg.icon
              const isExpanded = expandedBlock === block.index
              const prevBlock = i > 0 ? chain[i - 1] : null
              const hashChainValid = i === 0 || block.previousHash === prevBlock?.hash

              return (
                <motion.div
                  key={block.index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.3 }}
                >
                  {/* Connector line */}
                  {i > 0 && (
                    <div className="flex items-center ml-5 h-4">
                      <div className={`w-0.5 h-full ${hashChainValid ? 'bg-emerald-600/30' : 'bg-red-600/50'}`} />
                      {!hashChainValid && (
                        <XCircle className="h-3 w-3 text-red-500 ml-1" />
                      )}
                    </div>
                  )}

                  {/* Block Card */}
                  <div
                    className={`relative flex items-stretch gap-3 cursor-pointer group rounded-lg border ${cfg.border} ${cfg.bg} transition-all duration-200 hover:shadow-md ${cfg.glow}`}
                    onClick={() => setExpandedBlock(isExpanded ? null : block.index)}
                  >
                    {/* Block number badge */}
                    <div className="flex flex-col items-center justify-center w-12 shrink-0">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${cfg.bg} border ${cfg.border}`}>
                        <span className="text-[10px] font-bold tabular-nums text-muted-foreground"># {block.index}</span>
                      </div>
                    </div>

                    {/* Block content */}
                    <div className="flex-1 min-w-0 py-2.5 pr-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className={`text-[9px] gap-1 ${cfg.badge} border`}>
                          <IconComp className="h-2.5 w-2.5" />
                          {block.action}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground font-mono">{block.agentId}</span>
                        <span className="ml-auto text-[9px] text-muted-foreground tabular-nums">
                          {formatTimestamp(block.timestamp)}
                        </span>
                        <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                      </div>

                      {/* Hash display */}
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-600/70 dark:text-emerald-400/70">
                          {truncateHash(block.hash, 10)}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); copyHash(block.hash) }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Copy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                        </button>
                        {block.verified && (
                          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                        )}
                      </div>

                      {/* Expanded details */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 grid gap-2 sm:grid-cols-2 text-[10px]">
                              <div className="space-y-1">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-muted-foreground">Prev Hash:</span>
                                  <span className="font-mono text-blue-600/70 dark:text-blue-400/70">{truncateHash(block.previousHash, 8)}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-muted-foreground">Evidence:</span>
                                  <span className="font-mono text-purple-600/70 dark:text-purple-400/70">{truncateHash(block.evidenceHash, 8)}</span>
                                </div>
                              </div>
                              <div className="space-y-1">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-muted-foreground">L1:</span>
                                  {block.l1Valid ? <CheckCircle2 className="h-3 w-3 text-emerald-500" /> : <XCircle className="h-3 w-3 text-red-500" />}
                                  <span className={block.l1Valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                                    {block.l1Valid ? 'Valid' : 'Invalid'}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-muted-foreground">L2:</span>
                                  {block.l2Valid ? <CheckCircle2 className="h-3 w-3 text-emerald-500" /> : <XCircle className="h-3 w-3 text-amber-500" />}
                                  <span className={block.l2Valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}>
                                    {block.l2Valid ? 'Attested' : 'Pending'}
                                  </span>
                                </div>
                              </div>
                              {block.metadata && (
                                <div className="sm:col-span-2">
                                  <span className="text-muted-foreground">Metadata: </span>
                                  {Object.entries(block.metadata).map(([k, v]) => (
                                    <span key={k} className="inline-flex items-center gap-0.5 mr-2">
                                      <span className="text-foreground/60">{k}=</span>
                                      <span className="font-mono text-foreground/80">{v}</span>
                                    </span>
                                  ))}
                                </div>
                              )}
                              <div className="sm:col-span-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-[10px] gap-1 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300"
                                  onClick={(e) => { e.stopPropagation(); openBlockDetail(block) }}
                                >
                                  <ArrowRight className="h-3 w-3" /> View Full Details
                                </Button>
                              </div>
                            </div>

                            {/* Hash chain visual */}
                            <div className="mt-2 flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-muted/30 border border-border/30">
                              {i > 0 && (
                                <>
                                  <span className="text-[8px] text-muted-foreground">prev</span>
                                  <span className="font-mono text-[9px] text-blue-600/60 dark:text-blue-400/60">{truncateHash(block.previousHash, 6)}</span>
                                  <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/50" />
                                </>
                              )}
                              <span className="text-[8px] text-muted-foreground">SHA-256</span>
                              <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/50" />
                              <span className="font-mono text-[9px] text-emerald-600/60 dark:text-emerald-400/60">{truncateHash(block.hash, 6)}</span>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* ═══ Section 3: Verification Panel ═══ */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Verification Actions */}
        <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Cryptographic Verification
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-2 space-y-4">
            {/* L1 Verification */}
            <div className="rounded-lg border border-blue-600/20 bg-blue-600/3 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Fingerprint className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-semibold">L1 — Hash Chain Integrity</span>
                </div>
                <Badge className={`border-0 text-[10px] ${l1Result === 'pass' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : l1Result === 'fail' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : 'bg-blue-600/15 text-blue-600 dark:text-blue-400'}`}>
                  {l1Result === 'idle' ? 'Pending' : l1Result === 'pass' ? '✓ Pass' : '✗ Fail'}
                </Badge>
              </div>
              <p className="text-[10px] text-muted-foreground mb-3">
                Verifies that each block&apos;s previousHash matches the prior block&apos;s hash — ensures the chain has not been tampered with.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs border-blue-600/30 text-blue-600 dark:text-blue-400 hover:bg-blue-600/10"
                onClick={runL1Verification}
                disabled={l1Verifying}
              >
                {l1Verifying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {l1Verifying ? 'Verifying...' : 'Run L1 Check'}
              </Button>
              {l1Result !== 'idle' && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mt-3 flex items-center gap-2 rounded-md p-2 ${l1Result === 'pass' ? 'bg-emerald-600/10 border border-emerald-600/20' : 'bg-red-600/10 border border-red-600/20'}`}
                >
                  {l1Result === 'pass' ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
                  <span className={`text-xs ${l1Result === 'pass' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                    {l1Result === 'pass' ? `All ${totalBlocks} blocks verified — hash chain consistent` : 'Hash chain integrity break detected'}
                  </span>
                </motion.div>
              )}
            </div>

            {/* L2 Verification */}
            <div className="rounded-lg border border-cyan-600/20 bg-cyan-600/3 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileCheck className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
                  <span className="text-sm font-semibold">L2 — Cross-Attestation</span>
                </div>
                <Badge className={`border-0 text-[10px] ${l2Result === 'pass' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : l2Result === 'fail' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : 'bg-cyan-600/15 text-cyan-600 dark:text-cyan-400'}`}>
                  {l2Result === 'idle' ? 'Pending' : l2Result === 'pass' ? '✓ Attested' : '✗ Failed'}
                </Badge>
              </div>
              <p className="text-[10px] text-muted-foreground mb-3">
                External witnesses verify block contents through cross-attestation — provides third-party confirmation of chain state.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs border-cyan-600/30 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-600/10"
                onClick={runL2Verification}
                disabled={l2Verifying}
              >
                {l2Verifying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {l2Verifying ? 'Attesting...' : 'Run L2 Attestation'}
              </Button>
              {l2Result !== 'idle' && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mt-3 flex items-center gap-2 rounded-md p-2 ${l2Result === 'pass' ? 'bg-emerald-600/10 border border-emerald-600/20' : 'bg-red-600/10 border border-red-600/20'}`}
                >
                  {l2Result === 'pass' ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
                  <span className={`text-xs ${l2Result === 'pass' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                    {l2Result === 'pass' ? `${chain.length - 3} blocks attested by 3 witnesses` : 'Attestation quorum not reached'}
                  </span>
                </motion.div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Verification Event Log */}
        <Card className="relative overflow-hidden border-blue-600/20 shadow-lg">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Verification Log
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-2">
            <div className="max-h-[300px] overflow-y-auto custom-scrollbar space-y-2">
              {verificationEvents.map((evt) => (
                <div
                  key={evt.id}
                  className={`flex items-start gap-3 rounded-md border p-2.5 transition-colors ${
                    evt.status === 'PASS'
                      ? 'border-emerald-600/15 bg-emerald-600/3'
                      : 'border-red-600/15 bg-red-600/3'
                  }`}
                >
                  <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                    evt.type === 'L1' ? 'bg-blue-600/15' : 'bg-cyan-600/15'
                  }`}>
                    {evt.status === 'PASS' ? (
                      <CheckCircle2 className={`h-3.5 w-3.5 ${evt.type === 'L1' ? 'text-blue-600 dark:text-blue-400' : 'text-cyan-600 dark:text-cyan-400'}`} />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-red-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge className={`border-0 text-[9px] ${evt.type === 'L1' ? 'bg-blue-600/15 text-blue-600 dark:text-blue-400' : 'bg-cyan-600/15 text-cyan-600 dark:text-cyan-400'}`}>
                        {evt.type}
                      </Badge>
                      <Badge className={`border-0 text-[9px] ${evt.status === 'PASS' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
                        {evt.status}
                      </Badge>
                      <span className="text-[9px] text-muted-foreground tabular-nums ml-auto">{timeAgo(evt.timestamp)}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{evt.details}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[9px] text-muted-foreground tabular-nums">{evt.blocksChecked} blocks</span>
                      <span className="text-[9px] text-muted-foreground tabular-nums">{evt.duration}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ═══ Section 4: Audit Statistics ═══ */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Action Type Distribution */}
        <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Action Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-2 space-y-3">
            {/* Stacked bar */}
            <div className="flex h-6 w-full rounded-md overflow-hidden border border-border/30">
              {actionDistribution.map((d) => {
                const cfg = actionColors[d.action]
                const colorMap: Record<VapAction, string> = {
                  GOVERNANCE: '#34d399',
                  BRIDGE: '#60a5fa',
                  VAULT: '#a78bfa',
                  SWARM: '#fbbf24',
                  GMR: '#22d3ee',
                }
                return (
                  <div
                    key={d.action}
                    className={`h-full transition-all duration-500 ${cfg.bg}`}
                    style={{ width: `${d.pct}%`, backgroundColor: colorMap[d.action] + '40' }}
                    title={`${d.action}: ${d.count} (${d.pct}%)`}
                  />
                )
              })}
            </div>

            {/* Legend + counts */}
            {actionDistribution.map((d) => {
              const cfg = actionColors[d.action]
              const IconComp = cfg.icon
              const colorMap: Record<VapAction, string> = {
                GOVERNANCE: '#34d399',
                BRIDGE: '#60a5fa',
                VAULT: '#a78bfa',
                SWARM: '#fbbf24',
                GMR: '#22d3ee',
              }
              return (
                <div key={d.action} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: colorMap[d.action] }} />
                  <IconComp className={`h-3 w-3 ${cfg.text}`} />
                  <span className="text-xs font-medium flex-1">{d.action}</span>
                  <span className="text-xs tabular-nums font-bold">{d.count}</span>
                  <span className="text-[10px] text-muted-foreground tabular-nums">({d.pct}%)</span>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Agent Activity Breakdown */}
        <Card className="relative overflow-hidden border-blue-600/20 shadow-lg">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Agent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-2 space-y-3">
            {agentActivityData.map((agent) => {
              const maxBlocks = Math.max(...agentActivityData.map((a) => a.blocks))
              const pct = maxBlocks > 0 ? (agent.blocks / maxBlocks) * 100 : 0
              return (
                <div key={agent.name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium font-mono">{agent.name}</span>
                    <span className="text-[10px] tabular-nums text-muted-foreground">{agent.blocks} blocks</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted/30 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${pct}%`, backgroundColor: agent.color }}
                    />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Chain Growth Timeline */}
        <Card className="relative overflow-hidden border-purple-600/20 shadow-lg">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-purple-600/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              Chain Growth
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-2">
            <MiniAreaChart
              data={chainGrowthData}
              dataKey="blocks"
              color="#a78bfa"
              height={140}
              showAxis
            />
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>Growth over time</span>
              <span className="font-mono tabular-nums">{totalBlocks} total blocks</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ═══ Block Detail Dialog ═══ */}
      <Dialog open={blockDialogOpen} onOpenChange={setBlockDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          {selectedBlock && (() => {
            const cfg = actionColors[selectedBlock.action]
            const IconComp = cfg.icon
            const colorMap: Record<VapAction, string> = {
              GOVERNANCE: '#34d399',
              BRIDGE: '#60a5fa',
              VAULT: '#a78bfa',
              SWARM: '#fbbf24',
              GMR: '#22d3ee',
            }
            return (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${cfg.bg}`} style={{ backgroundColor: colorMap[selectedBlock.action] + '30' }}>
                      <IconComp className={`h-5 w-5 ${cfg.text}`} />
                    </div>
                    <div>
                      <DialogTitle className="text-base">
                        Block #{selectedBlock.index}
                      </DialogTitle>
                      <DialogDescription className="text-xs">
                        VAP Proof Chain Block Detail
                      </DialogDescription>
                    </div>
                  </div>
                </DialogHeader>

                <div className="space-y-4 mt-2">
                  {/* Action & Agent */}
                  <div className="flex items-center gap-2">
                    <Badge className={`text-[10px] gap-1 ${cfg.badge} border`}>
                      <IconComp className="h-3 w-3" />
                      {selectedBlock.action}
                    </Badge>
                    <span className="text-xs text-muted-foreground">Agent:</span>
                    <span className="text-xs font-mono font-medium">{selectedBlock.agentId}</span>
                  </div>

                  {/* Hash Information */}
                  <div className="rounded-lg border border-border/50 bg-muted/30 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Block Hash</span>
                      <button onClick={() => copyHash(selectedBlock.hash)} className="text-muted-foreground hover:text-foreground transition-colors">
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <p className="text-xs font-mono break-all text-emerald-600/80 dark:text-emerald-400/80">{selectedBlock.hash}</p>

                    <div className="border-t border-border/30 pt-2">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Previous Hash</span>
                      <p className="text-xs font-mono break-all text-blue-600/80 dark:text-blue-400/80 mt-0.5">{selectedBlock.previousHash}</p>
                    </div>

                    <div className="border-t border-border/30 pt-2">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Evidence Hash</span>
                      <p className="text-xs font-mono break-all text-purple-600/80 dark:text-purple-400/80 mt-0.5">{selectedBlock.evidenceHash}</p>
                    </div>
                  </div>

                  {/* Verification Status */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-blue-600/15 bg-blue-600/3 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Fingerprint className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                        <span className="text-xs font-semibold">L1 Verification</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {selectedBlock.l1Valid ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
                        <span className={`text-xs ${selectedBlock.l1Valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                          {selectedBlock.l1Valid ? 'Hash chain valid' : 'Hash chain invalid'}
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border border-cyan-600/15 bg-cyan-600/3 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <FileCheck className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
                        <span className="text-xs font-semibold">L2 Attestation</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {selectedBlock.l2Valid ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-amber-500" />}
                        <span className={`text-xs ${selectedBlock.l2Valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                          {selectedBlock.l2Valid ? 'Cross-attested' : 'Awaiting attestation'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Timestamp */}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{new Date(selectedBlock.timestamp).toLocaleString('en-US', { hour12: false })}</span>
                  </div>

                  {/* Metadata */}
                  {selectedBlock.metadata && (
                    <div className="rounded-lg border border-border/30 bg-muted/20 p-3">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Metadata</span>
                      <div className="mt-1.5 space-y-1">
                        {Object.entries(selectedBlock.metadata).map(([k, v]) => (
                          <div key={k} className="flex items-center gap-2 text-xs">
                            <span className="text-muted-foreground">{k}:</span>
                            <span className="font-mono">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <DialogFooter className="gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={() => copyHash(selectedBlock.hash)}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy Hash
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                    onClick={() => {
                      setBlockDialogOpen(false)
                      toast.info('Navigating to Vault entry...', { description: `Evidence hash: ${truncateHash(selectedBlock.evidenceHash, 10)}` })
                    }}
                  >
                    <Lock className="h-3.5 w-3.5" />
                    View in Vault
                  </Button>
                </DialogFooter>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
