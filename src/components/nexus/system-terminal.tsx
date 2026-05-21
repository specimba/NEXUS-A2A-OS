'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Terminal } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { motion, AnimatePresence } from 'framer-motion'

// ── Types ──────────────────────────────────────────────────────────
interface TerminalLine {
  id: number
  text: string
  type: 'input' | 'output' | 'success' | 'warning' | 'error' | 'info' | 'system'
}

interface AgentData {
  id: string
  name: string
  role?: string
  type?: string
  trustScore?: number
  status?: string
  totalTokens?: number
}

interface VaultData {
  entries: Array<{
    id: string
    track?: string
    key?: string
    value?: string
    score?: number
    agent: { name?: string } | null
  }>
}

interface ModelData {
  models: Array<{
    id: string
    name?: string
    tier?: number
    pool?: string
    health?: number
    latencyMs?: number
    isActive?: boolean
    successRate?: number
    totalCalls?: number
  }>
}

interface TokenData {
  budget: {
    totalBudget?: number
    usedBudget?: number
    remainingBudget?: number
  } | null
  agentUsage: Array<{ name?: string; totalTokens?: number }>
}

// ── Simulated command data ─────────────────────────────────────────
const HELP_TEXT = [
  { text: 'Available commands:', type: 'info' as const },
  { text: '  help          Show this help message', type: 'output' as const },
  { text: '  status        Show system status summary', type: 'output' as const },
  { text: '  agents        List registered agents', type: 'output' as const },
  { text: '  vault         Show vault statistics', type: 'output' as const },
  { text: '  gmr           Show GMR model registry', type: 'output' as const },
  { text: '  governor      Show governor decisions', type: 'output' as const },
  { text: '  tokens        Show token budget', type: 'output' as const },
  { text: '  ping          Simulate network ping', type: 'output' as const },
  { text: '  uptime        Show system uptime', type: 'output' as const },
  { text: '  whoami        Show current user context', type: 'output' as const },
  { text: '  ls            List NEXUS modules', type: 'output' as const },
  { text: '  cat constitution  Display constitution rules', type: 'output' as const },
  { text: '  clear         Clear terminal history', type: 'output' as const },
]

const STATUS_LINES: TerminalLine[] = [
  { id: 0, text: '╔══════════════════════════════════════╗', type: 'info' },
  { id: 1, text: '║     NEXUS OS v3.1 — System Status    ║', type: 'info' },
  { id: 2, text: '╚══════════════════════════════════════╝', type: 'info' },
  { id: 3, text: '', type: 'output' },
  { id: 4, text: 'Pillar Health:', type: 'success' },
  { id: 5, text: '  Bridge   ██████████ 100%  operational', type: 'success' },
  { id: 6, text: '  Engine   █████████░  98%  operational', type: 'success' },
  { id: 7, text: '  Governor █████████░  95%  operational', type: 'success' },
  { id: 8, text: '  Vault    ██████████ 100%  operational', type: 'success' },
  { id: 9, text: '  GMR      █████████░  92%  operational', type: 'warning' },
  { id: 10, text: '  Swarm    █████████░  88%  degraded', type: 'warning' },
  { id: 11, text: '  Monitor  █████████░  96%  operational', type: 'success' },
  { id: 12, text: '  Config   ██████████ 100%  operational', type: 'success' },
  { id: 13, text: '', type: 'output' },
  { id: 14, text: 'Overall: 7/8 operational, 1 degraded', type: 'warning' },
  { id: 15, text: 'Uptime: 3d 14h 27m | Token Budget: 73,450 / 100,000', type: 'info' },
]

