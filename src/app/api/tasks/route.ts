import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Unified Task CRUD API ───
// GET:    List all tasks with filtering — returns UI-mapped format
// POST:   Create task OR perform action (start/complete/fail/reopen/auto_generate)
// PUT:    Update task status, progress, output
// DELETE: Delete a task by id or taskId

// ── Mapping helpers ──────────────────────────────────────────────────

const RISK_TO_PRIORITY: Record<string, string> = {
  critical: 'P0',
  high: 'P1',
  medium: 'P2',
  low: 'P3',
}

const PRIORITY_TO_RISK: Record<string, string> = {
  P0: 'critical',
  P1: 'high',
  P2: 'medium',
  P3: 'low',
}

const STATUS_MAP_API_TO_UI: Record<string, string> = {
  active: 'open',
  in_progress: 'in_progress',
  completed: 'completed',
  failed: 'failed',
  held: 'blocked',
}

const STATUS_MAP_UI_TO_API: Record<string, string> = {
  open: 'active',
  in_progress: 'in_progress',
  completed: 'completed',
  failed: 'failed',
  blocked: 'held',
}

function mapTaskToUI(raw: Record<string, unknown>) {
  const rawStatus = String(raw.status || 'active')
  const rawRisk = String(raw.riskLevel || 'low')
  const rawType = String(raw.type || 'general')
  const rawMessage = raw.message ? String(raw.message) : ''
  const rawOutput = raw.output ? String(raw.output) : null
  const rawAgentId = raw.agentId ? String(raw.agentId) : null

  // Parse message: first line as title, rest as description
  const messageLines = rawMessage.split('\n')
  const title = messageLines[0] || `Task ${String(raw.taskId || '').slice(0, 12)}`
  const description = messageLines.length > 1 ? messageLines.slice(1).join('\n').trim() : rawMessage

  return {
    id: String(raw.taskId || raw.id),
    title,
    description,
    priority: RISK_TO_PRIORITY[rawRisk] || 'P2',
    status: STATUS_MAP_API_TO_UI[rawStatus] || rawStatus,
    category: rawType,
    source: rawAgentId || 'system',
    assignee: rawAgentId,
    completionProof: rawOutput,
    completedBy: rawStatus === 'completed' ? rawAgentId : null,
    completedAt: raw.completedAt ? String(raw.completedAt) : null,
    dueAt: null,
    parentId: null,
    tags: rawType ? JSON.stringify([rawType]) : null,
    metadata: JSON.stringify({
      progress: raw.progress ?? 0,
      tokensUsed: raw.tokensUsed ?? 0,
      durationMs: raw.durationMs ?? 0,
      cuid: raw.id,
    }),
    createdAt: String(raw.createdAt),
    updatedAt: String(raw.updatedAt),
  }
}

// ── GET: List tasks ──────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    // Build filter from query params
    const where: Record<string, unknown> = {}

    // Support both UI and API filter params
    const statusParam = searchParams.get('status')
    if (statusParam) {
      // Map UI status to API status
      where.status = STATUS_MAP_UI_TO_API[statusParam] || statusParam
    }

    const typeParam = searchParams.get('type') || searchParams.get('category')
    if (typeParam) {
      where.type = typeParam
    }

    const agentIdParam = searchParams.get('agentId') || searchParams.get('assignee')
    if (agentIdParam) {
      where.agentId = agentIdParam
    }

    const riskLevelParam = searchParams.get('riskLevel') || searchParams.get('priority')
    if (riskLevelParam) {
      // Map UI priority to API riskLevel
      where.riskLevel = PRIORITY_TO_RISK[riskLevelParam] || riskLevelParam
    }

    // Pagination
    const limit = Math.min(parseInt(searchParams.get('limit') || '50', 10), 200)
    const offset = parseInt(searchParams.get('offset') || '0', 10)

    // Sorting
    const sortBy = searchParams.get('sortBy') || 'updatedAt'
    const sortOrder = searchParams.get('sortOrder') === 'asc' ? 'asc' : 'desc'

    const [tasks, total] = await Promise.all([
      db.governanceTask.findMany({
        where,
        take: limit,
        skip: offset,
        orderBy: { [sortBy]: sortOrder },
      }),
      db.governanceTask.count({ where }),
    ])

    // Map tasks to UI format
    const mappedTasks = tasks.map((t: Record<string, unknown>) => mapTaskToUI(t))

    return NextResponse.json({
      tasks: mappedTasks,
      pagination: {
        total,
        limit,
        offset,
        hasMore: offset + tasks.length < total,
      },
    })
  } catch (error) {
    console.error('Tasks GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch tasks' }, { status: 500 })
  }
}

