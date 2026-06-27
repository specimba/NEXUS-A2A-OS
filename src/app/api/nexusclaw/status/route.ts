import fs from 'fs'
import path from 'path'
import { NextRequest, NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

type ProbeStatus = 'live' | 'offline' | 'error'
type NexusClawStatus = 'operational' | 'degraded' | 'halted'
type DataSource = 'brain-api' | 'local-probe' | 'fallback'

type ProbeResult = {
  id: string
  label: string
  port: number
  expectedOwner: string
  url: string
  status: ProbeStatus
  latencyMs?: number
  statusCode?: number
  error?: string
  data?: Record<string, unknown>
}

type AgentPoolStats = {
  total: number
  online: number
  busy: number
  error: number
}

type SupervisorProfileStatus = {
  sourceId: string
  cadenceSeconds: number
  requiresBridge: boolean
  cdpPort?: number
  urlHint?: string
  active: boolean
}

type SupervisorMemoryStatus = {
  path: string
  exists: boolean
  lastAction?: string
  lastRunId?: string
  lastSourceId?: string
  lastCompletedAt?: string
  lastBlocker?: string | null
  providerCallsLastRecord?: number
}

const SUPERVISOR_PROFILES: SupervisorProfileStatus[] = [
  {
    sourceId: 'grok-project-nexus',
    cadenceSeconds: 10 * 60,
    requiresBridge: true,
    cdpPort: 9224,
    urlHint: 'https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba',
    active: true,
  },
  {
    sourceId: 'zo-computer-nexus',
    cadenceSeconds: 6 * 60 * 60,
    requiresBridge: false,
    urlHint: 'https://www.zo.computer/chats/pub_wEKDc2wQF0tGj1o0',
    active: true,
  },
  {
    sourceId: 'glm52-dashboard',
    cadenceSeconds: 6 * 60 * 60,
    requiresBridge: false,
    urlHint: 'https://chat.z.ai/c/47e59a42-06cb-442e-9b35-3e3d8d2b078f',
    active: true,
  },
  {
    sourceId: 'gpt-browser-mcp',
    cadenceSeconds: 6 * 60 * 60,
    requiresBridge: true,
    active: true,
  },
]

const SUPERVISOR_MEMORY_CANDIDATES = [
  'scratch/browser_ai_mcp_runtime/browser_ai_supervisor/grok-project-nexus.jsonl',
  'scratch/browser_ai_mcp_runtime/browser_ai_supervisor/director.jsonl',
  'scratch/browser_ai_mcp_runtime/director_memory.jsonl',
  '.codex/automations/grok-nexus-progression-cycle-hourly/memory.jsonl',
]

function readLastJsonlRecord(filePath: string): Record<string, unknown> | undefined {
  if (!fs.existsSync(filePath)) return undefined
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean)
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]) as Record<string, unknown>
    } catch {
      continue
    }
  }
  return undefined
}

function supervisorSummary() {
  const memories: SupervisorMemoryStatus[] = SUPERVISOR_MEMORY_CANDIDATES.map((relativePath) => {
    const fullPath = path.join(process.cwd(), relativePath)
    const last = readLastJsonlRecord(fullPath)
    return {
      path: relativePath,
      exists: fs.existsSync(fullPath),
      lastAction: getString(last?.action, ''),
      lastRunId: getString(last?.run_id, ''),
      lastSourceId: getString(last?.source_id, ''),
      lastCompletedAt: getString(last?.completed_at, ''),
      lastBlocker: typeof last?.blocker === 'string' ? last.blocker : null,
      providerCallsLastRecord: getNumber(last?.provider_calls),
    }
  })
  const activeMemory = memories.find((memory) => memory.exists && memory.lastAction) ?? memories.find((memory) => memory.exists)
  return {
    status: activeMemory?.lastAction ? 'memory-backed' : 'awaiting-memory',
    profiles: SUPERVISOR_PROFILES,
    memories,
    activeMemory,
    rules: {
      noopUnchangedProviderCalls: 0,
      setupBlockerProviderCalls: 0,
      maxProviderCallsPerMaterialDelta: 1,
      providerCooldownSeconds: 20 * 60,
      maxProviderCallsPerHourPerSource: 3,
    },
  }
}