const GOVERNOR_LINES: TerminalLine[] = [
  { id: 0, text: 'Governor Engine — Kaiju v2.4', type: 'info' },
  { id: 1, text: '────────────────────────────────', type: 'output' },
  { id: 2, text: '', type: 'output' },
  { id: 3, text: 'Recent Decisions:', type: 'info' },
  { id: 4, text: '  [ALLOW] worker-3 → read file (scope: SELF)', type: 'success' },
  { id: 5, text: '  [ALLOW] worker-1 → API call (scope: SELF)', type: 'success' },
  { id: 6, text: '  [HOLD]  research-agent → API call (scope: CROSS)', type: 'warning' },
  { id: 7, text: '  [DENY]  worker-2 → delete_all (scope: CRIT)', type: 'error' },
  { id: 8, text: '  [ALLOW] coordinator → write file (scope: SELF)', type: 'success' },
  { id: 9, text: '', type: 'output' },
  { id: 10, text: 'Trust Score Thresholds:', type: 'info' },
  { id: 11, text: '  research: 0.60 | review: 0.70 | audit: 0.80 | impl: 0.75', type: 'output' },
  { id: 12, text: '', type: 'output' },
  { id: 13, text: 'Decision Rate (24h): ALLOW 96.9% | DENY 2.6% | HOLD 0.5%', type: 'success' },
]

const PING_LINES: TerminalLine[] = [
  { id: 0, text: 'PING nexus-os.local (127.0.0.1)', type: 'info' },
  { id: 1, text: '64 bytes: icmp_seq=1 ttl=64 time=2.3ms', type: 'success' },
  { id: 2, text: '64 bytes: icmp_seq=2 ttl=64 time=1.8ms', type: 'success' },
  { id: 3, text: '64 bytes: icmp_seq=3 ttl=64 time=2.1ms', type: 'success' },
  { id: 4, text: '64 bytes: icmp_seq=4 ttl=64 time=1.9ms', type: 'success' },
  { id: 5, text: '', type: 'output' },
  { id: 6, text: '--- nexus-os.local ping statistics ---', type: 'info' },
  { id: 7, text: '4 packets transmitted, 4 received, 0% loss', type: 'success' },
  { id: 8, text: 'rtt min/avg/max = 1.8/2.0/2.3 ms', type: 'output' },
]

const UPTIME_LINES: TerminalLine[] = [
  { id: 0, text: 'System Uptime Report', type: 'info' },
  { id: 1, text: '────────────────────────────────', type: 'output' },
  { id: 2, text: '  Uptime:       3d 14h 27m 52s', type: 'success' },
  { id: 3, text: '  Availability: 99.94%', type: 'success' },
  { id: 4, text: '  Last Restart: 3d 14h ago', type: 'output' },
  { id: 5, text: '  Active Since: 2025-02-25 08:42:17 UTC', type: 'output' },
  { id: 6, text: '', type: 'output' },
  { id: 7, text: 'Service Health:', type: 'info' },
  { id: 8, text: '  Bridge     3d 14h  ▓▓▓▓▓▓▓▓▓▓ 100%', type: 'success' },
  { id: 9, text: '  Engine     3d 14h  ▓▓▓▓▓▓▓▓▓░  98%', type: 'success' },
  { id: 10, text: '  Governor   3d 14h  ▓▓▓▓▓▓▓▓▓░  95%', type: 'warning' },
  { id: 11, text: '  Swarm      3d 14h  ▓▓▓▓▓▓▓▓░░  88%', type: 'warning' },
]

const WHOAMI_LINES: TerminalLine[] = [
  { id: 0, text: 'User Context:', type: 'info' },
  { id: 1, text: '────────────────────────────────', type: 'output' },
  { id: 2, text: '  User:      nexus-operator', type: 'output' },
  { id: 3, text: '  Role:      admin', type: 'success' },
  { id: 4, text: '  Session:   ses-7f3a2c91', type: 'output' },
  { id: 5, text: '  Scope:     CRIT (full access)', type: 'success' },
  { id: 6, text: '  Trust:     0.95', type: 'success' },
  { id: 7, text: '  Agent:     coordinator', type: 'output' },
  { id: 8, text: '  Node:      nexus-primary-01', type: 'output' },
]