// ── POST: Create task or perform action ──────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // ── Action-based operations ──
    if (body.action) {
      switch (body.action) {
        case 'auto_generate': {
          // Delegate to auto-generate logic inline
          const tiers = body.tiers || ['P0', 'P1']
          const papers = await db.paper.findMany({
            where: { priorityTier: { in: tiers } },
            orderBy: [{ priorityTier: 'asc' }, { dgFinalScore: 'desc' }],
          })
          const existingTasks = await db.governanceTask.findMany({ select: { taskId: true } })
          const existingTaskIds = new Set(existingTasks.map((t: { taskId: string }) => t.taskId))

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
          const PRIORITY_RISK_MAP: Record<string, string> = {
            P0: 'high', P1: 'medium', P2: 'low', HOLD: 'low',
          }

          let generated = 0
          for (const paper of papers) {
            const taskId = `paper-${paper.externalId || paper.id.slice(0, 8)}`
            if (existingTaskIds.has(taskId)) continue
            const roleMapping = ROLE_AGENT_MAP[paper.researchRole] || ROLE_AGENT_MAP.context_only
            const riskLevel = PRIORITY_RISK_MAP[paper.priorityTier] || 'low'
            const messageParts: string[] = []
            if (paper.title) messageParts.push(paper.title)
            if (paper.implementationTask) messageParts.push(`Task: ${paper.implementationTask}`)
            const message = messageParts.length > 0 ? messageParts.join('\n') : `Auto-generated task for paper ${paper.externalId || paper.id}`

            await db.governanceTask.create({
              data: { agentId: roleMapping.agentId, taskId, type: roleMapping.type, status: 'active', progress: 0, message, riskLevel },
            })
            existingTaskIds.add(taskId)
            generated++
          }
          return NextResponse.json({ generated, total: papers.length })
        }

        case 'create': {
          // Create task with UI-friendly fields
          if (!body.title) {
            return NextResponse.json({ error: 'Title is required' }, { status: 400 })
          }
          const taskId = body.id || `manual-${Date.now()}`
          const riskLevel = PRIORITY_TO_RISK[body.priority] || 'low'
          const agentId = body.assignee || body.category || 'system'
          const type = body.category || 'general'
          const status = STATUS_MAP_UI_TO_API[body.status] || 'active'
          // Combine title + description as message
          const message = body.description ? `${body.title}\n${body.description}` : body.title

          const existing = await db.governanceTask.findUnique({ where: { taskId } })
          if (existing) {
            return NextResponse.json({ error: `Task '${taskId}' already exists` }, { status: 409 })
          }

          const task = await db.governanceTask.create({
            data: {
              agentId,
              taskId,
              type,
              status,
              progress: 0,
              message,
              riskLevel,
            },
          })

          // Audit log
          try {
            const agent = await db.agent.findFirst({ where: { name: agentId } })
            if (agent) {
              await db.vaultEntry.create({
                data: {
                  agentId: agent.id,
                  track: 'GOV',
                  category: 'task_created',
                  key: `gov:task:${taskId}:created`,
                  value: JSON.stringify({ taskId, agentId, type, riskLevel, createdAt: new Date().toISOString() }),
                  score: 0.5,
                },
              })
            }
          } catch { /* non-critical */ }

          return NextResponse.json({ task: mapTaskToUI(task as Record<string, unknown>) }, { status: 201 })
        }

        case 'start': {
          // Set status to in_progress
          if (!body.id) return NextResponse.json({ error: 'Task id is required' }, { status: 400 })
          const task = await findAndMapTask(body.id)
          if (!task) return NextResponse.json({ error: 'Task not found' }, { status: 404 })
          const updated = await db.governanceTask.update({
            where: { taskId: body.id },
            data: { status: 'in_progress' },
          })
          return NextResponse.json({ task: mapTaskToUI(updated as Record<string, unknown>) })
        }

        case 'complete': {
          if (!body.id) return NextResponse.json({ error: 'Task id is required' }, { status: 400 })
          const task = await findAndMapTask(body.id)
          if (!task) return NextResponse.json({ error: 'Task not found' }, { status: 404 })
          if (!body.completionProof) {
            return NextResponse.json({ error: 'Completion proof is required' }, { status: 400 })
          }
          const updated = await db.governanceTask.update({
            where: { taskId: body.id },
            data: { status: 'completed', output: body.completionProof, completedAt: new Date(), progress: 100 },
          })
          return NextResponse.json({ task: mapTaskToUI(updated as Record<string, unknown>) })
        }

        case 'fail': {
          if (!body.id) return NextResponse.json({ error: 'Task id is required' }, { status: 400 })
          const task = await findAndMapTask(body.id)
          if (!task) return NextResponse.json({ error: 'Task not found' }, { status: 404 })
          const updated = await db.governanceTask.update({
            where: { taskId: body.id },
            data: { status: 'failed', output: body.reason || 'Task failed' },
          })
          return NextResponse.json({ task: mapTaskToUI(updated as Record<string, unknown>) })
        }

        case 'reopen': {
          if (!body.id) return NextResponse.json({ error: 'Task id is required' }, { status: 400 })
          const task = await findAndMapTask(body.id)
          if (!task) return NextResponse.json({ error: 'Task not found' }, { status: 404 })
          const updated = await db.governanceTask.update({
            where: { taskId: body.id },
            data: { status: 'active', completedAt: null, progress: 0 },
          })
          return NextResponse.json({ task: mapTaskToUI(updated as Record<string, unknown>) })
        }

        default:
          return NextResponse.json({ error: `Unknown action: ${body.action}` }, { status: 400 })
      }
    }

    // ── Legacy create (agentId + type) ──
    if (!body.agentId || !body.type) {
      return NextResponse.json({ error: 'Missing required fields: agentId, type (or use action)' }, { status: 400 })
    }

    const taskId = body.taskId || `manual-${body.agentId}-${Date.now()}`
    const existing = await db.governanceTask.findUnique({ where: { taskId } })
    if (existing) {
      return NextResponse.json({ error: `Task with taskId '${taskId}' already exists` }, { status: 409 })
    }
    const riskLevel = body.riskLevel || 'low'

    const task = await db.governanceTask.create({
      data: {
        agentId: body.agentId,
        taskId,
        type: body.type,
        status: body.status || 'active',
        progress: body.progress ?? 0,
        message: body.message ?? null,
        output: body.output ?? null,
        tokensUsed: body.tokensUsed ?? 0,
        durationMs: body.durationMs ?? 0,
        riskLevel,
      },
    })

    // Audit log
    try {
      const agent = await db.agent.findFirst({ where: { name: body.agentId } })
      if (agent) {
        await db.vaultEntry.create({
          data: {
            agentId: agent.id,
            track: 'GOV',
            category: 'task_created',
            key: `gov:task:${taskId}:created`,
            value: JSON.stringify({ taskId, agentId: body.agentId, type: body.type, riskLevel, createdAt: new Date().toISOString() }),
            score: 0.5,
          },
        })
      }
    } catch { /* non-critical */ }

    return NextResponse.json({ task: mapTaskToUI(task as Record<string, unknown>) }, { status: 201 })
  } catch (error) {
    console.error('Tasks POST error:', error)
    return NextResponse.json({ error: 'Failed to process task request' }, { status: 500 })
  }
}

