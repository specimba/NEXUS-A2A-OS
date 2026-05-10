'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
  Terminal,
  Shield,
  Cpu,
  Network,
  Lock,
  Play,
  Square,
  Wifi,
  WifiOff,
  Activity,
  Clock,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  Globe,
  FileLock2,
  Server,
  GitPullRequest,
  ExternalLink,
  CircleDot,
  Boxes,
  Timer,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { toast } from 'sonner'

// ─── Types ────────────────────────────────────────────────────────────────────

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting'

interface GatewayHealth {
  status: ConnectionStatus
  latencyMs: number
  activeConnections: number
  idleConnections: number
  maxPoolSize: number
  lastHeartbeat: string
  uptime: string
}

interface SandboxPolicy {
  name: string
  type: 'codex' | 'opencode'
  status: 'active' | 'standby'
  restrictions: string[]
  allowedEndpoints: string[]
  deniedEndpoints: string[]
  processLimits: { label: string; value: string }[]
  specialRules: string[]
}

interface RetryPolicy {
  maxRetries: number
  initialDelayMs: number
  maxDelayMs: number
  backoffMultiplier: number
  jitterMs: number
}

interface ConnectionPoolConfig {
  minIdle: number
  maxActive: number
  idleTimeoutMs: number
  connectionTimeoutMs: number
  validationIntervalMs: number
}

interface PRStatus {
  number: number
  title: string
  status: 'open' | 'closed' | 'merged'
  description: string
  branch: string
  files: number
  additions: number
  deletions: number
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const mockGatewayHealth: GatewayHealth = {
  status: 'connected',
  latencyMs: 23,
  activeConnections: 4,
  idleConnections: 2,
  maxPoolSize: 8,
  lastHeartbeat: new Date(Date.now() - 1500).toISOString(),
  uptime: '4h 23m 17s',
}

const codexSandbox: SandboxPolicy = {
  name: 'Codex Sandbox',
  type: 'codex',
  status: 'active',
  restrictions: [
    'Read-only root filesystem (/usr, /lib, /bin mounted read-only)',
    'No write access to /etc, /var, /tmp outside sandbox workspace',
    'Process execution restricted to pre-approved binaries',
    'Inference routing enforced — no direct model API calls',
    'Memory limit: 512MB per sandbox instance',
    'CPU quota: 2 cores maximum per sandbox',
  ],
  allowedEndpoints: [
    'api.nexus-os.local/v1/inference',
    'api.nexus-os.local/v1/embeddings',
    'registry.nexus-os.local/v1/models',
  ],
  deniedEndpoints: [
    '*.amazonaws.com',
    '*.googleapis.com',
    '0.0.0.0/0 (all other egress)',
  ],
  processLimits: [
    { label: 'Max Processes', value: '64' },
    { label: 'Max Open Files', value: '256' },
    { label: 'Max Memory', value: '512MB' },
    { label: 'CPU Cores', value: '2' },
  ],
  specialRules: [
    'Inference requests must route through GMR router',
    'File writes restricted to /workspace/sandbox/ prefix',
    'Network egress requires Governor approval for new endpoints',
  ],
}

const opencodeSandbox: SandboxPolicy = {
  name: 'OpenCode Sandbox',
  type: 'opencode',
  status: 'active',
  restrictions: [
    'Landlock enforcement: FS_ACCESS_R | FS_ACCESS_W on workspace only',
    'No network egress except package registry mirrors',
    'Package allowances: numpy, pandas, scipy, scikit-learn only',
    'Process isolation via PID + network namespaces',
    'Memory limit: 1GB per sandbox instance',
    'CPU quota: 4 cores maximum per sandbox',
  ],
  allowedEndpoints: [
    'pypi-mirror.nexus-os.local/simple',
    'npm-mirror.nexus-os.local/registry',
    'api.nexus-os.local/v1/code-eval',
  ],
  deniedEndpoints: [
    '*.external.io',
    'pypi.org (direct)',
    'registry.npmjs.org (direct)',
    '0.0.0.0/0 (all other egress)',
  ],
  processLimits: [
    { label: 'Max Processes', value: '128' },
    { label: 'Max Open Files', value: '512' },
    { label: 'Max Memory', value: '1GB' },
    { label: 'CPU Cores', value: '4' },
  ],
  specialRules: [
    'Safety constraints block eval(), exec(), subprocess.Popen()',
    'Landlock LSM enforces filesystem access at kernel level',
    'Package installs verified against approved manifest hash',
  ],
}

const retryPolicy: RetryPolicy = {
  maxRetries: 5,
  initialDelayMs: 200,
  maxDelayMs: 3200,
  backoffMultiplier: 2.0,
  jitterMs: 50,
}

const connectionPoolConfig: ConnectionPoolConfig = {
  minIdle: 2,
  maxActive: 8,
  idleTimeoutMs: 30000,
  connectionTimeoutMs: 5000,
  validationIntervalMs: 10000,
}

const prStatuses: PRStatus[] = [
  {
    number: 10,
    title: 'Research OpenShell docs and create installation playbook',
    status: 'merged',
    description: 'Comprehensive installation playbook for OpenShell integration including prerequisites, environment setup, and verification steps.',
    branch: 'feat/openshell-playbook',
    files: 12,
    additions: 847,
    deletions: 23,
  },
  {
    number: 11,
    title: 'Create Codex worker sandbox policy',
    status: 'merged',
    description: 'Defines filesystem restrictions (read-only root), network egress policy, process limits, and inference routing rules for Codex workers.',
    branch: 'feat/codex-sandbox-policy',
    files: 6,
    additions: 412,
    deletions: 5,
  },
  {
    number: 12,
    title: 'Create OpenCode worker sandbox policy for OpenShell',
    status: 'open',
    description: 'Safety constraints, package allowances, landlock enforcement, and process isolation for OpenCode workers within OpenShell.',
    branch: 'feat/opencode-sandbox-policy',
    files: 8,
    additions: 563,
    deletions: 11,
  },
  {
    number: 13,
    title: 'Implement Nexus-OpenShell integration adapter',
    status: 'open',
    description: 'Gateway client with connection pooling & retry logic, sandbox lifecycle management, task execution wrapper, and GatewayResponse structured responses.',
    branch: 'feat/openshell-adapter',
    files: 18,
    additions: 1294,
    deletions: 47,
  },
]

// ─── Animation variants ───────────────────────────────────────────────────────

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as [number, number, number, number] },
  }),
}

