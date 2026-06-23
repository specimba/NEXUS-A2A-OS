import { NextRequest, NextResponse } from 'next/server'
import { BRAIN_API_BASE } from '@/lib/brain-api/contract'

type BrainRouteContext = { params: Promise<{ path?: string[] }> }

async function resolveParams(context: BrainRouteContext) {
  return context.params
}

function buildTarget(params: { path?: string[] }, request: NextRequest) {
  const suffix = `/${(params.path || []).join('/')}`
  const source = new URL(request.url)
  const target = new URL(`${BRAIN_API_BASE}${suffix}`)
  target.search = source.search
  return target
}

async function forwardReadOnly(request: NextRequest, params: { path?: string[] }) {
  const target = buildTarget(params, request)
  const res = await fetch(target, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  const text = await res.text()
  return new NextResponse(text, {
    status: res.status,
    headers: {
      'content-type': res.headers.get('content-type') || 'application/json',
    },
  })
}

async function forwardMutation(request: NextRequest, params: { path?: string[] }) {
  if (process.env.NEXUS_ENABLE_BRAIN_PROXY_MUTATIONS !== '1') {
    return NextResponse.json(
      { error: 'BRAIN_PROXY_MUTATIONS_DISABLED', message: 'Set NEXUS_ENABLE_BRAIN_PROXY_MUTATIONS=1 to enable guarded mutation proxying.' },
      { status: 403 },
    )
  }
  const apiKey = process.env.NEXUS_BRAIN_API_KEY
  if (!apiKey) {
    return NextResponse.json(
      { error: 'BRAIN_API_KEY_REQUIRED', message: 'NEXUS_BRAIN_API_KEY is required for mutation proxying.' },
      { status: 403 },
    )
  }
  const target = buildTarget(params, request)
  const body = await request.text()
  const res = await fetch(target, {
    method: request.method,
    headers: {
      Accept: 'application/json',
      'Content-Type': request.headers.get('content-type') || 'application/json',
      'X-Api-Key': apiKey,
    },
    body,
    cache: 'no-store',
  })
  const text = await res.text()
  return new NextResponse(text, {
    status: res.status,
    headers: {
      'content-type': res.headers.get('content-type') || 'application/json',
    },
  })
}

export async function GET(request: NextRequest, context: BrainRouteContext) {
  return forwardReadOnly(request, await resolveParams(context))
}

export async function POST(request: NextRequest, context: BrainRouteContext) {
  return forwardMutation(request, await resolveParams(context))
}

export async function PUT(request: NextRequest, context: BrainRouteContext) {
  return forwardMutation(request, await resolveParams(context))
}

export async function DELETE(request: NextRequest, context: BrainRouteContext) {
  return forwardMutation(request, await resolveParams(context))
}
