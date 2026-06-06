import { createServer } from 'http'
import { Server } from 'socket.io'

const httpServer = createServer()
const io = new Server(httpServer, {
  // DO NOT change the path, it is used by Caddy to forward the request to the correct port
  path: '/',
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
  pingTimeout: 60000,
  pingInterval: 25000,
})

// ─── Configuration ───────────────────────────────────────────────────

const API_BASE = 'http://localhost:3000/api'
const POLL_INTERVAL_MS = 4000  // How often we poll the main app for fresh data
const VAULT_POLL_INTERVAL_MS = 5000
const METRICS_POLL_INTERVAL_MS = 5000
const WORKER_POLL_INTERVAL_MS = 3000

// ─── State tracking ─────────────────────────────────────────────────

let lastSeenVaultEntryId: string | null = null
let usingSyntheticFallback = false
let connectedClients = 0

// Cache for latest real data
let cachedWorkers: RealWorker[] = []
let cachedStats: SwarmStats | null = null
let cachedVaultEntries: VaultEntryItem[] = []

// ─── Types ───────────────────────────────────────────────────────────

interface RealWorker {
  id: string
  name: string
  type: string
  status: string
  domain: string | null
  trustScore: number
  totalTokens: number
  tasksDone: number
  tasksFailed: number
  lastActive: string
  recentActivity: number
}

interface SwarmStats {
  totalWorkers: number
  busyWorkers: number
  idleWorkers: number
  errorWorkers: number
  offlineWorkers: number
  totalTasks: number
  avgTrust: number
}

interface VaultEntryItem {
  id: string
  agentId: string
  track: string
  category: string
  key: string
  value: string
  score: number
  createdAt: string
  agent: { name: string }
}

// ─── Synthetic data pools (fallback) ─────────────────────────────────

const WORKER_IDS = ['worker-1', 'worker-2', 'worker-3', 'worker-4', 'worker-5', 'worker-6']
const WORKER_STATUSES: Array<'busy' | 'idle' | 'error'> = ['busy', 'idle', 'error']
const TASKS = [
  'benchmark-ISC-007',
  'research-arxiv-2401.12345',
  'audit-trust-score-worker-3',
  'gmr-rotation-trinity-large',
  'vault-entry-V-2048',
  'governor-decision-D-0892',
  'swarm-rebalance-pool',
  'stresslab-run-ISC-012',
  'token-budget-analysis',
  'paper-summarize-P-003',
  'model-health-check',
  'failover-gemma-to-nemotron',
]
const DOMAINS = ['security', 'reasoning', 'math', 'code', 'multilingual', 'knowledge']
const PRIORITIES: Array<'high' | 'medium' | 'low'> = ['high', 'medium', 'low']
const SUBMITTERS = ['governor', 'coordinator', 'research-agent', 'worker-1', 'operator']
const SOURCES = ['Bridge', 'Engine', 'Governor', 'Vault', 'GMR', 'Swarm', 'Monitor', 'Config']
const ACTIVITY_TYPES: Array<'info' | 'success' | 'warning' | 'error'> = ['info', 'success', 'warning', 'error']
const ACTIVITY_MESSAGES: Record<string, string[]> = {
  info: [
    'Swarm health check completed — all workers nominal',
    'GMR pool rotation scheduled for next cycle',
    'New vault entry committed to TRUST track',
    'Coordinator dispatched batch research queries',
    'System configuration backup completed',
    'Bridge relay latency: 12ms (normal range)',
    'Monitor: No anomalies detected in last 5 min',
  ],
  success: [
    'Worker-3 completed benchmark-ISC-007 in 4.2s',
    'Governor approved trust threshold adjustment',
    'StressLab test ISC-012 passed all assertions',
    'GMR failover to trinity-large successful',
    'Paper P-003 summarized and queued for review',
    'Vault integrity check passed — 1792 entries verified',
    'Swarm rebalance completed — utilization at 87%',
  ],
  warning: [
    'Token budget at 68% — 4h 12m remaining at current rate',
    'Worker-5 approaching rate limit (429 responses detected)',
    'gemma-fast health degraded to 82% — monitoring',
    'Governor: Agent coordinator trust score near lane threshold',
    'Vault entry V-2045 score below 0.5 — flagged for review',
    'GMR rotation log shows unusual frequency for kimi-k2.5',
    'Monitor: Slight memory pressure on worker-2',
  ],
  error: [
    'Worker-4 encountered E-RATE-429 — task reassigned',
    'GMR failover from dolphin-mistral failed — retrying',
    'Vault commit conflict on entry V-2050 — resolution pending',
    'Governor blocked action: trust score below CRIT threshold',
    'StressLab test ISC-009 failed — assertion mismatch on line 42',
    'Bridge relay timeout — upstream unresponsive for 8s',
    'Swarm: Worker-6 unresponsive — heartbeat missed',
  ],
}

