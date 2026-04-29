import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Single Task Operations ───
// GET:    Get task details by ID (cuid) or taskId
// PATCH:  Update task with evidence validation

interface RouteContext {
  params: Promise<{ id: string }>
}

export async function GET(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    // Try to find by cuid (id) first, then by taskId
    let task = await db.governanceTask.findUnique({ where: { id } })

    if (!task) {
      task = await db.governanceTask.findUnique({ where: { taskId: id } })
    }

    if (!task) {
      return NextResponse.json(
        { error: `Task '${id}' not found` },
        { status: 404 }
      )
    }

    // Fetch related vault entries for this task
    const vaultEntries = await db.vaultEntry.findMany({
      where: {
        key: { contains: `gov:task:${task.taskId}` },
      },
      orderBy: { createdAt: 'desc' },
      take: 20,
    })

    return NextResponse.json({
      task,
      auditTrail: vaultEntries,
    })
  } catch (error) {
    console.error('Task GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch task' }, { status: 500 })
  }
}

export async function PATCH(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params
    const body = await request.json()

    // Try to find by cuid (id) first, then by taskId
    let task = await db.governanceTask.findUnique({ where: { id } })

    if (!task) {
      task = await db.governanceTask.findUnique({ where: { taskId: id } })
    }

    if (!task) {
      return NextResponse.json(
        { error: `Task '${id}' not found` },
        { status: 404 }
      )
    }

    // Evidence validation: task cannot be marked 'completed' without output evidence
    if (body.status === 'completed') {
      const hasOutput = body.output || task.output
      if (!hasOutput) {
        return NextResponse.json(
          { error: 'Cannot mark task as completed without output evidence. Provide an output field.' },
          { status: 400 }
        )
      }
    }

    // Build update data from provided fields
    const updateData: Record<string, unknown> = {}

    if (body.agentId !== undefined) updateData.agentId = body.agentId
    if (body.type !== undefined) updateData.type = body.type
    if (body.status !== undefined) updateData.status = body.status
    if (body.progress !== undefined) updateData.progress = body.progress
    if (body.message !== undefined) updateData.message = body.message
    if (body.output !== undefined) updateData.output = body.output
    if (body.tokensUsed !== undefined) updateData.tokensUsed = body.tokensUsed
    if (body.durationMs !== undefined) updateData.durationMs = body.durationMs
    if (body.riskLevel !== undefined) updateData.riskLevel = body.riskLevel

    // Set completedAt when marking as completed
    if (body.status === 'completed') {
      updateData.completedAt = new Date()
      // Auto-set progress to 100 if not explicitly set
      if (body.progress === undefined) {
        updateData.progress = 100
      }
    }

    // If status is being changed away from completed, clear completedAt
    if (body.status && body.status !== 'completed' && task.status === 'completed') {
      updateData.completedAt = null
    }

    const updatedTask = await db.governanceTask.update({
      where: { id: task.id },
      data: updateData,
    })

    // Create VaultEntry audit log for the update
    try {
      const agent = await db.agent.findFirst({ where: { name: task.agentId } })
      if (agent) {
        const auditCategory = body.status === 'completed'
          ? 'task_completed'
          : body.status === 'failed'
            ? 'task_failed'
            : 'task_updated'

        const auditScore = body.status === 'completed'
          ? 1.0
          : body.status === 'failed'
            ? 0.0
            : 0.5

        await db.vaultEntry.create({
          data: {
            agentId: agent.id,
            track: 'GOV',
            category: auditCategory,
            key: `gov:task:${task.taskId}:${auditCategory}`,
            value: JSON.stringify({
              taskId: task.taskId,
              previousStatus: task.status,
              newStatus: body.status || task.status,
              updatedFields: Object.keys(updateData),
              timestamp: new Date().toISOString(),
            }),
            score: auditScore,
          },
        })
      }
    } catch {
      // Vault logging is non-critical
    }

    return NextResponse.json({ task: updatedTask })
  } catch (error) {
    console.error('Task PATCH error:', error)
    return NextResponse.json({ error: 'Failed to update task' }, { status: 500 })
  }
}
