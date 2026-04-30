import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Auto-Task Generation from Papers ───
// POST: Scan P0/P1 papers, generate GovernanceTasks for those without tasks
//
// Mapping logic:
//   researchRole → agentId + type
//   priorityTier → riskLevel
//   taskId: paper-{paper.externalId || paper.id.slice(0,8)}

// Research role to agent assignment mapping
const ROLE_AGENT_MAP: Record<string, { agentId: string; type: string }> = {
  evaluation: { agentId: 'nexus-specialist', type: 'evaluation' },
  safety: { agentId: 'nexus-coordinator', type: 'safety_review' },
  implementation: { agentId: 'nexus-worker', type: 'implementation' },
  memory: { agentId: 'nexus-specialist', type: 'memory_research' },
  harness: { agentId: 'nexus-coordinator', type: 'harness_testing' },
  compression: { agentId: 'nexus-worker', type: 'compression' },
  benchmark: { agentId: 'nexus-specialist', type: 'benchmark' },
  survey: { agentId: 'nexus-specialist', type: 'survey_analysis' },
  infra: { agentId: 'nexus-coordinator', type: 'infra_build' },
  context_only: { agentId: 'nexus-worker', type: 'context_processing' },
}

// Priority tier to risk level mapping
const PRIORITY_RISK_MAP: Record<string, string> = {
  P0: 'high',
  P1: 'medium',
  P2: 'low',
  HOLD: 'low',
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}))

    // Allow overriding which tiers to scan (default: P0 and P1)
    const tiers = body.tiers || ['P0', 'P1']

    // Scan papers in the specified priority tiers
    const papers = await db.paper.findMany({
      where: {
        priorityTier: { in: tiers },
      },
      orderBy: [
        { priorityTier: 'asc' }, // P0 first
        { dgFinalScore: 'desc' },
      ],
    })

    // Get all existing taskIds to check for duplicates (idempotency)
    const existingTasks = await db.governanceTask.findMany({
      select: { taskId: true },
    })
    const existingTaskIds = new Set(existingTasks.map((t) => t.taskId))

    const generated: Array<{
      taskId: string
      paperId: string
      paperTitle: string
      agentId: string
      type: string
      riskLevel: string
    }> = []
    const skipped: Array<{ paperId: string; taskId: string; reason: string }> = []
    const errors: Array<{ paperId: string; error: string }> = []

    for (const paper of papers) {
      // Build the taskId for this paper
      const taskId = `paper-${paper.externalId || paper.id.slice(0, 8)}`

      // Idempotency check — skip if task already exists
      if (existingTaskIds.has(taskId)) {
        skipped.push({
          paperId: paper.id,
          taskId,
          reason: 'Task already exists for this paper',
        })
        continue
      }

      // Derive agentId and type from researchRole
      const roleMapping = ROLE_AGENT_MAP[paper.researchRole] || ROLE_AGENT_MAP.context_only
      const agentId = roleMapping.agentId
      const type = roleMapping.type

      // Derive riskLevel from priorityTier
      const riskLevel = PRIORITY_RISK_MAP[paper.priorityTier] || 'low'

      // Build message from paper title + implementationTask
      const messageParts: string[] = []
      if (paper.title) {
        messageParts.push(paper.title)
      }
      if (paper.implementationTask) {
        messageParts.push(`Task: ${paper.implementationTask}`)
      }
      const message = messageParts.length > 0
        ? messageParts.join(' | ')
        : `Auto-generated task for paper ${paper.externalId || paper.id}`

      try {
        const task = await db.governanceTask.create({
          data: {
            agentId,
            taskId,
            type,
            status: 'active',
            progress: 0,
            message,
            riskLevel,
          },
        })

        // Add to existing set so subsequent papers with same taskId get skipped
        existingTaskIds.add(taskId)

        generated.push({
          taskId: task.taskId,
          paperId: paper.id,
          paperTitle: paper.title,
          agentId,
          type,
          riskLevel,
        })

        // Create VaultEntry audit log for the auto-generated task
        try {
          const agent = await db.agent.findFirst({ where: { name: agentId } })
          if (agent) {
            await db.vaultEntry.create({
              data: {
                agentId: agent.id,
                track: 'GOV',
                category: 'task_auto_generated',
                key: `gov:task:${taskId}:auto_generated`,
                value: JSON.stringify({
                  taskId,
                  paperId: paper.id,
                  paperTitle: paper.title,
                  agentId,
                  type,
                  riskLevel,
                  priorityTier: paper.priorityTier,
                  researchRole: paper.researchRole,
                  implementationTask: paper.implementationTask || null,
                  deliverable: paper.deliverable || null,
                  autoGeneratedAt: new Date().toISOString(),
                }),
                score: riskLevel === 'high' ? 1.0 : riskLevel === 'medium' ? 0.6 : 0.3,
              },
            })
          }
        } catch {
          // Vault logging is non-critical
        }
      } catch (createError) {
        errors.push({
          paperId: paper.id,
          error: String(createError),
        })
      }
    }

    return NextResponse.json({
      summary: {
        papersScanned: papers.length,
        tasksGenerated: generated.length,
        tasksSkipped: skipped.length,
        errors: errors.length,
        tiers,
      },
      generated,
      skipped,
      errors: errors.length > 0 ? errors : undefined,
    })
  } catch (error) {
    console.error('Auto-generate POST error:', error)
    return NextResponse.json({ error: 'Failed to auto-generate tasks' }, { status: 500 })
  }
}

// GET: Preview what auto-generation would produce (dry-run)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const tiersParam = searchParams.get('tiers')
    const tiers = tiersParam ? tiersParam.split(',') : ['P0', 'P1']

    const papers = await db.paper.findMany({
      where: {
        priorityTier: { in: tiers },
      },
      orderBy: [
        { priorityTier: 'asc' },
        { dgFinalScore: 'desc' },
      ],
      select: {
        id: true,
        externalId: true,
        title: true,
        priorityTier: true,
        researchRole: true,
        implementationTask: true,
        deliverable: true,
      },
    })

    const existingTasks = await db.governanceTask.findMany({
      select: { taskId: true },
    })
    const existingTaskIds = new Set(existingTasks.map((t) => t.taskId))

    const preview = papers.map((paper) => {
      const taskId = `paper-${paper.externalId || paper.id.slice(0, 8)}`
      const roleMapping = ROLE_AGENT_MAP[paper.researchRole] || ROLE_AGENT_MAP.context_only
      const riskLevel = PRIORITY_RISK_MAP[paper.priorityTier] || 'low'

      return {
        paperId: paper.id,
        paperTitle: paper.title,
        priorityTier: paper.priorityTier,
        researchRole: paper.researchRole,
        taskId,
        agentId: roleMapping.agentId,
        type: roleMapping.type,
        riskLevel,
        alreadyExists: existingTaskIds.has(taskId),
        implementationTask: paper.implementationTask,
        deliverable: paper.deliverable,
      }
    })

    const newCount = preview.filter((p) => !p.alreadyExists).length
    const existingCount = preview.filter((p) => p.alreadyExists).length

    return NextResponse.json({
      dryRun: true,
      tiers,
      summary: {
        papersScanned: papers.length,
        wouldGenerate: newCount,
        alreadyHaveTasks: existingCount,
      },
      preview,
    })
  } catch (error) {
    console.error('Auto-generate GET (dry-run) error:', error)
    return NextResponse.json({ error: 'Failed to preview auto-generation' }, { status: 500 })
  }
}