const LOCAL_PROBES = [
  { id: 'brainApi', label: 'Brain API', port: 7352, expectedOwner: 'NEXUS governance / Brain API', path: '/health' },
  { id: 'modelRelayNode', label: 'Node ModelRelay', port: 7350, expectedOwner: 'Node ModelRelay primary', path: '/v1/models' },
  { id: 'browserAiBridge', label: 'Grok MCP Bridge', port: 7354, expectedOwner: 'Browser AI MCP / GROSS bridge', path: '/health' },
  { id: 'modelRelayPython', label: 'Python ModelRelay', port: 7355, expectedOwner: 'Python ModelRelay fallback/internal', path: '/health' },
  { id: 'godModeProxy', label: 'God Mode Proxy', port: 7357, expectedOwner: 'God mode proxy', path: '/health' },
]

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

async function fetchJson(url: string, timeoutMs = 1200): Promise<{ statusCode: number; data: Record<string, unknown> }> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { cache: 'no-store', signal: controller.signal })
    const text = await res.text()
    let data: Record<string, unknown> = {}
    if (text.trim()) {
      try {
        data = JSON.parse(text) as Record<string, unknown>
      } catch {
        data = { preview: text.slice(0, 240) }
      }
    }
    return { statusCode: res.status, data }
  } finally {
    clearTimeout(timeout)
  }
}

async function probeLocalService(probe: (typeof LOCAL_PROBES)[number]): Promise<ProbeResult> {
  const url = `http://127.0.0.1:${probe.port}${probe.path}`
  const started = Date.now()
  try {
    const result = await fetchJson(url)
    const latencyMs = Date.now() - started
    return {
      ...probe,
      url,
      latencyMs,
      statusCode: result.statusCode,
      status: result.statusCode >= 200 && result.statusCode < 500 ? 'live' : 'error',
      data: result.data,
    }
  } catch (error) {
    return {
      ...probe,
      url,
      status: 'offline',
      error: errorMessage(error),
    }
  }
}

function getObject(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : undefined
}

function getNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function getString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function bridgeSummary(probes: ProbeResult[]) {
  const bridge = probes.find((probe) => probe.id === 'browserAiBridge')
  const data = getObject(bridge?.data)
  const queue = getObject(data?.queue)
  const registry = getObject(data?.registry_security)
  const hardening = getObject(data?.hardening)
  const allowedHosts = Array.isArray(hardening?.allowed_hosts) ? hardening.allowed_hosts : []
  const tools = Array.isArray(data?.tools) ? data.tools : []

  return {
    status: bridge?.status ?? 'offline',
    version: getString(data?.version, 'unknown'),
    server: getString(data?.server, 'nexus-grok-bridge-v2'),
    toolCount: getNumber(data?.mcp_tool_count, tools.length),
    queue: {
      pending: getNumber(queue?.pending),
      claimed: getNumber(queue?.claimed),
      done: getNumber(queue?.done),
      failed: getNumber(queue?.failed),
    },
    registrySchemaHash: getString(registry?.registry_schema_hash, ''),
    l1RegistrySchemaHash: Boolean(registry?.l1_registry_schema_hash),
    l3OutputTaint: Boolean(registry?.l3_output_taint),
    allowedHostCount: allowedHosts.length,
    privateTargetsBlocked: Boolean(hardening?.private_targets_blocked),
  }
}

function fallbackStats(probes: ProbeResult[]): AgentPoolStats {
  const liveCount = probes.filter((probe) => probe.status === 'live').length
  const offlineCount = probes.filter((probe) => probe.status !== 'live').length
  return {
    total: probes.length,
    online: liveCount,
    busy: 0,
    error: offlineCount,
  }
}

function deriveStatus(brainApiLive: boolean, bridgeLive: boolean): NexusClawStatus {
  if (brainApiLive && bridgeLive) return 'operational'
  if (brainApiLive || bridgeLive) return 'degraded'
  return 'halted'
}

/**
 * GET /api/nexusclaw/status
 * Returns NEXUSCLAW control-plane status without pretending fallback data is live.
 */
