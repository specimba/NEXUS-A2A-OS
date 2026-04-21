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

      // Log this action to the vault
      await db.vaultEntry.create({
        data: {
          agentId: workerId,
          track: 'EVENT',
          category: 'task_reassignment',
          key: `reassign:${agent.name}`,
          value: JSON.stringify({ from: agent.domain, to: newDomain || agent.domain, task: newTask || 'auto' }),
          score: agent.trustScore,
        },
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

      // Log to vault
      await db.vaultEntry.create({
        data: {
          agentId: workerId,
          track: 'EVENT',
          category: 'worker_termination',
          key: `terminate:${agent.name}`,
          value: JSON.stringify({ reason: 'manual_termination', trustScore: agent.trustScore }),
          score: agent.trustScore,
        },
      })

      return NextResponse.json({
        worker: updated,
        message: `Worker ${agent.name} terminated`,
      })
    }

    if (action === 'restart_worker') {
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
          status: 'idle',
          lastActive: new Date(),
        },
      })

      // Log to vault
      await db.vaultEntry.create({
        data: {
          agentId: workerId,
          track: 'EVENT',
          category: 'worker_restart',
          key: `restart:${agent.name}`,
          value: JSON.stringify({ previousStatus: agent.status, newStatus: 'idle' }),
          score: agent.trustScore,
        },
      })

      return NextResponse.json({
        worker: updated,
        message: `Worker ${agent.name} restarted — now idle`,
      })
    }

    if (action === 'spawn_worker') {
      const { name, type, domain } = body

      if (!name || !type) {
        return NextResponse.json(
          { error: 'Missing required fields: name, type' },
          { status: 400 }
        )
      }

      // Check max agent limit
      const activeAgents = await db.agent.findMany({ where: { status: { not: 'offline' } } })
      const constitution = await db.systemConfig.findUnique({ where: { key: 'constitution' } })
      const maxAgents = constitution ? JSON.parse(constitution.value).maxAgents : 5

      if (activeAgents.length >= maxAgents) {
        return NextResponse.json(
          { error: `Cannot spawn worker: maximum agent limit (${maxAgents}) reached` },
          { status: 403 }
        )
      }

      const newAgent = await db.agent.create({
        data: {
          name,
          type,
          status: 'idle',
          domain: domain || 'general',
          trustScore: 0.5,
        },
      })

      // Log to vault
      await db.vaultEntry.create({
        data: {
          agentId: newAgent.id,
          track: 'CAP',
          category: 'worker_spawn',
          key: `spawn:${name}`,
          value: JSON.stringify({ type, domain: domain || 'general', initialTrust: 0.5 }),
          score: 0.5,
        },
      })

      return NextResponse.json({
        worker: newAgent,
        message: `Worker ${name} spawned successfully`,
      }, { status: 201 })
    }

    if (action === 'update_trust') {
      const { workerId, delta, reason } = body

      if (!workerId || delta === undefined) {
        return NextResponse.json(
          { error: 'Missing required fields: workerId, delta' },
          { status: 400 }
        )
      }

      const agent = await db.agent.findUnique({ where: { id: workerId } })
      if (!agent) {
        return NextResponse.json({ error: 'Worker not found' }, { status: 404 })
      }

      const newTrust = Math.max(0, Math.min(1, agent.trustScore + delta))

      const updated = await db.agent.update({
        where: { id: workerId },
        data: { trustScore: newTrust },
      })

      // Log trust change to vault
      await db.vaultEntry.create({
        data: {
          agentId: workerId,
          track: 'TRUST',
          category: 'trust_update',
          key: `trust:${agent.name}`,
          value: JSON.stringify({ from: agent.trustScore, to: newTrust, delta, reason: reason || 'manual adjustment' }),
          score: newTrust,
        },
      })

      return NextResponse.json({
        worker: updated,
        message: `Trust score for ${agent.name} updated: ${agent.trustScore.toFixed(2)} → ${newTrust.toFixed(2)}`,
      })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: reassign_task, terminate_worker, restart_worker, spawn_worker, update_trust` },
      { status: 400 }
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
