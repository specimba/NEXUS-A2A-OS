import { NextRequest, NextResponse } from 'next/server'
import type { WidgetType, DataSource } from '@/lib/dashboard-types'

interface AiWidgetSuggestion {
  type: WidgetType
  dataSource: DataSource
  title: string
}

// Keyword-to-widget mapping for heuristic AI generation
const KEYWORD_MAP: Record<string, AiWidgetSuggestion[]> = {
  token: [
    { type: 'token_gauge', dataSource: 'tokens', title: 'Token Budget' },
    { type: 'line_chart', dataSource: 'tokens', title: 'Token Usage Over Time' },
    { type: 'kpi', dataSource: 'tokens', title: 'Token Consumption' },
  ],
  budget: [
    { type: 'token_gauge', dataSource: 'tokens', title: 'Budget Gauge' },
    { type: 'metric', dataSource: 'tokens', title: 'Budget Utilization' },
  ],
  cost: [
    { type: 'token_gauge', dataSource: 'tokens', title: 'Cost Overview' },
    { type: 'bar_chart', dataSource: 'tokens', title: 'Cost Breakdown' },
  ],
  agent: [
    { type: 'agent_health', dataSource: 'agents', title: 'Agent Health Overview' },
    { type: 'kpi', dataSource: 'agents', title: 'Active Agents' },
    { type: 'status_grid', dataSource: 'agents', title: 'Agent Status Grid' },
  ],
  worker: [
    { type: 'kpi', dataSource: 'agents', title: 'Worker Count' },
    { type: 'status_grid', dataSource: 'agents', title: 'Worker Status' },
  ],
  trust: [
    { type: 'agent_health', dataSource: 'agents', title: 'Agent Trust Scores' },
    { type: 'metric', dataSource: 'agents', title: 'Average Trust' },
  ],
  model: [
    { type: 'model_relay', dataSource: 'models', title: 'Model Relay Status' },
    { type: 'kpi', dataSource: 'models', title: 'Model Health' },
    { type: 'pie_chart', dataSource: 'models', title: 'Model Distribution' },
  ],
  provider: [
    { type: 'model_relay', dataSource: 'providers', title: 'Provider Health' },
    { type: 'status_grid', dataSource: 'providers', title: 'Provider Status' },
  ],
  relay: [
    { type: 'model_relay', dataSource: 'models', title: 'Model Relay' },
  ],
  govern: [
    { type: 'kpi', dataSource: 'governor', title: 'Governor Compliance' },
    { type: 'bar_chart', dataSource: 'governor', title: 'Governor Decisions' },
  ],
  compliance: [
    { type: 'kpi', dataSource: 'governor', title: 'Compliance Score' },
    { type: 'metric', dataSource: 'governor', title: 'Compliance Rate' },
  ],
  swarm: [
    { type: 'kpi', dataSource: 'swarm', title: 'Swarm Workers' },
    { type: 'status_grid', dataSource: 'swarm', title: 'Swarm Status' },
  ],
  system: [
    { type: 'kpi', dataSource: 'system', title: 'System Health Score' },
    { type: 'status_grid', dataSource: 'system', title: 'Pillar Status' },
    { type: 'line_chart', dataSource: 'system', title: 'Health Over Time' },
  ],
  health: [
    { type: 'kpi', dataSource: 'system', title: 'Health Score' },
    { type: 'status_grid', dataSource: 'system', title: 'Health Pillars' },
  ],
  uptime: [
    { type: 'kpi', dataSource: 'system', title: 'System Uptime' },
    { type: 'metric', dataSource: 'system', title: 'Uptime Target' },
  ],
  alert: [
    { type: 'alert_feed', dataSource: 'system', title: 'Recent Alerts' },
  ],
  error: [
    { type: 'alert_feed', dataSource: 'system', title: 'Error Feed' },
    { type: 'line_chart', dataSource: 'ratelimit', title: 'Error Trends' },
  ],
  rate: [
    { type: 'kpi', dataSource: 'ratelimit', title: 'Rate Limit Status' },
    { type: 'bar_chart', dataSource: 'ratelimit', title: 'Rate Limit Events' },
  ],
  research: [
    { type: 'metric', dataSource: 'research', title: 'Research Papers' },
    { type: 'kpi', dataSource: 'research', title: 'Vetted Papers' },
  ],
  overview: [
    { type: 'kpi', dataSource: 'system', title: 'System Overview' },
    { type: 'status_grid', dataSource: 'agents', title: 'Agent Status' },
    { type: 'token_gauge', dataSource: 'tokens', title: 'Token Budget' },
  ],
  dashboard: [
    { type: 'kpi', dataSource: 'system', title: 'System Health' },
    { type: 'line_chart', dataSource: 'tokens', title: 'Token Usage' },
    { type: 'agent_health', dataSource: 'agents', title: 'Agent Overview' },
  ],
}

function generateWidgetsFromPrompt(prompt: string): AiWidgetSuggestion[] {
  const lower = prompt.toLowerCase()
  const seen = new Set<string>()
  const results: AiWidgetSuggestion[] = []

  for (const [keyword, suggestions] of Object.entries(KEYWORD_MAP)) {
    if (lower.includes(keyword)) {
      for (const s of suggestions) {
        const key = `${s.type}-${s.dataSource}`
        if (!seen.has(key)) {
          seen.add(key)
          results.push(s)
        }
      }
    }
  }

  // Default fallback
  if (results.length === 0) {
    results.push(
      { type: 'kpi', dataSource: 'system', title: 'System Overview' },
      { type: 'line_chart', dataSource: 'tokens', title: 'Token Trends' },
      { type: 'status_grid', dataSource: 'agents', title: 'Agent Status' }
    )
  }

  return results.slice(0, 6)
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const prompt = body.prompt as string | undefined

    if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      )
    }

    const widgets = generateWidgetsFromPrompt(prompt)

    return NextResponse.json({ widgets })
  } catch {
    return NextResponse.json(
      { error: 'Failed to generate widgets' },
      { status: 500 }
    )
  }
}
