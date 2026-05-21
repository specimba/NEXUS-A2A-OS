import { NextRequest, NextResponse } from 'next/server'
import yaml from 'js-yaml'
import { z } from 'zod'
import { db } from '@/lib/db'

// ────────────────────────────────────────────────────────────────────────────
// /api/config — NEXUS OS config.yaml ingest, parse, validate, persist
// ────────────────────────────────────────────────────────────────────────────
// Accepts either:
//   • multipart/form-data with a `file` field (the user-uploaded config.yaml)
//   • application/json with `{ raw: "<yaml text>" }` (paste-in flow)
//   • application/x-yaml or text/yaml with the YAML directly in the body
// Persists the parsed JSON to SystemConfig[key=nexus.config], and keeps the
// last 10 revisions under SystemConfig[key=nexus.config.history.N] for audit.
// ────────────────────────────────────────────────────────────────────────────

const ConfigSchema = z.object({
  version: z.string().or(z.number()).optional(),
  kernel: z
    .object({
      name: z.string().optional(),
      tier: z.enum(['dev', 'staging', 'prod']).or(z.string()).optional(),
      maxAgents: z.number().int().positive().optional(),
    })
    .partial()
    .optional(),
  agents: z
    .array(
      z.object({
        id: z.string(),
        name: z.string().optional(),
        model: z.string().optional(),
        status: z.enum(['online', 'offline', 'error', 'paused']).or(z.string()).optional(),
        tokenBudget: z.number().int().nonnegative().optional(),
      }),
    )
    .optional(),
  governor: z
    .object({
      approvalThreshold: z.number().min(0).max(1).optional(),
      maxConcurrent: z.number().int().positive().optional(),
      escalationPolicy: z.string().optional(),
    })
    .partial()
    .optional(),
  models: z
    .array(
      z.object({
        id: z.string(),
        tier: z.string().optional(),
        provider: z.string().optional(),
      }),
    )
    .optional(),
  alerts: z
    .object({
      onConfigError: z.boolean().optional(),
      onStreamFailure: z.boolean().optional(),
      slackWebhook: z.string().url().optional(),
    })
    .partial()
    .optional(),
}).passthrough() // allow user-defined extras (forward-compat)

type ParsedConfig = z.infer<typeof ConfigSchema>

interface ParseResult {
  ok: boolean
  parsed?: ParsedConfig
  errors: { path: string; message: string }[]
  warnings: string[]
  raw: string
}

function parseAndValidate(raw: string): ParseResult {
  const errors: { path: string; message: string }[] = []
  const warnings: string[] = []

  if (!raw.trim()) {
    return { ok: false, errors: [{ path: 'root', message: 'Empty document' }], warnings, raw }
  }

  let loaded: unknown
  try {
    loaded = yaml.load(raw, { schema: yaml.JSON_SCHEMA })
  } catch (err) {
    const msg = err instanceof yaml.YAMLException
      ? `${err.reason} (line ${(err.mark?.line ?? 0) + 1}, col ${(err.mark?.column ?? 0) + 1})`
      : err instanceof Error
        ? err.message
        : String(err)
    return { ok: false, errors: [{ path: 'yaml', message: msg }], warnings, raw }
  }

  if (loaded === null || loaded === undefined || typeof loaded !== 'object') {
    return { ok: false, errors: [{ path: 'root', message: 'Expected a YAML mapping at the root' }], warnings, raw }
  }

  const result = ConfigSchema.safeParse(loaded)
  if (!result.success) {
    for (const issue of result.error.issues) {
      errors.push({ path: issue.path.join('.') || 'root', message: issue.message })
    }
    return { ok: false, errors, warnings, raw }
  }

  // Soft warnings (non-blocking)
  if (!result.data.agents || result.data.agents.length === 0) {
    warnings.push('No agents declared — the dashboard will show empty rosters.')
  }
  if (result.data.governor && result.data.governor.approvalThreshold !== undefined && result.data.governor.approvalThreshold < 0.5) {
    warnings.push('Governor approvalThreshold is below 0.5 — most actions will auto-approve.')
  }

  return { ok: true, parsed: result.data, errors, warnings, raw }
}

