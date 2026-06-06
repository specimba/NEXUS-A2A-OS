import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET() {
  try {
    const keys = await db.apiKey.findMany({
      orderBy: [{ provider: 'asc' }, { createdAt: 'desc' }],
    })

    const masked = keys.map(k => ({
      id: k.id,
      provider: k.provider,
      keyPrefix: k.keyPrefix,
      keySuffix: k.keySuffix,
      masked: `${k.keyPrefix}...${k.keySuffix}`,
      isActive: k.isActive,
      health: k.health,
      totalRequests: k.totalRequests,
      total429s: k.total429s,
      successRate: k.successRate,
      lastError: k.lastError,
      cooldownUntil: k.cooldownUntil?.toISOString() ?? null,
      lastUsed: k.lastUsed?.toISOString() ?? null,
      createdAt: k.createdAt.toISOString(),
      updatedAt: k.updatedAt.toISOString(),
    }))

    return NextResponse.json({ keys: masked })
  } catch (error) {
    console.error('[/api/providers/keys GET] Error:', error)
    return NextResponse.json({ error: 'Failed to list keys' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider, apiKey } = body as { provider?: string; apiKey?: string }

    if (!provider || !apiKey) {
      return NextResponse.json({ error: 'Missing provider or apiKey' }, { status: 400 })
    }

    const trimmedKey = apiKey.trim()
    if (trimmedKey.length < 8) {
      return NextResponse.json({ error: 'API key must be at least 8 characters' }, { status: 400 })
    }

    const keyPrefix = trimmedKey.slice(0, 8)
    const keySuffix = trimmedKey.slice(-4)

    // Encrypt the key
    const { encrypt } = await import('@/lib/encryption')
    const encrypted = encrypt(trimmedKey)

    // Find or create key in database
    const existing = await db.apiKey.findFirst({ where: { provider, keySuffix } })

    let savedKey
    if (existing) {
      savedKey = await db.apiKey.update({
        where: { id: existing.id },
        data: {
          keyPrefix,
          encryptedKey: encrypted.encrypted,
          keyIv: encrypted.iv,
          keyTag: encrypted.tag,
          isActive: true,
          health: 'healthy',
          lastError: null,
          updatedAt: new Date(),
        },
      })
    } else {
      savedKey = await db.apiKey.create({
        data: {
          provider,
          keyPrefix,
          keySuffix,
          encryptedKey: encrypted.encrypted,
          keyIv: encrypted.iv,
          keyTag: encrypted.tag,
          isActive: true,
          health: 'healthy',
        },
      })
    }

    // Update process.env for current session availability
    const envVarMap: Record<string, string> = {
      openrouter: 'OPENROUTER_API_KEY',
      openai: 'OPENAI_API_KEY',
      'z-ai': 'ZAI_API_KEY',
      groq: 'GROQ_API_KEY',
      cerebras: 'CEREBRAS_API_KEY',
      mistral: 'MISTRAL_API_KEY',
      codestral: 'CODESTRAL_API_KEY',
      fireworks: 'FIREWORKS_API_KEY',
      jina: 'JINA_API_KEY',
      tavily: 'TAVILY_API_KEY',
      scaleway: 'SCALEWAY_ACCESS_KEY',
      kilocode: 'KILOCODE_API_KEY',
      dashscope: 'DASHSCOPE_API_KEY',
      bitdeer: 'BITDEER_ACCESS_KEY',
    }
    const envVar = envVarMap[provider]
    if (envVar) process.env[envVar] = trimmedKey

    return NextResponse.json({
      success: true,
      key: {
        id: savedKey.id,
        provider: savedKey.provider,
        masked: `${keyPrefix}...${keySuffix}`,
        isActive: savedKey.isActive,
        health: savedKey.health,
      },
      envVar: envVar || '',
      envPersisted: false,
      runtimeInjected: true,
    })
  } catch (error) {
    console.error('[/api/providers/keys POST] Error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to save key' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, provider } = body as { id?: string; provider?: string }

    if (!id && !provider) {
      return NextResponse.json({ error: 'Missing id or provider' }, { status: 400 })
    }

    if (id) {
      const key = await db.apiKey.findUnique({ where: { id } })
      if (!key) return NextResponse.json({ error: 'Not found' }, { status: 404 })
      await db.apiKey.delete({ where: { id } })
      return NextResponse.json({ success: true, deleted: id })
    }

    if (provider) {
      const deleted = await db.apiKey.deleteMany({ where: { provider } })
      return NextResponse.json({ success: true, deletedCount: deleted.count })
    }

    return NextResponse.json({ error: 'Invalid request' }, { status: 400 })
  } catch (error) {
    console.error('[/api/providers/keys DELETE] Error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete' },
      { status: 500 }
    )
  }
}
