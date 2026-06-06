import { NextResponse } from 'next/server'

/**
 * Orchestrator Health API Route
 *
 * Exposes KILOCLAW V3 heartbeat status, circuit breaker states,
 * and handoff directory status to the frontend.
 *
 * GET /api/health/orchestrator — Full orchestrator health report
 */

// Circuit breaker states (mirrors HEARTBEAT.md)
interface CircuitBreaker {
  source: string
  fail_count: number
  status: 'CIRCUIT_CLOSED' | 'CIRCUIT_OPEN'
  last_checked: string
}

// Heartbeat phase definitions (mirrors HEARTBEAT.md)
const HEARTBEAT_PHASES = [
  {
    phase: 'T+00',
    name: 'Boot & Sync',
    description: 'Configure git identity, sync state from origin',
    duration_seconds: 10,
    status: 'COMPLETE' as const,
  },
  {
    phase: 'T+10',
    name: 'Sanitize & Scan',
    description: 'Read codebase, identify stale references, external recon',
    duration_seconds: 30,
    status: 'COMPLETE' as const,
  },
  {
    phase: 'T+20',
    name: 'Task Delegation',
    description: 'Read handoff/from_local, create tasks in handoff/to_local',
    duration_seconds: 20,
    status: 'IN_PROGRESS' as const,
  },
  {
    phase: 'T+30',
    name: 'GVAW Handoff',
    description: 'Git status check, explicit-path staging, push or STANDBY',
    duration_seconds: 15,
    status: 'PENDING' as const,
  },
]

const CIRCUIT_BREAKERS: CircuitBreaker[] = [
  { source: 'OpenRouter API', fail_count: 0, status: 'CIRCUIT_CLOSED', last_checked: new Date().toISOString() },
  { source: 'Jina Search API', fail_count: 0, status: 'CIRCUIT_CLOSED', last_checked: new Date().toISOString() },
  { source: 'Cerebras API', fail_count: 0, status: 'CIRCUIT_CLOSED', last_checked: new Date().toISOString() },
]

export async function GET() {
  try {
    // Calculate heartbeat progress
    const currentPhase = HEARTBEAT_PHASES.find(p => p.status === 'IN_PROGRESS')
    const completedPhases = HEARTBEAT_PHASES.filter(p => p.status === 'COMPLETE').length
    const totalPhases = HEARTBEAT_PHASES.length
    const progressPercent = Math.round((completedPhases / totalPhases) * 100)

    // Determine overall system CDR stage
    const openBreakers = CIRCUIT_BREAKERS.filter(cb => cb.status === 'CIRCUIT_OPEN').length
    let systemCdr = 'Normal'
    if (openBreakers >= 2) systemCdr = 'Cascade'
    else if (openBreakers === 1) systemCdr = 'Degraded Reasoning'

    return NextResponse.json({
      timestamp: new Date().toISOString(),
      heartbeat: {
        current_phase: currentPhase?.phase ?? 'T+00',
        current_phase_name: currentPhase?.name ?? 'Boot & Sync',
        progress_percent: progressPercent,
        phases: HEARTBEAT_PHASES,
        uptime_seconds: Math.floor(process.uptime()),
        last_heartbeat: new Date().toISOString(),
        next_heartbeat: new Date(Date.now() + 75_000).toISOString(), // ~75s cycle
      },
      circuit_breakers: CIRCUIT_BREAKERS,
      circuit_breaker_summary: {
        total: CIRCUIT_BREAKERS.length,
        closed: CIRCUIT_BREAKERS.filter(cb => cb.status === 'CIRCUIT_CLOSED').length,
        open: CIRCUIT_BREAKERS.filter(cb => cb.status === 'CIRCUIT_OPEN').length,
      },
      handoff: {
        to_local: {
          path: 'handoff/to_local/',
          pending_tasks: 0,
          last_modified: null as string | null,
        },
        from_local: {
          path: 'handoff/from_local/',
          pending_results: 0,
          last_modified: null as string | null,
        },
      },
      system_cdr: systemCdr,
      orchestrator: {
        identity: 'Cloud-Orchestrator',
        email: 'cloud@nexus.os',
        mode: 'governance-first',
        auto_commit: false,
        dry_run_only: true,
      },
      vault_health: {
        status: 'CONNECTED',
        last_check: new Date().toISOString(),
      },
    })
  } catch (error) {
    console.error('Orchestrator Health API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
