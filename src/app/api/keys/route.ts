/**
 * /api/keys — API Key Management
 *
 * POST   /api/keys          — Save a new API key (encrypts and upserts)
 * GET    /api/keys          — List all keys (masked, never plaintext)
 * DELETE /api/keys?id=xxx   — Delete a key by ID
 */

import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { encrypt, maskKey } from '@/lib/encryption'

// ── GET: List all keys (masked) ──────────────────────────────────

export async function GET() {
  try {
    const keys = await db.apiKey.findMany({
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        provider: true,
        keyPrefix: true,
        keySuffix: true,
        isActive: true,
        health: true,
        totalRequests: true,
        total429s: true,
        successRate: true,
        lastError: true,
        cooldownUntil: true,
        lastUsed: true,
        createdAt: true,
        updatedAt: true,
        // NEVER select encryptedKey, keyIv, keyTag
      },
    })

    return NextResponse.json({
      keys: keys.map(k => ({
        ...k,
        masked: `${k.keyPrefix}...${k.keySuffix}`,
      })),
    })
  } catch (error) {
    console.error('[/api/keys GET] Error:', error)
    return NextResponse.json(
      { error: 'Failed to list API keys', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

// ── POST: Save/Update an API key ─────────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { provider, keyValue } = body

    // Validate inputs
    if (!provider || typeof provider !== 'string') {
      return NextResponse.json({ error: 'provider is required' }, { status: 400 })
    }
    if (!keyValue || typeof keyValue !== 'string') {
      return NextResponse.json({ error: 'keyValue is required' }, { status: 400 })
    }
    if (keyValue.length < 8) {
      return NextResponse.json({ error: 'API key must be at least 8 characters' }, { status: 400 })
    }

    // Derive key identifiers
    const keyPrefix = keyValue.slice(0, 8)
    const keySuffix = keyValue.slice(-4)

    // Encrypt the key
    const { encryptedKey, keyIv, keyTag } = encrypt(keyValue)

    // Upsert into database
    const saved = await db.apiKey.upsert({
      where: {
        provider_keySuffix: {
          provider,
          keySuffix,
        },
      },
      update: {
        keyPrefix,
        encryptedKey,
        keyIv,
        keyTag,
        isActive: true,
        health: 'healthy',
        lastError: null,
        cooldownUntil: null,
      },
      create: {
        provider,
        keyPrefix,
        keySuffix,
        encryptedKey,
        keyIv,
        keyTag,
        isActive: true,
        health: 'healthy',
      },
    })

    // Key is persisted in the database. The in-memory key manager
    // will pick it up on the next server start. For immediate availability,
    // the providers API also reads from the database via loadDatabaseKeys().

    return NextResponse.json({
      success: true,
      key: {
        id: saved.id,
        provider: saved.provider,
        masked: maskKey(keyValue),
        keyPrefix: saved.keyPrefix,
        keySuffix: saved.keySuffix,
        isActive: saved.isActive,
        health: saved.health,
        createdAt: saved.createdAt,
        updatedAt: saved.updatedAt,
      },
    })
  } catch (error) {
    console.error('[/api/keys POST] Error:', error)
    return NextResponse.json(
      { error: 'Failed to save API key', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

// ── DELETE: Remove an API key ─────────────────────────────────────

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get('id')

    if (!id) {
      return NextResponse.json({ error: 'id query parameter is required' }, { status: 400 })
    }

    const deleted = await db.apiKey.delete({
      where: { id },
    })

    // Key deleted from database. Will be reflected on next server start.

    return NextResponse.json({
      success: true,
      deleted: {
        id: deleted.id,
        provider: deleted.provider,
        keySuffix: deleted.keySuffix,
      },
    })
  } catch (error) {
    console.error('[/api/keys DELETE] Error:', error)
    return NextResponse.json(
      { error: 'Failed to delete API key', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
