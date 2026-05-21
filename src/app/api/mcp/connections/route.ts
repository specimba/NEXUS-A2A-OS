import { db } from '@/lib/db'
import { audit, serializeConnection } from '@/lib/mcp'
import { createHash } from 'crypto'
import { NextRequest, NextResponse } from 'next/server'

const MAX_NAME_LENGTH = 120
const MAX_ENDPOINT_LENGTH = 2048
const MAX_API_KEY_LENGTH = 512
const MAX_TOPIC_MAP_KEYS = 50
const MAX_TOPIC_MAP_KEY_LENGTH = 120
const MAX_TOPIC_MAP_VALUE_LENGTH = 256
const VALID_TRANSPORTS = new Set(['websocket', 'sse', 'http'])

export async function GET() {
  try {
    const connections = await db.mcpConnection.findMany({
      orderBy: [{ enabled: 'desc' }, { createdAt: 'desc' }],
    })
    return NextResponse.json(connections.map(serializeConnection))
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const {
      name,
      endpoint,
      transport = 'websocket',
      apiKey,
      topicMap = {},
      autoReconnect = true,
    } = body as {
      name?: string
      endpoint?: string
      transport?: 'websocket' | 'sse' | 'http'
      apiKey?: string
      topicMap?: Record<string, string>
      autoReconnect?: boolean
    }

    const normalizedName = typeof name === 'string' ? name.trim() : ''
    const normalizedEndpoint = typeof endpoint === 'string' ? endpoint.trim() : ''
    if (!normalizedName || !normalizedEndpoint) {
      return NextResponse.json({ error: 'name and endpoint are required' }, { status: 400 })
    }
    if (normalizedName.length > MAX_NAME_LENGTH || normalizedEndpoint.length > MAX_ENDPOINT_LENGTH) {
      return NextResponse.json({ error: 'name or endpoint is too long' }, { status: 400 })
    }
    if (!VALID_TRANSPORTS.has(transport)) {
      return NextResponse.json({ error: 'invalid transport' }, { status: 400 })
    }
    if (typeof autoReconnect !== 'boolean') {
      return NextResponse.json({ error: 'autoReconnect must be boolean' }, { status: 400 })
    }
    // Basic endpoint shape validation.
    if (!/^(ws|wss|http|https):\/\//i.test(normalizedEndpoint)) {
      return NextResponse.json(
        { error: 'endpoint must start with ws://, wss://, http://, or https://' },
        { status: 400 },
      )
    }
    if (apiKey && apiKey.length > MAX_API_KEY_LENGTH) {
      return NextResponse.json({ error: 'apiKey is too long' }, { status: 400 })
    }
    const topicMapResult = normalizeTopicMap(topicMap)
    if ('error' in topicMapResult) {
      return NextResponse.json({ error: topicMapResult.error }, { status: 400 })
    }

    const created = await db.mcpConnection.create({
      data: {
        name: normalizedName,
        endpoint: normalizedEndpoint,
        transport,
        apiKeyRef: apiKey ? apiKeyFingerprint(apiKey) : null,
        topicMap: JSON.stringify(topicMapResult.value),
        autoReconnect,
        status: 'disconnected',
      },
    })
    await audit('mcp.create', {
      target: created.id,
      metadata: { name: normalizedName, endpoint: normalizedEndpoint, transport },
    })
    return NextResponse.json(serializeConnection(created), { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function apiKeyFingerprint(apiKey: string): string {
  const hash = createHash('sha256').update(apiKey).digest('hex').slice(0, 16)
  return `sha256:${hash}`
}

function normalizeTopicMap(
  topicMap: unknown,
): { value: Record<string, string> } | { error: string } {
  if (!topicMap || typeof topicMap !== 'object' || Array.isArray(topicMap)) {
    return { error: 'topicMap must be an object' }
  }
  const entries = Object.entries(topicMap as Record<string, unknown>)
  if (entries.length > MAX_TOPIC_MAP_KEYS) {
    return { error: 'topicMap has too many entries' }
  }
  const normalized: Record<string, string> = {}
  for (const [key, value] of entries) {
    if (!key || key.length > MAX_TOPIC_MAP_KEY_LENGTH) {
      return { error: 'topicMap contains an invalid key' }
    }
    if (typeof value !== 'string' || value.length > MAX_TOPIC_MAP_VALUE_LENGTH) {
      return { error: 'topicMap values must be bounded strings' }
    }
    normalized[key] = value
  }
  return { value: normalized }
}
