import { db } from '@/lib/db'
import { serializeEvent } from '@/lib/mcp'
import { NextRequest } from 'next/server'

// GET /api/mcp/stream?connectionId=  → Server-Sent Events for live MCP events.
// We poll the database every 1.5s and push new rows downstream. This is
// intentionally simple/portable so it works on serverless without needing a
// real pub/sub broker. The client can also fall back to polling /api/mcp/events.
export async function GET(req: NextRequest) {
  const url = new URL(req.url)
  const connectionId = url.searchParams.get('connectionId') ?? undefined

  const encoder = new TextEncoder()
  let lastSeen = new Date()
  let timer: ReturnType<typeof setInterval> | null = null

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      // SSE preamble
      controller.enqueue(encoder.encode(`event: ready\ndata: {"ts":"${new Date().toISOString()}"}\n\n`))

      const tick = async () => {
        try {
          const events = await db.mcpEvent.findMany({
            where: {
              occurredAt: { gt: lastSeen },
              ...(connectionId ? { connectionId } : {}),
            },
            include: { connection: { select: { name: true } } },
            orderBy: { occurredAt: 'asc' },
            take: 50,
          })
          if (events.length > 0) {
            lastSeen = events[events.length - 1].occurredAt
            for (const e of events) {
              const dto = serializeEvent(e)
              controller.enqueue(encoder.encode(`event: mcp\ndata: ${JSON.stringify(dto)}\n\n`))
            }
          } else {
            // Comment line as keep-alive — prevents proxies dropping the conn.
            controller.enqueue(encoder.encode(`: ping ${Date.now()}\n\n`))
          }
        } catch (err) {
          controller.enqueue(
            encoder.encode(`event: error\ndata: ${JSON.stringify({ error: String(err) })}\n\n`),
          )
        }
      }
      timer = setInterval(tick, 1500)

      // Stop polling when the client disconnects.
      req.signal.addEventListener('abort', () => {
        if (timer) clearInterval(timer)
        try {
          controller.close()
        } catch {
          /* already closed */
        }
      })
    },
    cancel() {
      if (timer) clearInterval(timer)
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