// ─── Utility functions ───────────────────────────────────────────────

const pick = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)]
const randInt = (min: number, max: number): number => Math.floor(Math.random() * (max - min + 1)) + min
const randFloat = (min: number, max: number, decimals = 1): number =>
  parseFloat((Math.random() * (max - min) + min).toFixed(decimals))
const genId = (prefix: string): string => `${prefix}-${String(Math.floor(Math.random() * 9000) + 1000)}`

// ─── API fetch helper with error handling ────────────────────────────

async function safeFetch<T>(url: string, options?: RequestInit): Promise<T | null> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)

    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    })
    clearTimeout(timeout)

    if (!res.ok) {
      console.warn(`[NEXUS Swarm WS] API returned ${res.status} for ${url}`)
      return null
    }

    const data = await res.json()

    // If we got here, the main app is running — clear synthetic fallback flag
    if (usingSyntheticFallback) {
      console.log('[NEXUS Swarm WS] ✅ Main app recovered — switching back to real data')
      usingSyntheticFallback = false
    }

    return data as T
  } catch (err: any) {
    if (!usingSyntheticFallback) {
      console.warn(`[NEXUS Swarm WS] ⚠️ API fetch failed for ${url}: ${err?.message || err}. Using synthetic fallback.`)
      usingSyntheticFallback = true
    }
    return null
  }
}

// ─── Real data fetching ──────────────────────────────────────────────

interface SwarmGetResponse {
  workers: RealWorker[]
  stats: SwarmStats
}

interface VaultGetResponse {
  entries: VaultEntryItem[]
}

async function fetchSwarmState(): Promise<SwarmGetResponse | null> {
  const data = await safeFetch<SwarmGetResponse>(`${API_BASE}/swarm`)
  if (data && data.workers) {
    cachedWorkers = data.workers
    cachedStats = data.stats
  }
  return data
}

async function fetchVaultEntries(): Promise<VaultEntryItem[]> {
  const data = await safeFetch<VaultGetResponse>(`${API_BASE}/vault`)
  if (data && data.entries) {
    cachedVaultEntries = data.entries
    return data.entries
  }
  return []
}

async function reassignTaskViaApi(workerId: string, newDomain?: string, newTask?: string) {
  return safeFetch<{ worker: RealWorker; message: string }>(`${API_BASE}/swarm`, {
    method: 'POST',
    body: JSON.stringify({
      action: 'reassign_task',
      workerId,
      newDomain,
      newTask,
    }),
  })
}

// ─── Synthetic event generators (unchanged, for fallback) ────────────

function generateSyntheticWorkerUpdate() {
  const workerId = pick(WORKER_IDS)
  const status = pick(WORKER_STATUSES)
  const task = status === 'busy' ? pick(TASKS) : status === 'error' ? pick(TASKS) : null
  const progress = status === 'busy' ? randInt(10, 95) : status === 'error' ? randInt(0, 60) : 0
  const tokens = randInt(50, 8000)
  return { workerId, status, task, progress, tokens }
}

function generateSyntheticTaskComplete() {
  return {
    taskId: genId('T'),
    workerId: pick(WORKER_IDS),
    result: pick(['success', 'success', 'success', 'failure'] as const),
    duration: `${randFloat(0.8, 12.5)}s`,
    tokens: randInt(200, 6000),
  }
}

function generateSyntheticTaskQueued() {
  return {
    taskId: genId('T'),
    domain: pick(DOMAINS),
    priority: pick(PRIORITIES),
    submittedBy: pick(SUBMITTERS),
  }
}

