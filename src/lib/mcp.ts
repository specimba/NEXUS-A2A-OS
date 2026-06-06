// Shared helpers for the MCP Hub API + UI.
// Source-of-truth shapes for connection/event JSON serialization.

import { db } from './db'

export type McpStatus = 'connected' | 'connecting' | 'disconnected' | 'error'
export type McpTransport = 'websocket' | 'sse' | 'http'
export type McpEventLevel = 'info' | 'warn' | 'error' | 'debug'

export interface McpConnectionDTO {
  id: string
  name: string
  endpoint: string
  transport: McpTransport
  status: McpStatus
  lastError: string | null
  topicMap: Record<string, string>
  autoReconnect: boolean
  enabled: boolean
  hasApiKey: boolean // never return the key itself
  totalEvents: number
  errorCount: number
  lastEventAt: string | null
  connectedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface McpEventDTO {
  id: string
  connectionId: string
  connectionName?: string
  topic: string
  level: McpEventLevel
  payload: unknown
  occurredAt: string
}

export function serializeConnection(
  c: {
    id: string
    name: string
    endpoint: string
    transport: string
    status: string
    lastError: string | null
    topicMap: string
    autoReconnect: boolean
    enabled: boolean
    apiKeyRef: string | null
    totalEvents: number
    errorCount: number
    lastEventAt: Date | null
    connectedAt: Date | null
    createdAt: Date
    updatedAt: Date
  },
): McpConnectionDTO {
  let topicMap: Record<string, string> = {}
  try {
    topicMap = JSON.parse(c.topicMap ?? '{}')
  } catch {
    topicMap = {}
  }
  return {
    id: c.id,
    name: c.name,
    endpoint: c.endpoint,
    transport: c.transport as McpTransport,
    status: c.status as McpStatus,
    lastError: c.lastError,
    topicMap,
    autoReconnect: c.autoReconnect,
    enabled: c.enabled,
    hasApiKey: !!c.apiKeyRef,
    totalEvents: c.totalEvents,
    errorCount: c.errorCount,
    lastEventAt: c.lastEventAt?.toISOString() ?? null,
    connectedAt: c.connectedAt?.toISOString() ?? null,
    createdAt: c.createdAt.toISOString(),
    updatedAt: c.updatedAt.toISOString(),
  }
}

export function serializeEvent(e: {
  id: string
  connectionId: string
  topic: string
  level: string
  payload: string
  occurredAt: Date
  connection?: { name: string } | null
}): McpEventDTO {
  let payload: unknown = null
  try {
    payload = JSON.parse(e.payload)
  } catch {
    payload = e.payload
  }
  return {
    id: e.id,
    connectionId: e.connectionId,
    connectionName: e.connection?.name,
    topic: e.topic,
    level: e.level as McpEventLevel,
    payload,
    occurredAt: e.occurredAt.toISOString(),
  }
}

// Append an audit log entry. Never throws — audit failures must not break the request.
export async function audit(
  action: string,
  opts: { target?: string; metadata?: Record<string, unknown>; actor?: string; ip?: string } = {},
) {
  try {
    await db.auditLog.create({
      data: {
        actor: opts.actor ?? 'operator',
        action,
        target: opts.target ?? null,
        metadata: JSON.stringify(opts.metadata ?? {}),
        ip: opts.ip ?? null,
      },
    })
  } catch (err) {
    console.error('[v0] audit log failed:', err)
  }
}