async function readBody(request: NextRequest): Promise<{ raw: string; filename?: string }> {
  const contentType = request.headers.get('content-type') ?? ''

  if (contentType.includes('multipart/form-data')) {
    const form = await request.formData()
    const file = form.get('file')
    if (!(file instanceof File)) throw new Error('Missing `file` field in form data')
    return { raw: await file.text(), filename: file.name }
  }

  if (contentType.includes('application/json')) {
    const body = await request.json() as { raw?: string; filename?: string }
    if (typeof body.raw !== 'string') throw new Error('Missing `raw` (string) in JSON body')
    return { raw: body.raw, filename: body.filename }
  }

  // text/yaml, application/x-yaml, text/plain, etc.
  return { raw: await request.text() }
}

const HISTORY_LIMIT = 10

export async function POST(request: NextRequest) {
  try {
    const { raw, filename } = await readBody(request)
    const result = parseAndValidate(raw)

    if (!result.ok || !result.parsed) {
      return NextResponse.json(
        { ok: false, errors: result.errors, warnings: result.warnings, filename },
        { status: 400 },
      )
    }

    const payload = JSON.stringify({
      data: result.parsed,
      raw,
      filename: filename ?? null,
      uploadedAt: new Date().toISOString(),
    })

    // Snapshot the current value into history (if any), then write the new one.
    const current = await db.systemConfig.findUnique({ where: { key: 'nexus.config' } })
    if (current) {
      // Shift history slots: nexus.config.history.N → N+1 (cap at HISTORY_LIMIT)
      const history = await db.systemConfig.findMany({
        where: { key: { startsWith: 'nexus.config.history.' } },
        orderBy: { key: 'asc' },
      })
      // Keep only the most recent HISTORY_LIMIT - 1, then push current as history.0
      const kept = history.slice(0, HISTORY_LIMIT - 1)
      await db.$transaction([
        db.systemConfig.deleteMany({ where: { key: { startsWith: 'nexus.config.history.' } } }),
        ...kept.map((h, idx) =>
          db.systemConfig.create({
            data: { key: `nexus.config.history.${idx + 1}`, value: h.value },
          }),
        ),
        db.systemConfig.create({
          data: { key: 'nexus.config.history.0', value: current.value },
        }),
      ])
    }

    await db.systemConfig.upsert({
      where: { key: 'nexus.config' },
      create: { key: 'nexus.config', value: payload },
      update: { value: payload },
    })

    // Audit
    await db.auditLog.create({
      data: {
        actor: 'operator',
        action: 'config.upload',
        target: 'nexus.config',
        metadata: JSON.stringify({ filename: filename ?? null, agents: result.parsed.agents?.length ?? 0 }),
      },
    })

    return NextResponse.json({
      ok: true,
      parsed: result.parsed,
      warnings: result.warnings,
      filename: filename ?? null,
    })
  } catch (error) {
    console.error('[v0] Config upload error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ ok: false, errors: [{ path: 'request', message }] }, { status: 400 })
  }
}

export async function GET() {
  try {
    const [current, history] = await Promise.all([
      db.systemConfig.findUnique({ where: { key: 'nexus.config' } }),
      db.systemConfig.findMany({
        where: { key: { startsWith: 'nexus.config.history.' } },
        orderBy: { key: 'asc' },
      }),
    ])

    const safeParse = (s: string) => {
      try { return JSON.parse(s) } catch { return null }
    }

    return NextResponse.json({
      current: current ? safeParse(current.value) : null,
      history: history.map((h) => ({ slot: h.key, ...safeParse(h.value) })),
    })
  } catch (error) {
    console.error('[v0] Config GET error:', error)
    return NextResponse.json({ current: null, history: [] }, { status: 200 })
  }
}

export async function DELETE() {
  try {
    await db.$transaction([
      db.systemConfig.deleteMany({ where: { key: 'nexus.config' } }),
      db.systemConfig.deleteMany({ where: { key: { startsWith: 'nexus.config.history.' } } }),
      db.auditLog.create({
        data: { actor: 'operator', action: 'config.clear', target: 'nexus.config', metadata: '{}' },
      }),
    ])
    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('[v0] Config DELETE error:', error)
    return NextResponse.json({ ok: false }, { status: 500 })
  }
}