export async function GET(_req: NextRequest) {
  try {
    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    const localProbes = await Promise.all(LOCAL_PROBES.map(probeLocalService))
    const brainProbe = localProbes.find((probe) => probe.id === 'brainApi')
    const bridgeProbe = localProbes.find((probe) => probe.id === 'browserAiBridge')
    const brainApiLive = brainProbe?.status === 'live'
    const bridgeLive = bridgeProbe?.status === 'live'

    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/nexusclaw/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json() as Record<string, unknown>
        return NextResponse.json({
          ...data,
          source: 'brain-api' satisfies DataSource,
          brainApiLive: true,
          localProbes,
          browserAiBridge: bridgeSummary(localProbes),
          browserAiSupervisor: supervisorSummary(),
          routing: {
            nexusclaw: 'governed coordinator',
            hermesGmr: 'planner/router lane',
            chimera: 'provider reconciliation lane',
            modelRelay: 'demand-driven only',
            browserAiAutomation: 'fingerprint + memory gated',
          },
          warnings: [],
          timestamp: new Date().toISOString(),
        })
      }
    } catch (pyError) {
      console.warn('Python NexusClaw status API offline; using local probes:', pyError)
    }

    const status = deriveStatus(brainApiLive, bridgeLive)
    const warnings = [
      !brainApiLive ? 'Brain API 7352 is not serving /api/nexusclaw/status; dashboard is using local probes.' : null,
      !bridgeLive ? 'Browser AI MCP bridge 7354 is offline; Grok hands are unavailable to the control center.' : null,
    ].filter(Boolean)

    return NextResponse.json({
      status,
      source: 'local-probe' satisfies DataSource,
      brainApiLive,
      stats: {
        agentPool: fallbackStats(localProbes),
        brainstorm: {
          activeSessions: bridgeLive ? 1 : 0,
          totalProposals: 0,
          pendingVotes: bridgeSummary(localProbes).queue.pending,
        },
        memoryChannels: {
          episodic: 0,
          task: bridgeSummary(localProbes).queue.pending,
          trust: 0,
        },
        trustEngine: {
          avgTrust: brainApiLive ? 0.72 : 0,
          degradedAgents: localProbes.filter((probe) => probe.status !== 'live').length,
        },
      },
      browserAiBridge: bridgeSummary(localProbes),
      browserAiSupervisor: supervisorSummary(),
      localProbes,
      routing: {
        nexusclaw: 'governed coordinator',
        hermesGmr: 'planner/router lane',
        chimera: 'provider reconciliation lane',
        modelRelay: 'demand-driven only',
        browserAiAutomation: 'fingerprint + memory gated',
      },
      controls: {
        strictPortOwnership: true,
        brainApiPort: 7352,
        browserAiBridgePort: 7354,
        broadPollingDisabled: true,
        autonomousToolExecution: false,
      },
      warnings,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('NEXUSCLAW status error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch NEXUSCLAW status', detail: errorMessage(error) },
      { status: 500 }
    )
  }
}

/**
 * POST /api/nexusclaw/intervene
 * Submit operator intervention command
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { intervention, target } = body

    if (!intervention || !target) {
      return NextResponse.json(
        { error: 'intervention and target are required' },
        { status: 400 }
      )
    }

    const apiKey = process.env.NEXUS_BRAIN_API_KEY || 'nexus-default-key'
    try {
      const res = await fetch(`${BRAIN_API_BASE}/api/nexusclaw/intervene`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
        },
        body: JSON.stringify(body),
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data)
      }
    } catch (pyError) {
      console.warn('Python NexusClaw intervene API offline, refusing fake success:', pyError)
    }

    return NextResponse.json(
      {
        success: false,
        status: 'deferred',
        message: `Intervention '${intervention}' for ${target} was not executed because Brain API intervention endpoint is unavailable.`,
      },
      { status: 202 }
    )
  } catch (error) {
    console.error('NEXUSCLAW intervention error:', error)
    return NextResponse.json(
      { error: 'Failed to submit intervention' },
      { status: 500 }
    )
  }
}
