import { NextResponse } from 'next/server'

interface Dashboard {
  id: string
  name: string
  description: string
  status: 'active' | 'draft' | 'archived'
  widgets: string[]
  lastUpdated: string
  createdAt: string
  template?: string
}

const dashboards: Dashboard[] = [
  {
    id: 'dsh-001',
    name: 'System Health Overview',
    description: 'Real-time system metrics and agent health monitoring',
    status: 'active',
    widgets: ['CPU', 'Memory', 'Latency', 'Agent Status'],
    lastUpdated: 'just now',
    createdAt: '2025-01-15T08:00:00Z',
    template: 'system-health',
  },
  {
    id: 'dsh-002',
    name: 'Token Economics',
    description: 'Token budget, burn rate, and provider cost analysis',
    status: 'active',
    widgets: ['Budget Gauge', 'Burn Chart', 'Cost Table', 'Provider Split'],
    lastUpdated: '5m ago',
    createdAt: '2025-01-14T12:30:00Z',
    template: 'token-economics',
  },
  {
    id: 'dsh-003',
    name: 'Provider Performance',
    description: 'Provider health, latency comparison, and quota tracking',
    status: 'draft',
    widgets: ['Health Grid', 'Latency Chart', 'Quota Bars'],
    lastUpdated: '1h ago',
    createdAt: '2025-01-13T16:45:00Z',
    template: 'provider-performance',
  },
]

export async function GET() {
  return NextResponse.json({
    success: true,
    data: dashboards,
    meta: {
      total: dashboards.length,
      active: dashboards.filter((d) => d.status === 'active').length,
      draft: dashboards.filter((d) => d.status === 'draft').length,
    },
  })
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { name, description, template } = body as {
      name?: string
      description?: string
      template?: string
    }

    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'Dashboard name is required' },
        { status: 400 }
      )
    }

    const newDashboard: Dashboard = {
      id: `dsh-${String(dashboards.length + 1).padStart(3, '0')}`,
      name: name.trim(),
      description: description?.trim() || '',
      status: 'draft',
      widgets: [],
      lastUpdated: 'just now',
      createdAt: new Date().toISOString(),
      template: template || 'blank',
    }

    dashboards.push(newDashboard)

    return NextResponse.json({
      success: true,
      data: newDashboard,
    })
  } catch {
    return NextResponse.json(
      { success: false, error: 'Invalid request body' },
      { status: 400 }
    )
  }
}