// ── PUT: Update task ─────────────────────────────────────────────────

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()

    if (!body.taskId) {
      return NextResponse.json({ error: 'Missing required field: taskId' }, { status: 400 })
    }

    const existing = await db.governanceTask.findUnique({
      where: { taskId: body.taskId },
    })
    if (!existing) {
      return NextResponse.json({ error: `Task '${body.taskId}' not found` }, { status: 404 })
    }

    // If marking as completed, validate output evidence
    if (body.status === 'completed' && !body.output && !existing.output) {
      return NextResponse.json({ error: 'Cannot mark task as completed without output evidence' }, { status: 400 })
    }

    // Build update data
    const updateData: Record<string, unknown> = {}
    if (body.status !== undefined) updateData.status = body.status
    if (body.progress !== undefined) updateData.progress = body.progress
    if (body.message !== undefined) updateData.message = body.message
    if (body.output !== undefined) updateData.output = body.output
    if (body.tokensUsed !== undefined) updateData.tokensUsed = body.tokensUsed
    if (body.durationMs !== undefined) updateData.durationMs = body.durationMs
    if (body.riskLevel !== undefined) updateData.riskLevel = body.riskLevel
    if (body.agentId !== undefined) updateData.agentId = body.agentId

    // Set completedAt if status is being set to completed
    if (body.status === 'completed') {
      updateData.completedAt = new Date()
      updateData.progress = 100
    }

    const task = await db.governanceTask.update({
      where: { taskId: body.taskId },
      data: updateData,
    })

    // Create VaultEntry audit log for the update
    try {
      const agent = await db.agent.findFirst({ where: { name: existing.agentId } })
      if (agent) {
        await db.vaultEntry.create({
          data: {
            agentId: agent.id,
            track: 'GOV',
            category: 'task_updated',
            key: `gov:task:${body.taskId}:updated`,
            value: JSON.stringify({
              taskId: body.taskId,
              updates: Object.keys(updateData),
              status: body.status || existing.status,
              timestamp: new Date().toISOString(),
            }),
            score: body.status === 'completed' ? 1.0 : 0.5,
          },
        })
      }
    } catch { /* non-critical */ }

    return NextResponse.json({ task: mapTaskToUI(task as Record<string, unknown>) })
  } catch (error) {
    console.error('Tasks PUT error:', error)
    return NextResponse.json({ error: 'Failed to update task' }, { status: 500 })
  }
}

// ── DELETE: Delete a task ────────────────────────────────────────────

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get('id')

    if (!id) {
      return NextResponse.json({ error: 'Missing required query param: id' }, { status: 400 })
    }

    // Try to find by taskId first, then by cuid
    let task = await db.governanceTask.findUnique({ where: { taskId: id } })
    if (!task) {
      task = await db.governanceTask.findUnique({ where: { id } })
    }
    if (!task) {
      return NextResponse.json({ error: `Task '${id}' not found` }, { status: 404 })
    }

    await db.governanceTask.delete({ where: { id: task.id } })

    return NextResponse.json({ deleted: true, taskId: task.taskId })
  } catch (error) {
    console.error('Tasks DELETE error:', error)
    return NextResponse.json({ error: 'Failed to delete task' }, { status: 500 })
  }
}

// ── Helper: Find task by taskId or cuid ──
async function findAndMapTask(id: string) {
  let task = await db.governanceTask.findUnique({ where: { taskId: id } })
  if (!task) {
    task = await db.governanceTask.findUnique({ where: { id } })
  }
  return task
}