function generateSyntheticMetrics() {
  return {
    throughput: randFloat(8, 45),
    avgDuration: randFloat(1.2, 8.5),
    successRate: randFloat(0.82, 0.99, 2),
    utilization: randFloat(0.55, 0.95, 2),
    totalTokens: randInt(150000, 420000),
  }
}

function generateSyntheticActivity() {
  const type = pick(ACTIVITY_TYPES)
  return {
    type,
    source: pick(SOURCES),
    message: pick(ACTIVITY_MESSAGES[type]),
    timestamp: Date.now(),
  }
}

// ─── Real event builders ─────────────────────────────────────────────

function buildWorkerUpdateFromReal(worker: RealWorker) {
  // Map agent status to worker status (frontend expects 'busy' | 'idle' | 'error')
  let status: 'busy' | 'idle' | 'error' = 'idle'
  if (worker.status === 'busy') status = 'busy'
  else if (worker.status === 'error') status = 'error'
  else if (worker.status === 'offline') status = 'idle'  // Treat offline as idle visually

  return {
    workerId: worker.id,
    status,
    task: status === 'busy' ? `${worker.domain || 'general'}-task-${worker.tasksDone + 1}` : null,
    progress: status === 'busy' ? Math.min(95, Math.max(10, Math.round(worker.trustScore * 100))) : 0,
    tokens: worker.totalTokens,
    domain: worker.domain,
  }
}

function buildMetricsFromReal(workers: RealWorker[], stats: SwarmStats) {
  const totalWorkers = stats.totalWorkers || workers.length || 1
  const totalTasksDone = workers.reduce((s, w) => s + w.tasksDone, 0)
  const totalTasksFailed = workers.reduce((s, w) => s + w.tasksFailed, 0)
  const totalTokens = workers.reduce((s, w) => s + w.totalTokens, 0)
  const totalTasksAll = totalTasksDone + totalTasksFailed
  const successRate = totalTasksAll > 0
    ? parseFloat((totalTasksDone / totalTasksAll).toFixed(2))
    : 0.95

  // Throughput: tasks per minute (approximate from tasks done)
  // Assume ~10 min uptime per session for estimation
  const throughput = parseFloat((totalTasksDone / 10).toFixed(1))

  // Utilization: fraction of workers that are busy
  const busyCount = workers.filter(w => w.status === 'busy').length
  const utilization = totalWorkers > 0
    ? parseFloat((busyCount / totalWorkers).toFixed(2))
    : 0.5

  // Average duration: estimate from trust scores (higher trust → faster completion)
  const avgTrust = workers.length > 0
    ? workers.reduce((s, w) => s + w.trustScore, 0) / workers.length
    : 0.5
  const avgDuration = parseFloat((8.5 - avgTrust * 6).toFixed(1)) // Higher trust → lower duration

  return {
    throughput: Math.max(0.1, throughput),
    avgDuration: Math.max(0.5, avgDuration),
    successRate: Math.max(0.1, Math.min(1.0, successRate)),
    utilization: Math.max(0.0, Math.min(1.0, utilization)),
    totalTokens,
  }
}

const TRACK_TO_ACTIVITY_TYPE: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
  FAIL: 'error',
  GOV: 'info',
  TRUST: 'success',
  CAP: 'warning',
  EVENT: 'info',
}

const TRACK_TO_SOURCE: Record<string, string> = {
  FAIL: 'Engine',
  GOV: 'Governor',
  TRUST: 'Vault',
  CAP: 'Swarm',
  EVENT: 'Monitor',
}

function buildActivityFromVaultEntry(entry: VaultEntryItem) {
  const track = entry.track.toUpperCase()
  const type = TRACK_TO_ACTIVITY_TYPE[track] || 'info'
  const source = TRACK_TO_SOURCE[track] || 'System'
  const agentName = entry.agent?.name || 'unknown'

  // Build a descriptive message from the vault entry
  let message: string
  try {
    const parsed = JSON.parse(entry.value)
    // Use the key as the basis for the message
    const keyParts = entry.key.split(':')
    const action = keyParts[0] || entry.category
    const detail = parsed.task || parsed.from ? JSON.stringify(parsed) : entry.key
    message = `[${agentName}] ${entry.category}: ${detail}`
  } catch {
    message = `[${agentName}] ${entry.category}: ${entry.key}`
  }

  return {
    type,
    source,
    message,
    timestamp: new Date(entry.createdAt).getTime(),
  }
}

