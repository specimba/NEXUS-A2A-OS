import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const agents = await db.agent.findMany({
      orderBy: { name: 'asc' },
      include: {
        vaultEntries: { take: 5, orderBy: { createdAt: 'desc' } },
        testRuns: { take: 5, orderBy: { createdAt: 'desc' } },
      },
    })

    // Format agents as swarm workers
    const workers = agents.map(agent => ({
      id: agent.id,
      name: agent.name,
      type: agent.type,
      status: agent.status,
      domain: agent.domain,
      trustScore: agent.trustScore,
      totalTokens: agent.totalTokens,
      tasksDone: agent.tasksDone,
      tasksFailed: agent.tasksFailed,
      lastActive: agent.lastActive,
      recentActivity: agent.vaultEntries.length + agent.testRuns.length,
    }))

    // Compute swarm-level stats
    const totalWorkers = workers.length
    const busyWorkers = workers.filter(w => w.status === 'busy').length
    const idleWorkers = workers.filter(w => w.status === 'idle').length
    const errorWorkers = workers.filter(w => w.status === 'error').length
    const offlineWorkers = workers.filter(w => w.status === 'offline').length
    const totalTasks = workers.reduce((sum, w) => sum + w.tasksDone + w.tasksFailed, 0)
    const avgTrust = totalWorkers > 0
      ? workers.reduce((sum, w) => sum + w.trustScore, 0) / totalWorkers
      : 0

    return NextResponse.json({
      workers,
      stats: {
        totalWorkers,
        busyWorkers,
        idleWorkers,
        errorWorkers,
        offlineWorkers,
        totalTasks,
        avgTrust: Math.round(avgTrust * 100) / 100,
      },
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'reassign_task') {
      const { workerId, newDomain, newTask } = body

      if (!workerId) {
        return NextResponse.json(
          { error: 'Missing required field: workerId' },
          { status: 400 }
        )
      }

      const agent = await db.agent.findUnique({ where: { id: workerId } })
      if (!agent) {
        return NextResponse.json({ error: 'Worker not found' }, { status: 404 })
      }

      const updateData: Record<string, unknown> = {
        status: 'busy',
        lastActive: new Date(),
      }
      if (newDomain) {
        updateData.domain = newDomain
      }

      const updated = await db.agent.update({
        where: { id: workerId },
        data: updateData,
      })

      return NextResponse.json({
        worker: updated,
        message: `Task${newTask ? ` "${newTask}"` : ''} reassigned to ${agent.name}`,
      })
    }

    if (action === 'terminate_worker') {
      const { workerId } = body

      if (!workerId) {
        return NextResponse.json(
          { error: 'Missing required field: workerId' },
          { status: 400 }
        )
      }

      const agent = await db.agent.findUnique({ where: { id: workerId } })
      if (!agent) {
        return NextResponse.json({ error: 'Worker not found' }, { status: 404 })
      }

      const updated = await db.agent.update({
        where: { id: workerId },
        data: {
          status: 'offline',
          lastActive: new Date(),
        },
      })

      return NextResponse.json({
        worker: updated,
        message: `Worker ${agent.name} terminated`,
      })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: reassign_task, terminate_worker` },
      { status: 400 }
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
