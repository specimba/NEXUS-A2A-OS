import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── 7352 Governance API Contract ───
// Endpoints: GET (stats), POST (heartbeat, result, propose, approve)

export async function GET() {
  try {
    // Task counts
    const [activeTasks, completedTasks, failedTasks] = await Promise.all([
      db.governanceTask.count({ where: { status: 'active' } }),
      db.governanceTask.count({ where: { status: 'completed' } }),
      db.governanceTask.count({ where: { status: 'failed' } }),
    ])

    // Proposal counts
    const [pendingProposals, approvedProposals, rejectedProposals] = await Promise.all([
      db.governanceProposal.count({ where: { status: 'pending' } }),
      db.governanceProposal.count({ where: { status: 'approved' } }),
      db.governanceProposal.count({ where: { status: 'rejected' } }),
    ])

    // Recent active agents (unique agentIds with recent tasks)
    const recentTasks = await db.governanceTask.findMany({
      take: 10,
      orderBy: { updatedAt: 'desc' },
      select: { agentId: true, updatedAt: true, status: true },
    })

    const agentMap = new Map<string, { agentId: string; status: string; lastHeartbeat: string }>()
    for (const t of recentTasks) {
      if (!agentMap.has(t.agentId)) {
        agentMap.set(t.agentId, {
          nexusId: t.agentId,
          status: t.status === 'active' ? 'online' : 'offline',
          lastHeartbeat: t.updatedAt.toISOString(),
        })
      }
    }

    // Constitution info (from system config or defaults)
    let constitutionVersion = 'v3.2'
    let constitutionRules = 12
    try {
      const versionConfig = await db.systemConfig.findUnique({ where: { key: 'constitution_version' } })
      const rulesConfig = await db.systemConfig.findUnique({ where: { key: 'constitution_rules' } })
      if (versionConfig) constitutionVersion = versionConfig.value
      if (rulesConfig) constitutionRules = parseInt(rulesConfig.value, 10) || 12
    } catch {
      // Use defaults
    }

    return NextResponse.json({
      tasks: { active: activeTasks, completed: completedTasks, failed: failedTasks },
      proposals: { pending: pendingProposals, approved: approvedProposals, rejected: rejectedProposals },
      agents: Array.from(agentMap.values()),
      constitution: { version: constitutionVersion, rules: constitutionRules },
    })
  } catch (error) {
    console.error('Governance GET error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    // ─── heartbeat ───
    if (action === 'heartbeat') {
      const { agentId, taskId, progress, message } = body
      if (!agentId) {
        return NextResponse.json({ error: 'Missing required field: agentId' }, { status: 400 })
      }

      const effectiveTaskId = taskId || `task-${agentId}-${Date.now()}`

      // Upsert the governance task
      const task = await db.governanceTask.upsert({
        where: { taskId: effectiveTaskId },
        update: {
          agentId,
          progress: progress ?? undefined,
          message: message ?? undefined,
          status: 'active',
        },
        create: {
          agentId,
          taskId: effectiveTaskId,
          type: 'stresslab_harness',
          progress: progress ?? 0,
          message: message ?? 'Heartbeat received',
          status: 'active',
        },
      })

      return NextResponse.json({ task, action: 'heartbeat' })
    }

    // ─── result ───
    if (action === 'result') {
      const { agentId, taskId, status, output, tokensUsed, durationMs } = body
      if (!agentId || !taskId) {
        return NextResponse.json({ error: 'Missing required fields: agentId, taskId' }, { status: 400 })
      }

      const effectiveStatus = status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : 'completed'

      const task = await db.governanceTask.update({
        where: { taskId },
        data: {
          status: effectiveStatus,
          output: output ?? undefined,
          tokensUsed: tokensUsed ?? undefined,
          durationMs: durationMs ?? undefined,
          progress: 100,
          completedAt: new Date(),
        },
      })

      // Create VaultEntry audit log for the result
      let vaultEntry = null
      try {
        const agent = await db.agent.findFirst({ where: { name: agentId } })
        if (agent) {
          vaultEntry = await db.vaultEntry.create({
            data: {
              agentId: agent.id,
              track: 'GOV',
              category: 'task_result',
              key: `gov:task:${taskId}:result`,
              value: JSON.stringify({
                taskId,
                agentId,
                status: effectiveStatus,
                tokensUsed: tokensUsed ?? 0,
                durationMs: durationMs ?? 0,
                timestamp: new Date().toISOString(),
              }),
              score: effectiveStatus === 'completed' ? 1.0 : 0.0,
            },
          })
        }
      } catch {
        // Vault logging is non-critical
      }

      // Log token usage
      if (tokensUsed && tokensUsed > 0) {
        try {
          await db.tokenUsageLog.create({
            data: {
              model: 'governance-api',
              promptTokens: Math.floor(tokensUsed * 0.3),
              completionTokens: Math.floor(tokensUsed * 0.7),
              totalTokens: tokensUsed,
              cost: 0,
              apiEndpoint: '/api/governance',
            },
          })
        } catch {
          // Token logging is non-critical
        }
      }

      return NextResponse.json({ task, vaultEntry, action: 'result' })
    }

    // ─── propose ───
    if (action === 'propose') {
      const { agentId, type, title, description, riskLevel } = body
      if (!agentId || !type || !title) {
        return NextResponse.json({ error: 'Missing required fields: agentId, type, title' }, { status: 400 })
      }

      const effectiveRiskLevel = riskLevel || 'low'
      // High-risk proposals are auto-held for governance review
      const initialStatus = effectiveRiskLevel === 'high' ? 'held' : 'pending'

      const proposal = await db.governanceProposal.create({
        data: {
          agentId,
          type,
          title,
          description: description ?? null,
          riskLevel: effectiveRiskLevel,
          status: initialStatus,
        },
      })

      return NextResponse.json({ proposal, autoHeld: initialStatus === 'held', action: 'propose' }, { status: 201 })
    }

    // ─── approve ───
    if (action === 'approve') {
      const { proposalId, approver, notes } = body
      if (!proposalId || !approver) {
        return NextResponse.json({ error: 'Missing required fields: proposalId, approver' }, { status: 400 })
      }

      const proposal = await db.governanceProposal.update({
        where: { id: proposalId },
        data: {
          status: 'approved',
          approver,
          notes: notes ?? undefined,
        },
      })

      // Create VaultEntry governance record
      let vaultEntry = null
      try {
        const agent = await db.agent.findFirst({ where: { name: proposal.agentId } })
        if (agent) {
          vaultEntry = await db.vaultEntry.create({
            data: {
              agentId: agent.id,
              track: 'GOV',
              category: 'proposal_approved',
              key: `gov:proposal:${proposalId}:approved`,
              value: JSON.stringify({
                proposalId,
                agentId: proposal.agentId,
                type: proposal.type,
                title: proposal.title,
                approver,
                notes: notes ?? null,
                timestamp: new Date().toISOString(),
              }),
              score: 1.0,
            },
          })
        }
      } catch {
        // Vault logging is non-critical
      }

      return NextResponse.json({ proposal, vaultEntry, action: 'approve' })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: heartbeat, result, propose, approve` },
      { status: 400 }
    )
  } catch (error) {
    console.error('Governance POST error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
