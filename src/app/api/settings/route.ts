import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

const PROVIDER_KEYS: Record<string, string[]> = {
  openrouter: ['OPENROUTER_API_KEY'],
  openai: ['OPENAI_API_KEY'],
  cerebras: ['CEREBRAS_API_KEY'],
  jina: ['JINA_API_KEY'],
  kilocode: ['KILOCODE_API_KEY'],
  zai: ['ZAI_API_KEY', 'ZAI_SDK_KEY'],
  brain: ['NEXUS_BRAIN_API_KEY'],
}

function maskValue(value: string | undefined): string | null {
  if (!value) return null
  if (value.length <= 8) return 'set'
  return `${value.slice(0, 4)}...${value.slice(-4)}`
}

function hasEnv(keys: string[]) {
  return keys.some((key) => !!process.env[key])
}

function envMasked(keys: string[]) {
  const found = keys.map((key) => process.env[key]).find(Boolean)
  return maskValue(found)
}

function dbMasked(settings: Record<string, string>, keys: string[]) {
  const found = keys.map((key) => settings[key]).find(Boolean)
  return maskValue(found)
}

export async function GET() {
  try {
    const configs = await db.systemConfig.findMany()
    const settings: Record<string, string> = {}
    for (const c of configs) {
      settings[c.key] = c.value
    }

    const providerStatus = Object.fromEntries(
      Object.entries(PROVIDER_KEYS).map(([provider, keys]) => {
        const env = hasEnv(keys)
        const stored = keys.some((key) => !!settings[key])
        return [
          provider,
          {
            env,
            db: stored,
            configured: env || stored,
            masked: envMasked(keys) || dbMasked(settings, keys),
          },
        ]
      })
    )
    const providers = Object.fromEntries(
      Object.entries(providerStatus).map(([provider, status]) => [
        provider === 'zai' ? 'zai_sdk' : provider,
        status.configured,
      ])
    )
    const maskedSettings = Object.fromEntries(
      Object.entries(settings).map(([key, value]) => [key, key.toUpperCase().includes('KEY') ? maskValue(value) : value])
    )
    const configured = Object.values(providerStatus).some((status) => status.configured)

    return NextResponse.json({
      settings: maskedSettings,
      configured,
      providers,
      providerStatus,
    })
  } catch (error) {
    console.error('Settings GET error:', error)
    return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { key, value } = body as { key: string; value: string }

    if (!key || !value) {
      return NextResponse.json({ error: 'Key and value are required' }, { status: 400 })
    }

    await db.systemConfig.upsert({
      where: { key },
      update: { value },
      create: { key, value },
    })

    return NextResponse.json({ success: true, key })
  } catch (error) {
    console.error('Settings PUT error:', error)
    return NextResponse.json({ error: 'Failed to save setting' }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const key = searchParams.get('key')

    if (!key) {
      return NextResponse.json({ error: 'Key is required' }, { status: 400 })
    }

    await db.systemConfig.deleteMany({ where: { key } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Settings DELETE error:', error)
    return NextResponse.json({ error: 'Failed to delete setting' }, { status: 500 })
  }
}
