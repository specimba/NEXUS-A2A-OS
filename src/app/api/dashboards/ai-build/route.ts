import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

const SUPPORTED_SOURCES = [
  { key: 'agents.byStatus', desc: 'Agents grouped by status (idle/busy/error/offline)' },
  { key: 'agents.byDomain', desc: 'Agents grouped by domain' },
  { key: 'agents.tokenLeaders', desc: 'Top 10 agents by total tokens used' },
  { key: 'agents.list', desc: 'Table of agents with status & tokens' },
  { key: 'agents.totalCount', desc: 'Total agent count' },
  { key: 'tokens.budget', desc: 'Current session token budget usage' },
  { key: 'tokens.history', desc: 'Hourly token usage over last 24 hours' },
  { key: 'tokens.burnRate', desc: 'Current tokens/min burn rate' },
  { key: 'tokens.byModel', desc: 'Tokens grouped by LLM model' },
  { key: 'tokens.lastHour', desc: 'Total tokens consumed in last hour' },
  { key: 'governor.decisions', desc: 'Recent governor decisions table' },
  { key: 'governor.approvalRate', desc: 'ALLOW rate over last 100 decisions' },
  { key: 'governor.byDecision', desc: 'Decisions grouped by ALLOW/DENY/HOLD' },
  { key: 'vault.size', desc: 'Total vault entries' },
  { key: 'vault.byTrack', desc: 'Vault entries by track (EVENT/TRUST/CAP/FAIL/GOV)' },
  { key: 'swarm.byStatus', desc: 'Swarm worker status distribution' },
  { key: 'swarm.trustAverage', desc: 'Average trust score across swarm' },
  { key: 'models.health', desc: 'Model health & latency table' },
  { key: 'models.byProvider', desc: 'Models grouped by provider' },
  { key: 'tests.passRate', desc: 'StressLab pass rate' },
  { key: 'tests.recent', desc: 'Recent stress test runs' },
  { key: 'tests.byStatus', desc: 'Tests grouped by status' },
  { key: 'research.papers', desc: 'Total research papers indexed' },
  { key: 'research.byCategory', desc: 'Papers grouped by arXiv category' },
  { key: 'rateLimit.recent', desc: 'Recent API rate-limit log' },
]

const SUPPORTED_TYPES = ['kpi', 'line', 'bar', 'pie', 'table']

const SYSTEM_PROMPT = `You are a NEXUS OS widget builder. Convert a natural-language request into a JSON widget specification.

Available widget types: ${SUPPORTED_TYPES.join(', ')}.

Available data sources:
${SUPPORTED_SOURCES.map((s) => `- ${s.key}: ${s.desc}`).join('\n')}

Rules:
- "kpi" -> single numeric data sources ending in: budget, burnRate, lastHour, totalCount, size, approvalRate, trustAverage, passRate, papers
- "line" -> timeseries (tokens.history)
- "bar" -> series sources (tokenLeaders, byStatus, swarm.byStatus, tests.byStatus)
- "pie" -> categorical (agents.byStatus, byDomain, byModel, byTrack, byDecision, byProvider, byCategory)
- "table" -> *.list, *.decisions, *.recent, models.health

Respond ONLY with strict JSON (no markdown, no commentary). Shape:
{
  "type": "kpi|line|bar|pie|table",
  "title": "short human title (3-6 words)",
  "subtitle": "optional one-line subtitle or null",
  "dataSource": "<one of the keys above>",
  "width": <1-12 grid columns, default 4 for KPI, 6 for charts, 12 for tables>,
  "height": <1-6 grid rows, default 2 for KPI, 3 for charts, 4 for tables>
}

If the request is ambiguous, pick the closest reasonable match.`

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function POST(req: NextRequest) {
  try {
    const { prompt } = await req.json()
    if (!prompt || typeof prompt !== 'string') {
      return NextResponse.json({ error: 'prompt required' }, { status: 400 })
    }

    const zai = await getZAI()

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: SYSTEM_PROMPT },
        { role: 'user', content: prompt },
      ],
      thinking: { type: 'disabled' },
    })

    const raw = completion.choices?.[0]?.message?.content || ''

    // Strip markdown fences if present
    const cleaned = raw
      .replace(/^```(?:json)?\s*/i, '')
      .replace(/\s*```\s*$/, '')
      .trim()

    let parsed: {
      type?: string
      title?: string
      subtitle?: string | null
      dataSource?: string
      width?: number
      height?: number
    }
    try {
      // try to extract first JSON object
      const start = cleaned.indexOf('{')
      const end = cleaned.lastIndexOf('}')
      const jsonStr = start >= 0 && end > start ? cleaned.slice(start, end + 1) : cleaned
      parsed = JSON.parse(jsonStr)
    } catch {
      return NextResponse.json(
        { error: 'AI returned non-JSON', raw },
        { status: 500 },
      )
    }

    // Validate
    if (!parsed.type || !SUPPORTED_TYPES.includes(parsed.type)) {
      return NextResponse.json(
        { error: `Invalid widget type: ${parsed.type}`, raw },
        { status: 400 },
      )
    }
    if (!parsed.dataSource || !SUPPORTED_SOURCES.find((s) => s.key === parsed.dataSource)) {
      return NextResponse.json(
        { error: `Unknown dataSource: ${parsed.dataSource}`, raw },
        { status: 400 },
      )
    }

    const defaults = {
      kpi: { width: 4, height: 2 },
      line: { width: 6, height: 3 },
      bar: { width: 6, height: 3 },
      pie: { width: 6, height: 3 },
      table: { width: 12, height: 4 },
    } as const

    const def = defaults[parsed.type as keyof typeof defaults]

    return NextResponse.json({
      type: parsed.type,
      title: parsed.title?.slice(0, 64) ?? 'AI Widget',
      subtitle: parsed.subtitle ?? null,
      dataSource: parsed.dataSource,
      width: clamp(parsed.width ?? def.width, 1, 12),
      height: clamp(parsed.height ?? def.height, 1, 6),
      config: {},
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n))
}