const LS_LINES: TerminalLine[] = [
  { id: 0, text: 'NEXUS Modules:', type: 'info' },
  { id: 1, text: '────────────────────────────────', type: 'output' },
  { id: 2, text: '  drwxr-xr-x  bridge/       HMAC auth & JSON-RPC', type: 'output' },
  { id: 3, text: '  drwxr-xr-x  engine/       Hermes intent routing', type: 'output' },
  { id: 4, text: '  drwxr-xr-x  governor/     Kaiju + TrustScorer', type: 'output' },
  { id: 5, text: '  drwxr-xr-x  vault/        5-Track memory system', type: 'output' },
  { id: 6, text: '  drwxr-xr-x  gmr/          Giant Model Router', type: 'output' },
  { id: 7, text: '  drwxr-xr-x  swarm/        Worker pool manager', type: 'output' },
  { id: 8, text: '  drwxr-xr-x  monitor/      Token budget & audit', type: 'output' },
  { id: 9, text: '  drwxr-xr-x  config/       Constitution manager', type: 'output' },
  { id: 10, text: '  -rw-r--r--  constitution   v3.2 operational rules', type: 'output' },
  { id: 11, text: '  -rw-r--r--  boot.md        NEXUS-BOOT sequence', type: 'output' },
  { id: 12, text: '  -rw-r--r--  state.json     NEXUS-STATE snapshot', type: 'output' },
]

const CONSTITUTION_LINES: TerminalLine[] = [
  { id: 0, text: 'NEXUS Constitution v3.2', type: 'info' },
  { id: 1, text: '═══════════════════════════════════════', type: 'info' },
  { id: 2, text: '', type: 'output' },
  { id: 3, text: 'Rule 1: No agent may delete data without CRIT scope approval', type: 'error' },
  { id: 4, text: 'Rule 2: All cross-scope requests must be reviewed (HOLD)', type: 'warning' },
  { id: 5, text: 'Rule 3: Trust scores below 0.60 trigger automatic review', type: 'warning' },
  { id: 6, text: 'Rule 4: Token budget exhaustion triggers system pause', type: 'error' },
  { id: 7, text: 'Rule 5: VAP chain must be verified every 1000 entries', type: 'info' },
  { id: 8, text: 'Rule 6: Model failover requires health < 30% or 3x timeout', type: 'warning' },
  { id: 9, text: 'Rule 7: Worker reassignment needs foreman + governor approval', type: 'info' },
  { id: 10, text: 'Rule 8: Constitution changes require 2/3 agent consensus', type: 'info' },
  { id: 11, text: '', type: 'output' },
  { id: 12, text: 'Last updated: 2025-02-28 | Hash: a4f2c8e1', type: 'output' },
]

const BOOT_SEQUENCE: TerminalLine[] = [
  { id: 0, text: 'NEXUS OS v3.1 Terminal Interface', type: 'system' },
  { id: 1, text: 'Connecting to kernel...', type: 'system' },
  { id: 2, text: 'Session established.', type: 'success' },
  { id: 3, text: "Type 'help' for available commands.", type: 'info' },
]

// ── Helpers ────────────────────────────────────────────────────────
let lineIdCounter = 0
function nextLineId(): number {
  lineIdCounter++
  return lineIdCounter
}

