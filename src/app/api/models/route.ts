import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

 
let zaiInstance: any = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function GET() {
  try {
    const models = await db.modelEntry.findMany({ orderBy: { tier: 'desc' } })
    return NextResponse.json({ models })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action, modelId } = body

    if (!action || !modelId) {
      return NextResponse.json(
        { error: 'Missing required fields: action, modelId' },
        { status: 400 }
      )
    }

    const model = await db.modelEntry.findUnique({ where: { id: modelId } })
    if (!model) {
      return NextResponse.json({ error: 'Model not found' }, { status: 404 })
    }

    if (action === 'toggle') {
      const updated = await db.modelEntry.update({
        where: { id: modelId },
        data: { isActive: !model.isActive },
      })
      return NextResponse.json({ model: updated })
    }

    if (action === 'health_check') {
      const startTime = Date.now()
      let newHealth = model.health
      let newLatency = model.latencyMs
      let newSuccessRate = model.successRate
      let isAlive = true

      try {
        // Actually ping the model with a simple test prompt
        const zai = await getZAI()
        const completion = await zai.chat.completions.create({
          messages: [
            { role: 'assistant', content: 'You are a health check endpoint. Respond with exactly: OK' },
            { role: 'user', content: 'Health check: respond with OK' },
          ],
          thinking: { type: 'disabled' },
        })

        const responseTime = Date.now() - startTime
        const response = completion.choices[0]?.message?.content || ''

        // If we got a response, model is healthy
        isAlive = response.length > 0
        newLatency = responseTime

        // Update health based on response
        if (isAlive) {
          // Health increases if response is fast, decreases if slow
          if (responseTime < 2000) {
            newHealth = Math.min(100, model.health + 2)
          } else if (responseTime < 5000) {
            newHealth = Math.min(100, model.health + 1)
          } else {
            newHealth = Math.max(0, model.health - 5)
          }
          newSuccessRate = Math.min(100, model.successRate + 0.1)
        } else {
          newHealth = Math.max(0, model.health - 15)
          newSuccessRate = Math.max(0, model.successRate - 2)
        }
      } catch (error) {
        // Model failed to respond
        isAlive = false
        newHealth = Math.max(0, model.health - 10)
        newSuccessRate = Math.max(0, model.successRate - 1)
        newLatency = Date.now() - startTime
      }

      const updated = await db.modelEntry.update({
        where: { id: modelId },
        data: {
          health: newHealth,
          latencyMs: newLatency,
          successRate: newSuccessRate,
          lastChecked: new Date(),
          isActive: isAlive ? model.isActive : (newHealth < 30 ? false : model.isActive),
          totalCalls: model.totalCalls + 1,
        },
      })

      return NextResponse.json({
        model: updated,
        healthCheck: {
          alive: isAlive,
          responseTime: newLatency,
          previousHealth: model.health,
          newHealth,
        },
      })
    }

    if (action === 'batch_health_check') {
      // Run health check on all active models
      const allModels = await db.modelEntry.findMany({ where: { isActive: true } })
       
      const results: any[] = []

      for (const m of allModels) {
        const startTime = Date.now()
        let newHealth = m.health
        let newLatency = m.latencyMs
        let isAlive = true

        try {
          const zai = await getZAI()
          const completion = await zai.chat.completions.create({
            messages: [
              { role: 'assistant', content: 'You are a health check endpoint. Respond with exactly: OK' },
              { role: 'user', content: 'Health check: respond with OK' },
            ],
            thinking: { type: 'disabled' },
          })

          const response = completion.choices[0]?.message?.content || ''
          const responseTime = Date.now() - startTime
          isAlive = response.length > 0
          newLatency = responseTime

          if (isAlive) {
            newHealth = responseTime < 3000 ? Math.min(100, m.health + 2) : Math.min(100, m.health)
          } else {
            newHealth = Math.max(0, m.health - 15)
          }
        } catch {
          isAlive = false
          newHealth = Math.max(0, m.health - 10)
          newLatency = Date.now() - startTime
        }

        await db.modelEntry.update({
          where: { id: m.id },
          data: {
            health: newHealth,
            latencyMs: newLatency,
            lastChecked: new Date(),
          },
        })

        results.push({
          name: m.name,
          alive: isAlive,
          health: newHealth,
          latencyMs: newLatency,
        })
      }

      return NextResponse.json({ results })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid actions: toggle, health_check, batch_health_check` },
      { status: 400 }
    )
  } catch (error) {
    console.error('Models API error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