// ─── Connection handling ─────────────────────────────────────────────

io.on('connection', (socket) => {
  connectedClients++
  console.log(`[NEXUS Swarm WS] Client connected: ${socket.id} (${connectedClients} total)`)

  // Emit initial worker state for all real workers on connection
  if (cachedWorkers.length > 0) {
    for (const worker of cachedWorkers) {
      socket.emit('swarm:worker-update', buildWorkerUpdateFromReal(worker))
    }
    // Also send current metrics
    if (cachedStats) {
      socket.emit('swarm:metrics', buildMetricsFromReal(cachedWorkers, cachedStats))
    }
    console.log(`[NEXUS Swarm WS] Sent initial state for ${cachedWorkers.length} real workers to ${socket.id}`)
  }

  // Handle task assignment from client
  socket.on('swarm:assign-task', async (data: { taskId: string; workerId: string }) => {
    console.log(`[NEXUS Swarm WS] Task assignment: ${data.taskId} → ${data.workerId}`)

    // Try to reassign via API
    const result = await reassignTaskViaApi(data.workerId, undefined, data.taskId)

    if (result) {
      // Real reassignment succeeded
      const updatedWorker = result.worker

      // Emit confirmation back to the sender
      socket.emit('swarm:assign-confirmed', {
        taskId: data.taskId,
        workerId: data.workerId,
        status: 'assigned',
        timestamp: Date.now(),
      })

      // Broadcast the worker update to all clients with real data
      io.emit('swarm:worker-update', buildWorkerUpdateFromReal(updatedWorker))

      // Broadcast activity
      io.emit('nexus:activity', {
        type: 'info' as const,
        source: 'Swarm',
        message: result.message || `Task ${data.taskId} assigned to ${updatedWorker.name}`,
        timestamp: Date.now(),
      })
    } else {
      // Fallback: synthetic confirmation
      socket.emit('swarm:assign-confirmed', {
        taskId: data.taskId,
        workerId: data.workerId,
        status: 'assigned',
        timestamp: Date.now(),
      })

      io.emit('swarm:worker-update', {
        workerId: data.workerId,
        status: 'busy',
        task: data.taskId,
        progress: 0,
        tokens: 0,
      })

      io.emit('nexus:activity', {
        type: 'info',
        source: 'Swarm',
        message: `Task ${data.taskId} assigned to ${data.workerId} (synthetic)`,
        timestamp: Date.now(),
      })
    }
  })

  socket.on('disconnect', (reason) => {
    connectedClients--
    console.log(`[NEXUS Swarm WS] Client disconnected: ${socket.id} (${reason}) (${connectedClients} remaining)`)
  })

  socket.on('error', (error) => {
    console.error(`[NEXUS Swarm WS] Socket error (${socket.id}):`, error)
  })
})

// ─── Periodic: Worker state polling ──────────────────────────────────

let workerPollTimer: ReturnType<typeof setTimeout> | null = null
let previousWorkerStatuses: Record<string, string> = {}

async function pollAndEmitWorkerUpdates() {
  const swarmData = await fetchSwarmState()

  if (swarmData && swarmData.workers.length > 0) {
    // Emit updates for workers whose status changed, or all if this is first poll
    const hasPrevious = Object.keys(previousWorkerStatuses).length > 0

    for (const worker of swarmData.workers) {
      const previousStatus = previousWorkerStatuses[worker.id]
      // Emit if status changed, or always emit for busy workers (progress updates), or if no previous state
      if (!hasPrevious || previousStatus !== worker.status || worker.status === 'busy') {
        io.emit('swarm:worker-update', buildWorkerUpdateFromReal(worker))
      }
      previousWorkerStatuses[worker.id] = worker.status
    }

    // Emit real metrics
    io.emit('swarm:metrics', buildMetricsFromReal(swarmData.workers, swarmData.stats))
  } else if (usingSyntheticFallback) {
    // Fall back to synthetic worker updates
    io.emit('swarm:worker-update', generateSyntheticWorkerUpdate())
  }
}

