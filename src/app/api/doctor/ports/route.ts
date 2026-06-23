import { NextResponse } from 'next/server'

type PortStatus = 'LIVE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'

interface PortProbe {
  port: number
  expectedOwner: string
  url: string
  status: PortStatus
  httpStatus: number | null
  contentType: string
  detectedOwner: string
  reason: string
}

const PORTS = [
  { port: 7350, expectedOwner: 'Node ModelRelay primary', path: '/v1/models' },
  { port: 7352, expectedOwner: 'Brain API FastAPI', path: '/health' },
  { port: 7355, expectedOwner: 'Python ModelRelay fallback/internal', path: '/health' },
  { port: 7356, expectedOwner: 'Static dashboard', path: '/dashboard.html' },
  { port: 3001, expectedOwner: 'Next dashboard', path: '/' },
]

function classifyOwner(port: number, contentType: string, text: string, data: unknown): { status: PortStatus; detectedOwner: string; reason: string } {
  const preview = text.slice(0, 240).toLowerCase()
  if (port === 7352) {
    if (contentType.includes('application/json') && data && typeof data === 'object') {
      const obj = data as Record<string, unknown>
      if ('model_relay' in obj || 'ws_clients' in obj || obj.status === 'healthy') {
        return { status: 'LIVE', detectedOwner: 'Brain API FastAPI', reason: 'Brain API health JSON signature' }
      }
    }
    if (contentType.includes('text/html') || preview.includes('cannot get')) {
      return { status: 'DEGRADED', detectedOwner: 'HTML/Node app', reason: '7352 returned HTML instead of Brain API JSON' }
    }
  }
  if (contentType.includes('application/json')) {
    return { status: 'LIVE', detectedOwner: 'JSON service', reason: 'JSON response' }
  }
  if (contentType.includes('text/html')) {
    return { status: port === 7356 || port === 3001 ? 'LIVE' : 'DEGRADED', detectedOwner: 'HTML app', reason: 'HTML response' }
  }
  return { status: 'UNKNOWN', detectedOwner: 'unknown service', reason: `content type: ${contentType || 'none'}` }
}

async function probePort(port: (typeof PORTS)[number]): Promise<PortProbe> {
  const url = `http://127.0.0.1:${port.port}${port.path}`
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 2000)
  try {
    const res = await fetch(url, { signal: controller.signal, cache: 'no-store' })
    const contentType = res.headers.get('content-type') || ''
    const text = await res.text()
    let data: unknown = null
    if (contentType.includes('application/json') && text) {
      try {
        data = JSON.parse(text)
      } catch {
        data = null
      }
    }
    const classified = classifyOwner(port.port, contentType, text, data)
    return {
      port: port.port,
      expectedOwner: port.expectedOwner,
      url,
      status: res.ok ? classified.status : port.port === 7352 && contentType.includes('text/html') ? 'DEGRADED' : 'OFFLINE',
      httpStatus: res.status,
      contentType,
      detectedOwner: classified.detectedOwner,
      reason: res.ok ? classified.reason : `HTTP ${res.status}: ${classified.reason}`,
    }
  } catch (error) {
    return {
      port: port.port,
      expectedOwner: port.expectedOwner,
      url,
      status: 'OFFLINE',
      httpStatus: null,
      contentType: '',
      detectedOwner: 'no listener or unreachable',
      reason: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timeout)
  }
}

export async function GET() {
  const ports = await Promise.all(PORTS.map(probePort))
  const brain = ports.find((port) => port.port === 7352)
  const status = brain?.status === 'LIVE' ? 'LIVE' : 'DEGRADED'

  return NextResponse.json({
    status,
    checkedAt: new Date().toISOString(),
    ports,
    nextAction: status === 'LIVE'
      ? 'brain_api_owner_verified'
      : 'relocate_wrong_7352_owner_or_start_brain_api',
  })
}
