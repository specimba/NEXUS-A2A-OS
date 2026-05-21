import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// GET /api/foundry — Return all FoundryAgent records
export async function GET() {
  try {
    const agents = await db.foundryAgent.findMany({
      orderBy: { port: 'asc' },
    })
    return NextResponse.json({ agents })
  } catch (error) {
    console.error('Foundry GET error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

// POST /api/foundry — Actions: register, heartbeat, invoke
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (!action) {
      return NextResponse.json({ error: 'Missing action field' }, { status: 400 })
    }

    switch (action) {
      // ── Register or update a Foundry Agent ──
      case 'register': {
        const { nexusId, displayName, modelRef, role, port, capabilities } = body
        if (!nexusId || !displayName || !modelRef || !port) {
          return NextResponse.json(
            { error: 'Missing required fields: nexusId, displayName, modelRef, port' },
            { status: 400 }
          )
        }

        const agent = await db.foundryAgent.upsert({
          where: { nexusId },
          update: {
            displayName,
            modelRef,
            role: role || '',
            port,
            capabilities: capabilities ? JSON.stringify(capabilities) : '[]',
            status: 'online',
            lastHeartbeat: new Date(),
          },
          create: {
            nexusId,
            displayName,
            modelRef,
            role: role || '',
            port,
            capabilities: capabilities ? JSON.stringify(capabilities) : '[]',
            status: 'online',
            health: 1.0,
            lastHeartbeat: new Date(),
          },
        })

        return NextResponse.json({ success: true, agent })
      }

      // ── Heartbeat — update agent status and lastHeartbeat ──
      case 'heartbeat': {
        const { nexusId, health } = body
        if (!nexusId) {
          return NextResponse.json({ error: 'Missing nexusId' }, { status: 400 })
        }

        const existing = await db.foundryAgent.findUnique({ where: { nexusId } })
        if (!existing) {
          return NextResponse.json({ error: `Agent ${nexusId} not found` }, { status: 404 })
        }

        const agent = await db.foundryAgent.update({
          where: { nexusId },
          data: {
            status: 'online',
            lastHeartbeat: new Date(),
            ...(health !== undefined ? { health: Math.min(1, Math.max(0, health)) } : {}),
          },
        })

        return NextResponse.json({ success: true, agent })
      }

      // ── Invoke — send a prompt to the agent via z-ai-web-dev-sdk ──
      case 'invoke': {
        const { nexusId, prompt } = body
        if (!nexusId || !prompt) {
          return NextResponse.json({ error: 'Missing nexusId or prompt' }, { status: 400 })
        }

        const agent = await db.foundryAgent.findUnique({ where: { nexusId } })
        if (!agent) {
          return NextResponse.json({ error: `Agent ${nexusId} not found` }, { status: 404 })
        }

        // Mark agent as busy
        await db.foundryAgent.update({
          where: { nexusId },
          data: { status: 'busy' },
        })

        try {
          // Use z-ai-web-dev-sdk to invoke the model
          const { ZAIWebDevSDK } = await import('z-ai-web-dev-sdk')
          const sdk = new ZAIWebDevSDK()
          const startTime = Date.now()

          const result = await sdk.chat.completions.create({
            model: agent.modelRef,
            messages: [
              {
                role: 'system',
                content: `You are ${agent.displayName}, a Foundry Agent with role: ${agent.role}. Respond concisely and helpfully.`,
              },
              { role: 'user', content: prompt },
            ],
          })

          const responseTimeMs = Date.now() - startTime
          const responseText = result.choices?.[0]?.message?.content || 'No response generated'

          // Mark agent back to online
          await db.foundryAgent.update({
            where: { nexusId },
            data: { status: 'online' },
          })

          return NextResponse.json({
            success: true,
            agent: nexusId,
            model: agent.modelRef,
            response: responseText,
            responseTimeMs,
          })
        } catch (invokeError) {
          // Mark agent back to online even on error
          await db.foundryAgent.update({
            where: { nexusId },
            data: { status: 'online' },
          })

          const errMsg = invokeError instanceof Error ? invokeError.message : 'Unknown invoke error'
          return NextResponse.json({ error: errMsg }, { status: 500 })
        }
      }

      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 })
    }
  } catch (error) {
    console.error('Foundry POST error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
