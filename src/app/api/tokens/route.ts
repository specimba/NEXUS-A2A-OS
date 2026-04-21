import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const budget = await db.sessionBudget.findFirst({ where: { isActive: true } })
    const usageLogs = await db.tokenUsageLog.findMany({
      take: 100,
      orderBy: { createdAt: 'desc' },
    })
    const agents = await db.agent.findMany({
      select: { name: true, totalTokens: true },
    })
    return NextResponse.json({ budget, usageLogs, agentUsage: agents })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action !== 'log_usage') {
      return NextResponse.json(
        { error: `Unknown action: ${action}. Valid action: log_usage` },
        { status: 400 }
      )
    }

    const { agentId, model, promptTokens, completionTokens, cost, apiEndpoint } = body

    if (!model || promptTokens === undefined || completionTokens === undefined) {
      return NextResponse.json(
        { error: 'Missing required fields: model, promptTokens, completionTokens' },
        { status: 400 }
      )
    }

    const totalTokens = (promptTokens as number) + (completionTokens as number)

    // Create the usage log entry
    const usageLog = await db.tokenUsageLog.create({
      data: {
        agentId: agentId ?? null,
        model,
        promptTokens,
        completionTokens,
        totalTokens,
        cost: cost ?? 0.0,
        apiEndpoint: apiEndpoint ?? null,
      },
    })

    // Update the active session budget
    const activeBudget = await db.sessionBudget.findFirst({ where: { isActive: true } })
    if (activeBudget) {
      const newUsed = activeBudget.usedBudget + totalTokens
      const newRemaining = Math.max(0, activeBudget.totalBudget - newUsed)
      await db.sessionBudget.update({
        where: { id: activeBudget.id },
        data: {
          usedBudget: newUsed,
          remainingBudget: newRemaining,
        },
      })
    }

    // Update the agent's totalTokens if agentId was provided
    if (agentId) {
      const agent = await db.agent.findUnique({ where: { id: agentId } })
      if (agent) {
        await db.agent.update({
          where: { id: agentId },
          data: {
            totalTokens: agent.totalTokens + totalTokens,
            lastActive: new Date(),
          },
        })
      }
    }

    return NextResponse.json({ usageLog }, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