function formatAgentLines(agents: AgentData[]): TerminalLine[] {
  const lines: TerminalLine[] = [
    { id: nextLineId(), text: 'Registered Agents:', type: 'info' },
    { id: nextLineId(), text: '────────────────────────────────────────────────────', type: 'output' },
  ]
  agents.forEach((a) => {
    const agentStatus = a.status ?? 'offline'
    const agentRole = a.role ?? a.type ?? 'unknown'
    const agentName = a.name ?? 'unnamed'
    const trust = a.trustScore ?? 0
    const tokens = a.totalTokens ?? 0
    const statusIcon = agentStatus === 'active' || agentStatus === 'busy' ? '●' : agentStatus === 'idle' ? '○' : '✕'
    const lineType = agentStatus === 'active' || agentStatus === 'busy' ? 'success' : agentStatus === 'idle' ? 'warning' : 'error'
    lines.push({
      id: nextLineId(),
      text: `  ${statusIcon} ${agentName.padEnd(18)} ${agentRole.padEnd(14)} trust:${trust.toFixed(2)}  tok:${tokens.toLocaleString()}`,
      type: lineType,
    })
  })
  lines.push({ id: nextLineId(), text: '', type: 'output' })
  lines.push({ id: nextLineId(), text: `Total: ${agents.length} agents registered`, type: 'info' })
  return lines
}

function formatVaultLines(data: VaultData): TerminalLine[] {
  const entries = data.entries || []
  const tracks = new Map<string, number>()
  entries.forEach((e) => {
    const track = e.track ?? 'UNKNOWN'
    tracks.set(track, (tracks.get(track) || 0) + 1)
  })

  const lines: TerminalLine[] = [
    { id: nextLineId(), text: 'Vault Statistics:', type: 'info' },
    { id: nextLineId(), text: '────────────────────────────────', type: 'output' },
    { id: nextLineId(), text: `  Total Entries: ${entries.length}`, type: 'success' },
    { id: nextLineId(), text: '', type: 'output' },
    { id: nextLineId(), text: '  Tracks:', type: 'info' },
  ]
  tracks.forEach((count, track) => {
    const trackLabel = (track ?? 'UNKNOWN').padEnd(10)
    lines.push({ id: nextLineId(), text: `    ${trackLabel} ${count} entries`, type: 'output' })
  })
  lines.push({ id: nextLineId(), text: '', type: 'output' })

  if (entries.length > 0) {
    lines.push({ id: nextLineId(), text: '  Latest 5 entries:', type: 'info' })
    entries.slice(0, 5).forEach((e) => {
      const agentName = e.agent?.name ?? 'system'
      const eTrack = e.track ?? 'UNKNOWN'
      const eKey = e.key ?? 'unknown-key'
      const eValue = e.value ?? ''
      lines.push({
        id: nextLineId(),
        text: `    [${eTrack}] ${eKey} = ${eValue.slice(0, 40)}${eValue.length > 40 ? '...' : ''} (${agentName})`,
        type: 'output',
      })
    })
  }

  lines.push({ id: nextLineId(), text: '', type: 'output' })
  lines.push({ id: nextLineId(), text: 'VAP Chain: Verified ✓', type: 'success' })
  return lines
}

function formatGmrLines(data: ModelData): TerminalLine[] {
  const models = data.models || []
  const lines: TerminalLine[] = [
    { id: nextLineId(), text: 'GMR Model Registry:', type: 'info' },
    { id: nextLineId(), text: '─────────────────────────────────────────────────────', type: 'output' },
  ]

  const pools = new Map<string, typeof models>()
  models.forEach((m) => {
    const pool = m.pool ?? 'UNASSIGNED'
    if (!pools.has(pool)) pools.set(pool, [])
    pools.get(pool)!.push(m)
  })

  pools.forEach((poolModels, pool) => {
    lines.push({ id: nextLineId(), text: `  Pool: ${pool}`, type: 'info' })
    poolModels.forEach((m) => {
      const mName = m.name ?? 'unknown'
      const mHealth = m.health ?? 0
      const mLatency = m.latencyMs ?? 0
      const mCalls = m.totalCalls ?? 0
      const active = m.isActive ? '●' : '○'
      const lineType = m.isActive ? 'success' : 'warning'
      const healthBar = mHealth >= 95 ? '▓▓▓▓▓▓▓▓▓▓' :
        mHealth >= 80 ? '▓▓▓▓▓▓▓▓▓░' :
        mHealth >= 60 ? '▓▓▓▓▓▓▓░░░' : '▓▓▓▓░░░░░░'
      lines.push({
        id: nextLineId(),
        text: `    ${active} ${mName.padEnd(24)} ${healthBar} ${mHealth}%  ${mLatency}ms  calls:${mCalls}`,
        type: lineType,
      })
    })
  })

  lines.push({ id: nextLineId(), text: '', type: 'output' })
  const activeCount = models.filter((m) => m.isActive).length
  lines.push({ id: nextLineId(), text: `Total: ${models.length} models, ${activeCount} active`, type: 'info' })
  return lines
}