function scheduleWorkerPoll() {
  workerPollTimer = setTimeout(async () => {
    await pollAndEmitWorkerUpdates()
    scheduleWorkerPoll()
  }, WORKER_POLL_INTERVAL_MS)
}
scheduleWorkerPoll()

// ─── Periodic: Vault activity feed ───────────────────────────────────

let vaultPollTimer: ReturnType<typeof setTimeout> | null = null
let lastVaultPollTime: number = 0

async function pollAndEmitVaultActivities() {
  const entries = await fetchVaultEntries()

  if (entries.length > 0) {
    // Determine which entries are new since last poll
    const newestEntry = entries[0] // Already sorted desc by createdAt

    // Initialize lastSeenVaultEntryId on first poll
    if (!lastSeenVaultEntryId) {
      lastSeenVaultEntryId = newestEntry.id
      lastVaultPollTime = new Date(newestEntry.createdAt).getTime()
      console.log(`[NEXUS Swarm WS] Initialized vault tracking from entry ${lastSeenVaultEntryId}`)
      return
    }

    // Find entries newer than what we've seen
    const newEntries = entries.filter(e => {
      const entryTime = new Date(e.createdAt).getTime()
      return entryTime > lastVaultPollTime
    })

    // Emit activities for new vault entries (in chronological order)
    if (newEntries.length > 0) {
      // Sort oldest first so they appear in order
      const sorted = [...newEntries].sort((a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
      )

      for (const entry of sorted) {
        io.emit('nexus:activity', buildActivityFromVaultEntry(entry))
      }

      // Update our cursor
      lastVaultPollTime = new Date(newestEntry.createdAt).getTime()
      lastSeenVaultEntryId = newestEntry.id

      if (sorted.length > 0) {
        console.log(`[NEXUS Swarm WS] Emitted ${sorted.length} vault activity events`)
      }
    }
  } else if (usingSyntheticFallback) {
    // Fall back to synthetic activity
    io.emit('nexus:activity', generateSyntheticActivity())
  }
}

function scheduleVaultPoll() {
  vaultPollTimer = setTimeout(async () => {
    await pollAndEmitVaultActivities()
    scheduleVaultPoll()
  }, VAULT_POLL_INTERVAL_MS)
}
scheduleVaultPoll()

// ─── Periodic: Task completion events (from real + synthetic blend) ──

let taskCompleteTimer: ReturnType<typeof setTimeout> | null = null

async function pollAndEmitTaskCompletions() {
  // Check for recently completed governance tasks
  if (cachedWorkers.length > 0) {
    // Find workers that have tasks done (simulate task completion from real data)
    const busyWorkers = cachedWorkers.filter(w => w.status === 'busy' && w.tasksDone > 0)
    if (busyWorkers.length > 0 && Math.random() < 0.4) {
      // Occasionally emit a task completion based on real worker data
      const worker = pick(busyWorkers)
      io.emit('swarm:task-complete', {
        taskId: `T-${worker.tasksDone}`,
        workerId: worker.id,
        result: (Math.random() > 0.2 ? 'success' : 'failure') as 'success' | 'failure',
        duration: `${randFloat(1.2, 8.5)}s`,
        tokens: randInt(200, Math.max(201, worker.totalTokens)),
      })
      return
    }
  }

  // Fallback: synthetic task completion
  if (usingSyntheticFallback || cachedWorkers.length === 0) {
    io.emit('swarm:task-complete', generateSyntheticTaskComplete())
  }
}

function scheduleTaskComplete() {
  const delay = randInt(5000, 8000)
  taskCompleteTimer = setTimeout(async () => {
    await pollAndEmitTaskCompletions()
    scheduleTaskComplete()
  }, delay)
}
scheduleTaskComplete()

// ─── Periodic: Task queued events ────────────────────────────────────

let taskQueuedTimer: ReturnType<typeof setTimeout> | null = null

function scheduleTaskQueued() {
  const delay = randInt(4000, 7000)
  taskQueuedTimer = setTimeout(() => {
    if (usingSyntheticFallback) {
      // Full synthetic when main app is down
      io.emit('swarm:task-queued', generateSyntheticTaskQueued())
    } else if (cachedWorkers.length > 0) {
      // Blend: use real domains from workers, generate a plausible task
      const domain = pick(cachedWorkers.map(w => w.domain || 'general').filter(Boolean))
      io.emit('swarm:task-queued', {
        taskId: genId('T'),
        domain,
        priority: pick(PRIORITIES),
        submittedBy: pick(['governor', 'coordinator', 'operator']),
      })
    } else {
      // No real workers yet, use synthetic
      io.emit('swarm:task-queued', generateSyntheticTaskQueued())
    }
    scheduleTaskQueued()
  }, delay)
}
scheduleTaskQueued()

// ─── Periodic: Metrics (supplementary, for real-time feel) ───────────

let metricsTimer: ReturnType<typeof setTimeout> | null = null

function scheduleMetrics() {
  const delay = randInt(3000, 5000)
  metricsTimer = setTimeout(() => {
    if (usingSyntheticFallback || cachedWorkers.length === 0) {
      io.emit('swarm:metrics', generateSyntheticMetrics())
    }
    // If we have real data, metrics are already emitted by the worker poll
    // So we only emit synthetic metrics here when in fallback mode
    scheduleMetrics()
  }, delay)
}
scheduleMetrics()

// ─── Periodic: Synthetic activity fallback ───────────────────────────

let activityTimer: ReturnType<typeof setTimeout> | null = null

function scheduleActivity() {
  const delay = randInt(3000, 5000)
  activityTimer = setTimeout(() => {
    // Only emit synthetic activity when main app is down
    // (Real activities come from vault polling)
    if (usingSyntheticFallback) {
      io.emit('nexus:activity', generateSyntheticActivity())
    }
    scheduleActivity()
  }, delay)
}
scheduleActivity()

// ─── Initial data load ───────────────────────────────────────────────

async function initialLoad() {
  console.log('[NEXUS Swarm WS] Loading initial data from main app...')
  await fetchSwarmState()
  await fetchVaultEntries()

  if (cachedWorkers.length > 0) {
    console.log(`[NEXUS Swarm WS] ✅ Loaded ${cachedWorkers.length} real workers from DB`)
  } else {
    console.log('[NEXUS Swarm WS] ⚠️ No workers in DB — will use synthetic fallback until data is available')
  }

  if (cachedVaultEntries.length > 0) {
    console.log(`[NEXUS Swarm WS] ✅ Loaded ${cachedVaultEntries.length} vault entries`)
  }
}

// ─── Server startup ──────────────────────────────────────────────────

const PORT = 3003
httpServer.listen(PORT, () => {
  console.log(`[NEXUS Swarm WS] 🟢 WebSocket server running on port ${PORT}`)
  console.log(`[NEXUS Swarm WS] Events: swarm:worker-update, swarm:task-complete, swarm:task-queued, swarm:metrics, nexus:activity`)
  console.log(`[NEXUS Swarm WS] Client event: swarm:assign-task`)
  console.log(`[NEXUS Swarm WS] API base: ${API_BASE}`)

  // Trigger initial data load
  initialLoad().catch(err => {
    console.warn(`[NEXUS Swarm WS] Initial load failed: ${err}. Will retry via periodic polls.`)
  })
})

// ─── Graceful shutdown ───────────────────────────────────────────────

const shutdown = () => {
  console.log('[NEXUS Swarm WS] Shutting down...')
  if (workerPollTimer) clearTimeout(workerPollTimer)
  if (vaultPollTimer) clearTimeout(vaultPollTimer)
  if (taskCompleteTimer) clearTimeout(taskCompleteTimer)
  if (taskQueuedTimer) clearTimeout(taskQueuedTimer)
  if (metricsTimer) clearTimeout(metricsTimer)
  if (activityTimer) clearTimeout(activityTimer)
  io.close()
  httpServer.close(() => {
    console.log('[NEXUS Swarm WS] Server closed')
    process.exit(0)
  })
}

process.on('SIGTERM', shutdown)
process.on('SIGINT', shutdown)
