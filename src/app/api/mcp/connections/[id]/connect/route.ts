import { db } from '@/lib/db'
import { audit, serializeConnection } from '@/lib/mcp'
import { NextRequest, NextResponse } from 'next/server'

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]'])

// POST /api/mcp/connections/[id]/connect  → flips status to "connecting" then
// "connected" after a short health probe. We don't actually open a server-side
// WebSocket here — the live stream is handled by /api/mcp/stream + the client
// MCP library. This endpoint is the "intent to connect" + status record.
export async function POST(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const conn = await db.mcpConnection.findUnique({ where: { id } })
    if (!conn) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    // Mark as connecting first so the UI can render a transitional state on poll.
    await db.mcpConnection.update({
      where: { id },
      data: { status: 'connecting', lastError: null },
    })

    // Probe the endpoint with a HEAD/GET when it's HTTP(S); WebSocket endpoints
    // can't be probed from a Node fetch, so we trust the configured URL and
    // mark connected. The real connection is opened by the client.
    let status: 'connected' | 'error' = 'connected'
    let lastError: string | null = null
    try {
      if (/^https?:\/\//i.test(conn.endpoint)) {
        const probeUrl = conn.endpoint
        if (!isProbeAllowed(probeUrl)) {
          status = 'error'
          lastError = 'Endpoint probe blocked by allowlist'
        } else {
          const res = await fetch(probeUrl, {
            method: 'HEAD',
            signal: AbortSignal.timeout(5000),
          }).catch(() => fetch(probeUrl, { method: 'GET', signal: AbortSignal.timeout(5000) }))
          if (!res.ok && res.status >= 500) {
            status = 'error'
            lastError = `Probe returned ${res.status}`
          }
        }
      }
    } catch (err) {
      status = 'error'
      lastError = err instanceof Error ? err.message : String(err)
    }

    const updated = await db.mcpConnection.update({
      where: { id },
      data: {
        status,
        lastError,
        connectedAt: status === 'connected' ? new Date() : conn.connectedAt,
      },
    })

    // Record the connection event in the event log so it shows up in Live Events.
    await db.mcpEvent.create({
      data: {
        connectionId: id,
        topic: status === 'connected' ? 'connection.opened' : 'connection.failed',
        level: status === 'connected' ? 'info' : 'error',
        payload: JSON.stringify({ endpoint: conn.endpoint, error: lastError }),
      },
    })
    await audit(status === 'connected' ? 'mcp.connect' : 'mcp.connect.failed', {
      target: id,
      metadata: { error: lastError },
    })

    return NextResponse.json(serializeConnection(updated))
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function isProbeAllowed(endpoint: string): boolean {
  try {
    const url = new URL(endpoint)
    const host = url.hostname.toLowerCase()
    if (LOOPBACK_HOSTS.has(host)) return true

    const allowlist = (process.env.NEXUS_MCP_PROBE_ALLOWLIST ?? '')
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
    return allowlist.includes(host)
  } catch {
    return false
  }
}