function formatTokenLines(data: TokenData): TerminalLine[] {
  const budget = data.budget
  const lines: TerminalLine[] = [
    { id: nextLineId(), text: 'Token Budget:', type: 'info' },
    { id: nextLineId(), text: '────────────────────────────────', type: 'output' },
  ]

  if (budget) {
    const total = budget.totalBudget ?? 0
    const used = budget.usedBudget ?? 0
    const remaining = budget.remainingBudget ?? 0
    const usedPct = total > 0 ? ((used / total) * 100).toFixed(1) : '0.0'
    const remainingPct = total > 0 ? (100 - parseFloat(usedPct)).toFixed(1) : '0.0'
    lines.push({ id: nextLineId(), text: `  Total:     ${total.toLocaleString()}`, type: 'output' })
    lines.push({ id: nextLineId(), text: `  Used:      ${used.toLocaleString()} (${usedPct}%)`, type: 'warning' })
    lines.push({ id: nextLineId(), text: `  Remaining: ${remaining.toLocaleString()} (${remainingPct}%)`, type: 'success' })
  } else {
    lines.push({ id: nextLineId(), text: '  No active budget found', type: 'error' })
  }

  lines.push({ id: nextLineId(), text: '', type: 'output' })
  lines.push({ id: nextLineId(), text: '  Per-Agent Usage:', type: 'info' })
  const agentUsage = data.agentUsage || []
  agentUsage.forEach((a) => {
    lines.push({
      id: nextLineId(),
      text: `    ${(a.name ?? 'unknown').padEnd(18)} ${(a.totalTokens ?? 0).toLocaleString()} tokens`,
      type: 'output',
    })
  })

  lines.push({ id: nextLineId(), text: '', type: 'output' })
  lines.push({ id: nextLineId(), text: 'Burn Rate: ~124 tok/min | Est. remaining: ~9.8h', type: 'warning' })
  return lines
}