const pulseVariants = {
  pulse: {
    scale: [1, 1.05, 1],
    transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
  },
}

// ─── Section 1: OpenShell Status Dashboard ─────────────────────────────────────

function StatusDashboard({ health, latency }: { health: GatewayHealth; latency: number[] }) {
  const statusIcon = health.status === 'connected'
    ? <Wifi className="h-5 w-5 text-emerald-400" />
    : health.status === 'connecting'
      ? <Activity className="h-5 w-5 text-yellow-400 animate-pulse" />
      : <WifiOff className="h-5 w-5 text-red-400" />

  const statusLabel = health.status.charAt(0).toUpperCase() + health.status.slice(1)
  const statusColor = health.status === 'connected'
    ? 'text-emerald-400'
    : health.status === 'connecting'
      ? 'text-yellow-400'
      : 'text-red-400'

  const badgeClass = health.status === 'connected'
    ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-emerald-600/20'
    : health.status === 'connecting'
      ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-yellow-600/20'
      : 'bg-red-600/15 text-red-600 dark:text-red-400 border-red-600/20'

  // Pool usage percentage
  const poolUsage = Math.round(((health.activeConnections + health.idleConnections) / health.maxPoolSize) * 100)

  return (
    <div className="space-y-4">
      {/* Stat Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover-lift shadow-lg">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Gateway Status</span>
                <motion.div variants={pulseVariants} animate="pulse">
                  {statusIcon}
                </motion.div>
              </div>
              <p className={`text-xl font-bold tabular-nums ${statusColor}`}>{statusLabel}</p>
              <div className="mt-1 flex items-center gap-1.5">
                <Badge className={`text-[8px] px-1.5 py-0 border-0 ${badgeClass}`}>
                  {health.status === 'connected' ? 'HEALTHY' : health.status === 'connecting' ? 'CONNECTING' : 'DOWN'}
                </Badge>
                <DataSourceBadge source="simulated" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover-lift shadow-lg">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Latency</span>
                <Timer className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="text-xl font-bold tabular-nums text-emerald-400">{health.latencyMs}<span className="text-xs text-muted-foreground ml-1">ms</span></p>
              <div className="mt-1 h-6 flex items-end gap-px">
                {latency.slice(-16).map((v, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-emerald-500/60 rounded-t-sm transition-all"
                    style={{ height: `${Math.max(10, (v / 50) * 100)}%` }}
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover-lift shadow-lg">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Connection Pool</span>
                <Boxes className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="text-xl font-bold tabular-nums">
                <span className="text-emerald-400">{health.activeConnections}</span>
                <span className="text-muted-foreground text-sm mx-1">/</span>
                <span className="text-muted-foreground text-sm">{health.maxPoolSize}</span>
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                <Progress value={poolUsage} className="h-1.5 flex-1 [&>div]:bg-emerald-500" />
                <span className="text-[9px] text-muted-foreground tabular-nums">{poolUsage}%</span>
              </div>
              <div className="mt-1 flex gap-3 text-[9px] text-muted-foreground">
                <span>Active: <span className="text-emerald-400 font-medium">{health.activeConnections}</span></span>
                <span>Idle: <span className="text-yellow-400 font-medium">{health.idleConnections}</span></span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={3} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover-lift shadow-lg">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Last Heartbeat</span>
                <Activity className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="text-xl font-bold tabular-nums text-emerald-400">
                {formatHeartbeat(health.lastHeartbeat)}
              </p>
              <div className="mt-1 flex items-center gap-2 text-[9px] text-muted-foreground">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <span>Uptime: {health.uptime}</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Gateway Health Detail */}
      <motion.div custom={4} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent shadow-lg">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-sm font-semibold">Gateway Health Detail</CardTitle>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1.5 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                onClick={() => toast.success('Gateway health check initiated', { description: 'Checking all connection endpoints...' })}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Health Check
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Endpoint', value: 'api.openshell.nexus.local', icon: Server },
                { label: 'Protocol', value: 'gRPC / TLS 1.3', icon: Lock },
                { label: 'Active Sandboxes', value: '2', icon: Cpu },
                { label: 'Queue Depth', value: '3 tasks', icon: Activity },
              ].map((item) => (
                <div key={item.label} className="rounded-lg border border-border/50 bg-muted/30 p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <item.icon className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{item.label}</span>
                  </div>
                  <p className="text-sm font-mono font-medium">{item.value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

// ─── Section 2: Worker Sandbox Policies ────────────────────────────────────────

function SandboxPolicyCard({ policy, index }: { policy: SandboxPolicy; index: number }) {
  const isCodex = policy.type === 'codex'
  const Icon = isCodex ? Shield : FileLock2

  const cardBorder = isCodex ? 'border-emerald-600/20' : 'border-cyan-600/20'
  const cardBg = isCodex
    ? 'bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent'
    : 'bg-gradient-to-br from-cyan-600/10 via-cyan-600/5 to-transparent'

  return (
    <motion.div custom={index} variants={cardVariants} initial="hidden" animate="visible">
      <Card className={`${cardBorder} ${cardBg} hover-lift shadow-lg h-full`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${isCodex ? 'bg-emerald-600/20' : 'bg-cyan-600/20'}`}>
                <Icon className={`h-4 w-4 ${isCodex ? 'text-emerald-400' : 'text-cyan-400'}`} />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold">{policy.name}</CardTitle>
                <p className="text-[10px] text-muted-foreground">PR #{isCodex ? '11' : '12'}</p>
              </div>
            </div>
            <Badge className={`text-[9px] border-0 ${
              policy.status === 'active'
                ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                : 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
            }`}>
              {policy.status === 'active' ? (
                <><CheckCircle2 className="h-2.5 w-2.5 mr-1" />ACTIVE</>
              ) : (
                <><Clock className="h-2.5 w-2.5 mr-1" />STANDBY</>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Restrictions */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Key Restrictions</p>
            <ul className="space-y-1.5">
              {policy.restrictions.slice(0, 4).map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <Lock className={`h-3 w-3 mt-0.5 shrink-0 ${isCodex ? 'text-emerald-500' : 'text-cyan-500'}`} />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>

          <Separator className="opacity-30" />

          {/* Network Policies */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Network Policies</p>
            <div className="space-y-2">
              <div>
                <p className="text-[9px] uppercase tracking-wider text-emerald-500 font-medium mb-1">Allowed Endpoints</p>
                {policy.allowedEndpoints.map((ep, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground">
                    <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500 shrink-0" />
                    {ep}
                  </div>
                ))}
              </div>
              <div>
                <p className="text-[9px] uppercase tracking-wider text-red-500 font-medium mb-1">Denied Endpoints</p>
                {policy.deniedEndpoints.map((ep, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground">
                    <XCircle className="h-2.5 w-2.5 text-red-500 shrink-0" />
                    {ep}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <Separator className="opacity-30" />

          {/* Process Limits */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Process Limits</p>
            <div className="grid grid-cols-2 gap-2">
              {policy.processLimits.map((lim) => (
                <div key={lim.label} className="rounded border border-border/50 bg-muted/30 px-2.5 py-1.5">
                  <p className="text-[9px] text-muted-foreground">{lim.label}</p>
                  <p className="text-sm font-bold tabular-nums">{lim.value}</p>
                </div>
              ))}
            </div>
          </div>

          <Separator className="opacity-30" />

          {/* Special Rules */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Special Rules</p>
            <ul className="space-y-1">
              {policy.specialRules.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-[11px] text-muted-foreground">
                  <AlertTriangle className={`h-3 w-3 mt-0.5 shrink-0 ${isCodex ? 'text-emerald-500' : 'text-cyan-500'}`} />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ─── Section 3: Integration Adapter Architecture ──────────────────────────────

function AdapterArchitecture() {
  const [activeStep, setActiveStep] = useState(0)

  const steps = [
    { label: 'Gateway Client', icon: Globe, desc: 'Connection pooling, TLS 1.3, gRPC transport' },
    { label: 'Sandbox Manager', icon: Shield, desc: 'Lifecycle management (create → run → destroy)' },
    { label: 'Task Executor', icon: Play, desc: 'Task dispatch, monitoring, result collection' },
  ]

  // Auto-cycle through steps
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [steps.length])

  return (
    <div className="space-y-4">
      {/* Adapter Flow Visualization */}
      <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent shadow-lg overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm font-semibold">Integration Adapter Flow</CardTitle>
              <DataSourceBadge source="mock" className="ml-auto" />
            </div>
          </CardHeader>
          <CardContent>
            {/* Flow Diagram */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-2 md:gap-0 py-4">
              {steps.map((step, i) => {
                const isActive = activeStep === i
                const StepIcon = step.icon
                return (
                  <div key={step.label} className="flex items-center gap-2 md:gap-0">
                    <motion.div
                      className={`flex flex-col items-center gap-2 rounded-xl border px-6 py-4 transition-all duration-300 ${
                        isActive
                          ? 'border-emerald-500/50 bg-emerald-600/15 shadow-lg shadow-emerald-600/10'
                          : 'border-border/50 bg-muted/20'
                      }`}
                      animate={isActive ? { scale: [1, 1.03, 1] } : { scale: 1 }}
                      transition={{ duration: 0.6, repeat: isActive ? Infinity : 0, ease: 'easeInOut' }}
                    >
                      <StepIcon className={`h-6 w-6 ${isActive ? 'text-emerald-400' : 'text-muted-foreground'}`} />
                      <span className={`text-xs font-medium ${isActive ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                        {step.label}
                      </span>
                      <span className="text-[9px] text-muted-foreground text-center max-w-[160px]">{step.desc}</span>
                    </motion.div>
                    {i < steps.length - 1 && (
                      <div className="hidden md:flex items-center px-2">
                        <div className="w-12 h-0.5 data-flow-line-h" />
                        <ArrowRight className="h-4 w-4 text-emerald-400/60 -ml-1" />
                      </div>
                    )}
                    {i < steps.length - 1 && (
                      <div className="md:hidden flex items-center py-1">
                        <ArrowRight className="h-4 w-4 text-emerald-400/60 rotate-90" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* GatewayResponse format */}
            <div className="mt-4 rounded-lg border border-emerald-600/20 bg-muted/30 p-3">
              <p className="text-[10px] uppercase tracking-wider text-emerald-500 font-medium mb-2">GatewayResponse Structure</p>
              <pre className="text-[11px] font-mono text-muted-foreground leading-relaxed overflow-x-auto custom-scrollbar">
{`{
  "status": "success" | "error" | "timeout",
  "data": T,
  "metadata": {
    "request_id": "uuid",
    "sandbox_id": "sbx-xxxxx",
    "latency_ms": 23,
    "retry_count": 0
  },
  "error": null | {
    "code": "string",
    "message": "string",
    "recoverable": boolean
  }
}`}
              </pre>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Config Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Retry Policy */}
        <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent shadow-lg h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-sm font-semibold">Retry Policy</CardTitle>
                <Badge className="text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 ml-auto">EXPONENTIAL</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: 'Max Retries', value: retryPolicy.maxRetries.toString(), desc: 'Maximum attempt count before failing' },
                { label: 'Initial Delay', value: `${retryPolicy.initialDelayMs}ms`, desc: 'First retry delay' },
                { label: 'Max Delay', value: `${retryPolicy.maxDelayMs}ms`, desc: 'Cap on exponential growth' },
                { label: 'Backoff Multiplier', value: `${retryPolicy.backoffMultiplier}x`, desc: 'Exponential growth factor' },
                { label: 'Jitter', value: `±${retryPolicy.jitterMs}ms`, desc: 'Random jitter to prevent thundering herd' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-3 py-2">
                  <div>
                    <p className="text-xs font-medium">{item.label}</p>
                    <p className="text-[9px] text-muted-foreground">{item.desc}</p>
                  </div>
                  <span className="text-sm font-bold tabular-nums text-emerald-400 font-mono">{item.value}</span>
                </div>
              ))}

              {/* Backoff visualization */}
              <div className="mt-2">
                <p className="text-[9px] uppercase tracking-wider text-muted-foreground mb-1.5">Backoff Sequence</p>
                <div className="flex items-end gap-1.5 h-12">
                  {Array.from({ length: retryPolicy.maxRetries }, (_, i) => {
                    const delay = Math.min(retryPolicy.initialDelayMs * Math.pow(retryPolicy.backoffMultiplier, i), retryPolicy.maxDelayMs)
                    const height = (delay / retryPolicy.maxDelayMs) * 100
                    return (
                      <div key={i} className="flex flex-col items-center gap-1 flex-1">
                        <div
                          className="w-full rounded-t bg-emerald-500/60 transition-all"
                          style={{ height: `${Math.max(8, height)}%` }}
                        />
                        <span className="text-[8px] text-muted-foreground tabular-nums">{Math.round(delay)}ms</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Connection Pool Settings */}
        <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent shadow-lg h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-sm font-semibold">Connection Pool Settings</CardTitle>
                <Badge className="text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 ml-auto">gRPC</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: 'Min Idle', value: connectionPoolConfig.minIdle.toString(), desc: 'Minimum idle connections maintained' },
                { label: 'Max Active', value: connectionPoolConfig.maxActive.toString(), desc: 'Maximum concurrent connections' },
                { label: 'Idle Timeout', value: `${connectionPoolConfig.idleTimeoutMs / 1000}s`, desc: 'Time before idle connections are closed' },
                { label: 'Connect Timeout', value: `${connectionPoolConfig.connectionTimeoutMs / 1000}s`, desc: 'Timeout for establishing new connections' },
                { label: 'Validation Interval', value: `${connectionPoolConfig.validationIntervalMs / 1000}s`, desc: 'Health check interval for pool connections' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-3 py-2">
                  <div>
                    <p className="text-xs font-medium">{item.label}</p>
                    <p className="text-[9px] text-muted-foreground">{item.desc}</p>
                  </div>
                  <span className="text-sm font-bold tabular-nums text-emerald-400 font-mono">{item.value}</span>
                </div>
              ))}

              {/* Pool visualization */}
              <div className="mt-2">
                <p className="text-[9px] uppercase tracking-wider text-muted-foreground mb-1.5">Pool Utilization</p>
                <div className="flex gap-1.5">
                  {Array.from({ length: connectionPoolConfig.maxActive }, (_, i) => (
                    <div
                      key={i}
                      className={`flex-1 h-6 rounded transition-all ${
                        i < mockGatewayHealth.activeConnections
                          ? 'bg-emerald-500/70 shadow-sm shadow-emerald-500/30'
                          : i < mockGatewayHealth.activeConnections + mockGatewayHealth.idleConnections
                            ? 'bg-yellow-500/40'
                            : 'bg-muted/30 border border-border/30'
                      }`}
                      title={
                        i < mockGatewayHealth.activeConnections
                          ? 'Active'
                          : i < mockGatewayHealth.activeConnections + mockGatewayHealth.idleConnections
                            ? 'Idle'
                            : 'Available'
                      }
                    />
                  ))}
                </div>
                <div className="mt-1.5 flex gap-3 text-[9px] text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded bg-emerald-500/70" />Active</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded bg-yellow-500/40" />Idle</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded bg-muted/30 border border-border/30" />Available</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

// ─── Section 4: Integration PRs Status ─────────────────────────────────────────

function PRStatusSection() {
  const prStatusIcon = (status: string) => {
    if (status === 'merged') return <CheckCircle2 className="h-3.5 w-3.5 text-purple-400" />
    if (status === 'open') return <CircleDot className="h-3.5 w-3.5 text-emerald-400" />
    return <XCircle className="h-3.5 w-3.5 text-red-400" />
  }

  const prBadgeClass = (status: string) => {
    if (status === 'merged') return 'bg-purple-600/15 text-purple-600 dark:text-purple-400 border-purple-600/20'
    if (status === 'open') return 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-emerald-600/20'
    return 'bg-red-600/15 text-red-600 dark:text-red-400 border-red-600/20'
  }

  return (
    <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible">
      <Card className="border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitPullRequest className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm font-semibold">Integration PRs Status</CardTitle>
              <Badge className="text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0">
                nexusalpha
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`text-[9px] border-0 ${prBadgeClass('merged')}`}>{prStatuses.filter(p => p.status === 'merged').length} merged</Badge>
              <Badge className={`text-[9px] border-0 ${prBadgeClass('open')}`}>{prStatuses.filter(p => p.status === 'open').length} open</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {prStatuses.map((pr, i) => (
              <motion.div
                key={pr.number}
                custom={i + 1}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                className={`rounded-lg border p-4 transition-all hover:border-emerald-600/30 ${
                  pr.status === 'merged'
                    ? 'border-purple-600/20 bg-gradient-to-r from-purple-600/5 via-transparent to-transparent'
                    : 'border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      {prStatusIcon(pr.status)}
                      <span className="text-xs font-mono font-bold text-muted-foreground">#{pr.number}</span>
                      <span className="text-sm font-medium truncate">{pr.title}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed mb-2">{pr.description}</p>
                    <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1 font-mono">
                        <GitPullRequest className="h-3 w-3" />{pr.branch}
                      </span>
                      <Separator orientation="vertical" className="h-3" />
                      <span className="text-emerald-500">+{pr.additions}</span>
                      <span className="text-red-500">-{pr.deletions}</span>
                      <Separator orientation="vertical" className="h-3" />
                      <span>{pr.files} files</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <Badge className={`text-[9px] border-0 ${prBadgeClass(pr.status)}`}>
                      {prStatusIcon(pr.status)}
                      <span className="ml-1">{pr.status.toUpperCase()}</span>
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 gap-1 text-[10px] text-muted-foreground hover:text-emerald-400"
                      onClick={() => toast.info(`Opening PR #${pr.number}`, { description: `nexusalpha/openshell-integration#${pr.number}` })}
                    >
                      <ExternalLink className="h-3 w-3" />
                      View
                    </Button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ─── Helper ────────────────────────────────────────────────────────────────────

function formatHeartbeat(iso: string): string {
  const now = Date.now()
  const then = new Date(iso).getTime()
  const diffMs = now - then
  if (diffMs < 1000) return 'just now'
  if (diffMs < 60000) return `${Math.floor(diffMs / 1000)}s ago`
  return `${Math.floor(diffMs / 60000)}m ago`
}

// ─── Main Component ────────────────────────────────────────────────────────────

export function OpenshellTab() {
  const [gatewayHealth, setGatewayHealth] = useState<GatewayHealth>(mockGatewayHealth)

  // Simulate live latency updates
  const latencyData = useMemo(() => {
    const base = 23
    return Array.from({ length: 32 }, (_, i) => base + Math.sin(i * 0.4) * 8 + (i % 3 === 0 ? 5 : -2))
  }, [])

  // Simulate heartbeat updates
  useEffect(() => {
    const interval = setInterval(() => {
      setGatewayHealth((prev) => ({
        ...prev,
        latencyMs: Math.max(12, Math.min(45, prev.latencyMs + (Math.random() > 0.5 ? 1 : -1) * Math.floor(Math.random() * 4))),
        lastHeartbeat: new Date().toISOString(),
        activeConnections: Math.max(2, Math.min(6, prev.activeConnections + (Math.random() > 0.7 ? (Math.random() > 0.5 ? 1 : -1) : 0))),
      }))
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-600/20">
            <Terminal className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight">
              OpenShell <span className="text-gradient-emerald">Integration</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              Nexus-OpenShell adapter · Gateway client · Sandbox policies · Task execution
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0">
            <Terminal className="h-2.5 w-2.5 mr-1" />
            OPENSHELL
          </Badge>
          <DataSourceBadge source="simulated" />
        </div>
      </div>

      {/* Section 1: OpenShell Status Dashboard */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Wifi className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold">Status Dashboard</h3>
        </div>
        <StatusDashboard health={gatewayHealth} latency={latencyData} />
      </section>

      {/* Section 2: Worker Sandbox Policies */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold">Worker Sandbox Policies</h3>
          <Badge className="text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0">
            PR #11 & #12
          </Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SandboxPolicyCard policy={codexSandbox} index={0} />
          <SandboxPolicyCard policy={opencodeSandbox} index={1} />
        </div>
      </section>

      {/* Section 3: Integration Adapter Architecture */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold">Integration Adapter Architecture</h3>
          <Badge className="text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0">
            PR #13
          </Badge>
        </div>
        <AdapterArchitecture />
      </section>

      {/* Section 4: Integration PRs Status */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <GitPullRequest className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold">nexusalpha Repository PRs</h3>
        </div>
        <PRStatusSection />
      </section>
    </div>
  )
}
