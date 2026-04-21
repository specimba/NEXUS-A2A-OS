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

// ─── Data pools for random generation ────────────────────────────────

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

// ─── Event generators ────────────────────────────────────────────────

function generateWorkerUpdate() {
  const workerId = pick(WORKER_IDS)
  const status = pick(WORKER_STATUSES)
  const task = status === 'busy' ? pick(TASKS) : status === 'error' ? pick(TASKS) : null
  const progress = status === 'busy' ? randInt(10, 95) : status === 'error' ? randInt(0, 60) : 0
  const tokens = randInt(50, 8000)
  return { workerId, status, task, progress, tokens }
}

function generateTaskComplete() {
  return {
    taskId: genId('T'),
    workerId: pick(WORKER_IDS),
    result: pick(['success', 'success', 'success', 'failure'] as const), // bias toward success
    duration: `${randFloat(0.8, 12.5)}s`,
    tokens: randInt(200, 6000),
  }
}

function generateTaskQueued() {
  return {
    taskId: genId('T'),
    domain: pick(DOMAINS),
    priority: pick(PRIORITIES),
    submittedBy: pick(SUBMITTERS),
  }
}

function generateMetrics() {
  return {
    throughput: randFloat(8, 45),
    avgDuration: randFloat(1.2, 8.5),
    successRate: randFloat(0.82, 0.99, 2),
    utilization: randFloat(0.55, 0.95, 2),
    totalTokens: randInt(150000, 420000),
  }
}

function generateActivity() {
  const type = pick(ACTIVITY_TYPES)
  return {
    type,
    source: pick(SOURCES),
    message: pick(ACTIVITY_MESSAGES[type]),
    timestamp: Date.now(),
  }
}

// ─── Connection handling ─────────────────────────────────────────────

io.on('connection', (socket) => {
  console.log(`[NEXUS Swarm WS] Client connected: ${socket.id}`)

  // Handle task assignment from client
  socket.on('swarm:assign-task', (data: { taskId: string; workerId: string }) => {
    console.log(`[NEXUS Swarm WS] Task assignment: ${data.taskId} → ${data.workerId}`)
    // Emit confirmation back to the sender
    socket.emit('swarm:assign-confirmed', {
      taskId: data.taskId,
      workerId: data.workerId,
      status: 'assigned',
      timestamp: Date.now(),
    })
    // Broadcast the worker update to all clients
    io.emit('swarm:worker-update', {
      workerId: data.workerId,
      status: 'busy',
      task: data.taskId,
      progress: 0,
      tokens: 0,
    })
    // Broadcast activity
    io.emit('nexus:activity', {
      type: 'info',
      source: 'Swarm',
      message: `Task ${data.taskId} assigned to ${data.workerId}`,
      timestamp: Date.now(),
    })
  })

  socket.on('disconnect', (reason) => {
    console.log(`[NEXUS Swarm WS] Client disconnected: ${socket.id} (${reason})`)
  })

  socket.on('error', (error) => {
    console.error(`[NEXUS Swarm WS] Socket error (${socket.id}):`, error)
  })
})

// ─── Periodic event emitters ─────────────────────────────────────────

// Worker status updates every 3-5 seconds
let workerUpdateTimer: ReturnType<typeof setTimeout> | null = null
function scheduleWorkerUpdate() {
  const delay = randInt(3000, 5000)
  workerUpdateTimer = setTimeout(() => {
    io.emit('swarm:worker-update', generateWorkerUpdate())
    scheduleWorkerUpdate()
  }, delay)
}
scheduleWorkerUpdate()

// Task completion events every 5-8 seconds
let taskCompleteTimer: ReturnType<typeof setTimeout> | null = null
function scheduleTaskComplete() {
  const delay = randInt(5000, 8000)
  taskCompleteTimer = setTimeout(() => {
    io.emit('swarm:task-complete', generateTaskComplete())
    scheduleTaskComplete()
  }, delay)
}
scheduleTaskComplete()

// New task queued events every 4-7 seconds
let taskQueuedTimer: ReturnType<typeof setTimeout> | null = null
function scheduleTaskQueued() {
  const delay = randInt(4000, 7000)
  taskQueuedTimer = setTimeout(() => {
    io.emit('swarm:task-queued', generateTaskQueued())
    scheduleTaskQueued()
  }, delay)
}
scheduleTaskQueued()

// Aggregate metrics update every 3-5 seconds
let metricsTimer: ReturnType<typeof setTimeout> | null = null
function scheduleMetrics() {
  const delay = randInt(3000, 5000)
  metricsTimer = setTimeout(() => {
    io.emit('swarm:metrics', generateMetrics())
    scheduleMetrics()
  }, delay)
}
scheduleMetrics()

// General activity feed items every 3-5 seconds
let activityTimer: ReturnType<typeof setTimeout> | null = null
function scheduleActivity() {
  const delay = randInt(3000, 5000)
  activityTimer = setTimeout(() => {
    io.emit('nexus:activity', generateActivity())
    scheduleActivity()
  }, delay)
}
scheduleActivity()

// ─── Server startup ──────────────────────────────────────────────────

const PORT = 3003
httpServer.listen(PORT, () => {
  console.log(`[NEXUS Swarm WS] 🟢 WebSocket server running on port ${PORT}`)
  console.log(`[NEXUS Swarm WS] Events: swarm:worker-update, swarm:task-complete, swarm:task-queued, swarm:metrics, nexus:activity`)
  console.log(`[NEXUS Swarm WS] Client event: swarm:assign-task`)
})

// ─── Graceful shutdown ───────────────────────────────────────────────

const shutdown = () => {
  console.log('[NEXUS Swarm WS] Shutting down...')
  if (workerUpdateTimer) clearTimeout(workerUpdateTimer)
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