// ── Component ──────────────────────────────────────────────────────
export function SystemTerminal() {
  const [lines, setLines] = useState<TerminalLine[]>([])
  const [input, setInput] = useState('')
  const [booted, setBooted] = useState(false)
  const [historyIndex, setHistoryIndex] = useState(-1)
  const commandHistory = useRef<string[]>([])
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [])

  // Boot sequence
  useEffect(() => {
    if (booted) return
    setBooted(true)

    const bootLines: TerminalLine[] = []
    BOOT_SEQUENCE.forEach((line, i) => {
      setTimeout(() => {
        setLines((prev) => [...prev, { ...line, id: nextLineId() }])
        scrollToBottom()
      }, i * 400)
    })
  }, [booted, scrollToBottom])

  // Scroll on new lines
  useEffect(() => {
    scrollToBottom()
  }, [lines, scrollToBottom])

  // Auto-focus input
  const focusInput = useCallback(() => {
    inputRef.current?.focus()
  }, [])

  // Process command
  const processCommand = useCallback(async (cmd: string) => {
    const trimmed = cmd.trim().toLowerCase()

    // Add command to output
    setLines((prev) => [...prev, { id: nextLineId(), text: `nexus@os:~$ ${cmd}`, type: 'input' }])

    // Add to history
    if (cmd.trim() && commandHistory.current[commandHistory.current.length - 1] !== cmd.trim()) {
      commandHistory.current.push(cmd.trim())
      if (commandHistory.current.length > 50) {
        commandHistory.current.shift()
      }
    }
    setHistoryIndex(-1)

    if (trimmed === 'clear') {
      setLines([])
      return
    }

    if (trimmed === 'help') {
      const helpLines = HELP_TEXT.map((h) => ({ ...h, id: nextLineId() }))
      setLines((prev) => [...prev, ...helpLines])
      return
    }

    if (trimmed === 'status') {
      setLines((prev) => [...prev, ...STATUS_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'governor') {
      setLines((prev) => [...prev, ...GOVERNOR_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'ping') {
      setLines((prev) => [...prev, ...PING_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'uptime') {
      setLines((prev) => [...prev, ...UPTIME_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'whoami') {
      setLines((prev) => [...prev, ...WHOAMI_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'ls') {
      setLines((prev) => [...prev, ...LS_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    if (trimmed === 'cat constitution') {
      setLines((prev) => [...prev, ...CONSTITUTION_LINES.map((l) => ({ ...l, id: nextLineId() }))])
      return
    }

    // Commands that fetch from API
    if (trimmed === 'agents') {
      setLines((prev) => [...prev, { id: nextLineId(), text: 'Fetching agents...', type: 'system' }])
      try {
        const res = await fetch('/api/agents')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: AgentData[] = await res.json()
        setLines((prev) => [...prev, ...formatAgentLines(data)])
      } catch {
        setLines((prev) => [...prev, { id: nextLineId(), text: 'Error: Failed to fetch agents', type: 'error' }])
      }
      return
    }

    if (trimmed === 'vault') {
      setLines((prev) => [...prev, { id: nextLineId(), text: 'Fetching vault data...', type: 'system' }])
      try {
        const res = await fetch('/api/vault')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: VaultData = await res.json()
        setLines((prev) => [...prev, ...formatVaultLines(data)])
      } catch {
        setLines((prev) => [...prev, { id: nextLineId(), text: 'Error: Failed to fetch vault data', type: 'error' }])
      }
      return
    }

    if (trimmed === 'gmr') {
      setLines((prev) => [...prev, { id: nextLineId(), text: 'Fetching GMR registry...', type: 'system' }])
      try {
        const res = await fetch('/api/models')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: ModelData = await res.json()
        setLines((prev) => [...prev, ...formatGmrLines(data)])
      } catch {
        setLines((prev) => [...prev, { id: nextLineId(), text: 'Error: Failed to fetch GMR data', type: 'error' }])
      }
      return
    }

    if (trimmed === 'tokens') {
      setLines((prev) => [...prev, { id: nextLineId(), text: 'Fetching token budget...', type: 'system' }])
      try {
        const res = await fetch('/api/tokens')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: TokenData = await res.json()
        setLines((prev) => [...prev, ...formatTokenLines(data)])
      } catch {
        setLines((prev) => [...prev, { id: nextLineId(), text: 'Error: Failed to fetch token data', type: 'error' }])
      }
      return
    }

    // Unknown command
    setLines((prev) => [
      ...prev,
      { id: nextLineId(), text: `nexus: command not found: ${trimmed}`, type: 'error' },
      { id: nextLineId(), text: "Type 'help' for available commands.", type: 'info' },
    ])
  }, [])

  // Handle key events
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = input
      setInput('')
      processCommand(cmd)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.current.length === 0) return
      const newIndex = historyIndex < commandHistory.current.length - 1 ? historyIndex + 1 : historyIndex
      setHistoryIndex(newIndex)
      setInput(commandHistory.current[commandHistory.current.length - 1 - newIndex] || '')
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex <= 0) {
        setHistoryIndex(-1)
        setInput('')
      } else {
        const newIndex = historyIndex - 1
        setHistoryIndex(newIndex)
        setInput(commandHistory.current[commandHistory.current.length - 1 - newIndex] || '')
      }
    } else if (e.key === 'Tab') {
      e.preventDefault()
      const commands = ['help', 'status', 'agents', 'vault', 'gmr', 'governor', 'tokens', 'ping', 'uptime', 'whoami', 'ls', 'cat constitution', 'clear']
      const partial = input.toLowerCase().trim()
      if (partial) {
        const match = commands.find((c) => c.startsWith(partial))
        if (match) {
          setInput(match)
        }
      }
    }
  }, [input, historyIndex, processCommand])

  // Get color class for line type
  const getLineTypeClass = (type: TerminalLine['type']): string => {
    switch (type) {
      case 'input': return 'text-zinc-300 dark:text-zinc-200'
      case 'output': return 'text-zinc-400 dark:text-zinc-500'
      case 'success': return 'text-emerald-400 dark:text-emerald-400'
      case 'warning': return 'text-yellow-400 dark:text-yellow-400'
      case 'error': return 'text-red-400 dark:text-red-400'
      case 'info': return 'text-sky-400 dark:text-sky-400'
      case 'system': return 'text-emerald-300/70 dark:text-emerald-300/70'
      default: return 'text-zinc-400'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="w-full"
    >
      <div className="rounded-xl border border-zinc-700/60 dark:border-zinc-800/80 shadow-2xl shadow-black/30 overflow-hidden bg-zinc-900 dark:bg-zinc-950">
        {/* Title bar */}
        <div className="flex items-center gap-3 border-b border-zinc-700/60 dark:border-zinc-800/80 bg-zinc-800/60 dark:bg-zinc-900/60 px-4 py-2.5">
          {/* macOS dots */}
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500 shadow-sm shadow-red-500/30" />
            <span className="h-3 w-3 rounded-full bg-yellow-500 shadow-sm shadow-yellow-500/30" />
            <span className="h-3 w-3 rounded-full bg-green-500 shadow-sm shadow-green-500/30" />
          </div>
          {/* Title */}
          <div className="flex-1 text-center">
            <span className="text-xs text-zinc-400 font-medium tracking-wide">
              NEXUS Terminal — bash
            </span>
          </div>
          {/* Terminal icon */}
          <Terminal className="h-3.5 w-3.5 text-zinc-500" />
        </div>

        {/* Terminal content */}
        <div
          ref={terminalRef}
          className="max-h-[400px] overflow-y-auto custom-scrollbar p-4 font-mono text-[12px] leading-5 cursor-text"
          onClick={focusInput}
        >
          <AnimatePresence>
            {lines.map((line) => (
              <motion.div
                key={line.id}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                className={`${getLineTypeClass(line.type)} whitespace-pre-wrap break-all ${
                  line.type === 'input' ? 'font-semibold' : ''
                }`}
              >
                {line.text || '\u00A0'}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Input line */}
          <div className="flex items-center whitespace-pre">
            <span className="text-emerald-400 font-semibold shrink-0">nexus@os</span>
            <span className="text-zinc-400">:</span>
            <span className="text-sky-400">~</span>
            <span className="text-zinc-400">$ </span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent outline-none text-zinc-200 caret-emerald-400 font-mono text-[12px]"
              autoFocus
              spellCheck={false}
              autoComplete="off"
              autoCapitalize="off"
            />
          </div>
        </div>

        {/* Footer bar */}
        <div className="flex items-center justify-between border-t border-zinc-700/60 dark:border-zinc-800/80 bg-zinc-800/40 dark:bg-zinc-900/40 px-4 py-1.5">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[9px] border-zinc-600 text-zinc-400 bg-zinc-800/50">
              bash
            </Badge>
            <Badge variant="outline" className="text-[9px] border-emerald-700/50 text-emerald-400 bg-emerald-900/20">
              ● connected
            </Badge>
          </div>
          <span className="text-[10px] text-zinc-500 tabular-nums">
            {lines.length} lines
          </span>
        </div>
      </div>
    </motion.div>
  )
}
