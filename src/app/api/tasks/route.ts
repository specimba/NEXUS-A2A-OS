import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── Unified Task CRUD API ───
// GET:  List all tasks with filtering (status, type, agentId, riskLevel)
// POST: Create a new task (manual creation)
// PUT:  Update task status, progress, output

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    // Build filter from query params
    const where: Record<string, unknown> = {}

    const status = searchParams.get('status')
    if (status) {
      where.status = status
    }

    const type = searchParams.get('type')
    if (type) {
      where.type = type
    }

    const agentId = searchParams.get('agentId')
    if (agentId) {
      where.agentId = agentId
    }

    const riskLevel = searchParams.get('riskLevel')
    if (riskLevel) {
      where.riskLevel = riskLevel
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

    return NextResponse.json({
      tasks,
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // Validate required fields
    if (!body.agentId || !body.type) {
      return NextResponse.json(
        { error: 'Missing required fields: agentId, type' },
        { status: 400 }
      )
    }

    // Generate taskId if not provided
    const taskId = body.taskId || `manual-${body.agentId}-${Date.now()}`

    // Check for duplicate taskId
    const existing = await db.governanceTask.findUnique({ where: { taskId } })
    if (existing) {
      return NextResponse.json(
        { error: `Task with taskId '${taskId}' already exists` },
        { status: 409 }
      )
    }

    // Derive riskLevel from priorityTier if provided, otherwise use body or default
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

    // Create VaultEntry audit log
    try {
      const agent = await db.agent.findFirst({ where: { name: body.agentId } })
      if (agent) {
        await db.vaultEntry.create({
          data: {
            agentId: agent.id,
            track: 'GOV',
            category: 'task_created',
            key: `gov:task:${taskId}:created`,
            value: JSON.stringify({
              taskId,
              agentId: body.agentId,
              type: body.type,
              riskLevel,
              createdAt: new Date().toISOString(),
            }),
            score: 0.5,
          },
        })
      }
    } catch {
      // Vault logging is non-critical
    }

    return NextResponse.json({ task }, { status: 201 })
  } catch (error) {
    console.error('Tasks POST error:', error)
    return NextResponse.json({ error: 'Failed to create task' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()

    if (!body.taskId) {
      return NextResponse.json(
        { error: 'Missing required field: taskId' },
        { status: 400 }
      )
    }

    const existing = await db.governanceTask.findUnique({
      where: { taskId: body.taskId },
    })
    if (!existing) {
      return NextResponse.json(
        { error: `Task '${body.taskId}' not found` },
        { status: 404 }
      )
    }

    // If marking as completed, validate output evidence
    if (body.status === 'completed' && !body.output && !existing.output) {
      return NextResponse.json(
        { error: 'Cannot mark task as completed without output evidence' },
        { status: 400 }
      )
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
    } catch {
      // Vault logging is non-critical
    }

    return NextResponse.json({ task })
  } catch (error) {
    console.error('Tasks PUT error:', error)
    return NextResponse.json({ error: 'Failed to update task' }, { status: 500 })
  }
}
