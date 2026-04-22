/**
 * API Key Manager for NEXUS OS
 *
 * Manages API keys for multiple providers with:
 * - Secure key storage (keys in env vars only, never exposed to client)
 * - Key rotation support — cycle through multiple keys per provider
 * - Per-key health tracking (requests remaining, last error, cooldown)
 * - Automatic key rotation on 429 errors
 *
 * IMPORTANT: API keys are NEVER sent to the client.
 * Only masked versions (sk-or-...XXXX) are exposed via APIs.
 */

import { enterCooldown, clearCooldown } from './rate-limiter'

// ── Types ──────────────────────────────────────────────────────────

export interface KeyInfo {
  id: string
  provider: string
  masked: string
  isActive: boolean
  health: 'healthy' | 'degraded' | 'rate_limited' | 'error' | 'no_key'
  requestsMade: number
  requestsRemaining: number
  lastError: string | null
  cooldownUntil: number
  lastUsed: number | null
  totalRequests: number
  total429s: number
  successRate: number
}

export interface ProviderKeyStatus {
  provider: string
  activeKeyIndex: number
  keys: KeyInfo[]
  totalKeys: number
  healthyKeys: number
  hasAvailableKey: boolean
}

// ── Key Store ──────────────────────────────────────────────────────

interface StoredKey {
  id: string
  provider: string
  keyValue: string
  masked: string
  isActive: boolean
  health: KeyInfo['health']
  requestsMade: number
  lastError: string | null
  cooldownUntil: number
  lastUsed: number | null
  totalRequests: number
  total429s: number
  totalSuccesses: number
}

// ── Environment Variable Mapping ───────────────────────────────────

const ENV_KEY_MAP: Record<string, string[]> = {
  openrouter: ['OPENROUTER_API_KEY', 'OPENROUTER_API_KEY_2', 'OPENROUTER_API_KEY_3'],
  jina: ['JINA_API_KEY', 'JINA_API_KEY_2'],
  kilocode: ['KILOCODE_API_KEY', 'KILOCODE_API_KEY_2'],
  cerebras: ['CEREBRAS_API_KEY', 'CEREBRAS_API_KEY_2'],
  openai: ['OPENAI_API_KEY', 'OPENAI_API_KEY_2'],
}

// ── In-Memory State ────────────────────────────────────────────────

const keyStore: Map<string, StoredKey[]> = new Map()
let initialized = false

// ── Initialization ─────────────────────────────────────────────────

function maskKey(key: string): string {
  if (key.length <= 12) return '***'
  return key.slice(0, 8) + '...' + key.slice(-4)
}

function initializeKeys(): void {
  if (initialized) return

  for (const [provider, envVars] of Object.entries(ENV_KEY_MAP)) {
    const keys: StoredKey[] = []

    for (const envVar of envVars) {
      const keyValue = process.env[envVar]
      if (keyValue) {
        keys.push({
          id: `${provider}_${keys.length + 1}`,
          provider,
          keyValue,
          masked: maskKey(keyValue),
          isActive: true,
          health: 'healthy',
          requestsMade: 0,
          lastError: null,
          cooldownUntil: 0,
          lastUsed: null,
          totalRequests: 0,
          total429s: 0,
          totalSuccesses: 0,
        })
      }
    }

    if (keys.length === 0) {
      keys.push({
        id: `${provider}_0`,
        provider,
        keyValue: '',
        masked: 'N/A',
        isActive: false,
        health: 'no_key',
        requestsMade: 0,
        lastError: 'No API key configured',
        cooldownUntil: 0,
        lastUsed: null,
        totalRequests: 0,
        total429s: 0,
        totalSuccesses: 0,
      })
    }

    keyStore.set(provider, keys)
  }

  initialized = true
}

// ── Public API ────────────────────────────────────────────────────

/** Get the active API key for a provider. SERVER SIDE ONLY. */
export function getActiveKey(provider: string): string | null {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys) return null

  const now = Date.now()
  const availableKey = keys.find(
    k => k.isActive && k.keyValue && now >= k.cooldownUntil && k.health !== 'no_key'
  )

  return availableKey?.keyValue ?? null
}

/** Get the active key info (masked) for a provider. Safe for client. */
export function getActiveKeyInfo(provider: string): KeyInfo | null {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys) return null

  const activeKey = keys.find(k => k.isActive && k.keyValue)
  if (!activeKey) return null

  return toKeyInfo(activeKey)
}

/** Rotate to the next available key for a provider. */
export function rotateKey(provider: string, failedKeyId?: string): KeyInfo | null {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys || keys.length <= 1) return null

  const now = Date.now()

  if (failedKeyId) {
    const failedKey = keys.find(k => k.id === failedKeyId)
    if (failedKey) {
      failedKey.health = 'rate_limited'
      failedKey.cooldownUntil = now + 60_000
      failedKey.total429s++
      failedKey.lastError = '429 Too Many Requests'
      enterCooldown(provider, 60)
    }
  }

  const availableKey = keys.find(
    k => k.id !== failedKeyId && k.isActive && k.keyValue && now >= k.cooldownUntil
  )

  if (availableKey) {
    availableKey.health = 'healthy'
    return toKeyInfo(availableKey)
  }

  const sortedByCooldown = [...keys]
    .filter(k => k.isActive && k.keyValue)
    .sort((a, b) => a.cooldownUntil - b.cooldownUntil)

  if (sortedByCooldown.length > 0) {
    return toKeyInfo(sortedByCooldown[0])
  }

  return null
}

/** Record a successful request with a key. */
export function recordKeySuccess(provider: string, keyId?: string): void {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys) return

  const key = keyId
    ? keys.find(k => k.id === keyId)
    : keys.find(k => k.isActive && k.keyValue)

  if (key) {
    key.totalRequests++
    key.totalSuccesses++
    key.requestsMade++
    key.lastUsed = Date.now()
    key.health = 'healthy'
    key.lastError = null
    clearCooldown(provider)
  }
}

/** Record a 429 error with a key and trigger rotation. */
export function recordKey429(provider: string, retryAfterSeconds: number = 60): KeyInfo | null {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys) return null

  const activeKey = keys.find(k => k.isActive && k.keyValue)
  if (!activeKey) return null

  activeKey.health = 'rate_limited'
  activeKey.cooldownUntil = Date.now() + retryAfterSeconds * 1000
  activeKey.total429s++
  activeKey.lastError = `429 Too Many Requests (retry after ${retryAfterSeconds}s)`

  enterCooldown(provider, retryAfterSeconds)

  return rotateKey(provider, activeKey.id)
}

/** Record an error (non-429) with a key. */
export function recordKeyError(provider: string, error: string, keyId?: string): void {
  initializeKeys()
  const keys = keyStore.get(provider)
  if (!keys) return

  const key = keyId
    ? keys.find(k => k.id === keyId)
    : keys.find(k => k.isActive && k.keyValue)

  if (key) {
    key.totalRequests++
    key.lastError = error
    key.lastUsed = Date.now()
    if (error.includes('401') || error.includes('403')) {
      key.health = 'error'
      key.isActive = false
    } else {
      key.health = 'degraded'
    }
  }
}

/** Get full key status for a provider. Safe for client. */
export function getProviderKeyStatus(provider: string): ProviderKeyStatus {
  initializeKeys()
  const keys = keyStore.get(provider) ?? []
  const now = Date.now()

  const keyInfos = keys.map(toKeyInfo)

  const activeIdx = keys.findIndex(k => k.isActive && now >= k.cooldownUntil && k.keyValue)
  const activeKeyIndex = activeIdx >= 0 ? activeIdx : 0

  const healthyKeys = keyInfos.filter(k => k.health === 'healthy').length
  const hasAvailableKey = keyInfos.some(k => k.isActive && k.health !== 'no_key' && now >= k.cooldownUntil)

  return {
    provider,
    activeKeyIndex,
    keys: keyInfos,
    totalKeys: keys.filter(k => k.keyValue).length,
    healthyKeys,
    hasAvailableKey,
  }
}

/** Get key status for all providers. Safe for client. */
export function getAllProviderKeyStatus(): Record<string, ProviderKeyStatus> {
  initializeKeys()
  const result: Record<string, ProviderKeyStatus> = {}
  for (const provider of Object.keys(ENV_KEY_MAP)) {
    result[provider] = getProviderKeyStatus(provider)
  }
  return result
}

/** Get the authorization header for a provider's API request. */
export function getAuthHeaders(provider: string): Record<string, string> | null {
  const key = getActiveKey(provider)
  if (!key) return null

  switch (provider) {
    case 'openrouter':
      return {
        'Authorization': `Bearer ${key}`,
        'HTTP-Referer': 'https://nexus-os.dev',
        'X-Title': 'NEXUS OS v3.0',
      }
    case 'jina':
    case 'cerebras':
    case 'openai':
    case 'kilocode':
    default:
      return { 'Authorization': `Bearer ${key}` }
  }
}

// ── Helper ─────────────────────────────────────────────────────────

function toKeyInfo(stored: StoredKey): KeyInfo {
  const successRate = stored.totalRequests > 0
    ? Math.round((stored.totalSuccesses / stored.totalRequests) * 100)
    : 100

  const requestsRemaining = stored.health === 'rate_limited' || stored.health === 'error'
    ? 0
    : 100

  return {
    id: stored.id,
    provider: stored.provider,
    masked: stored.masked,
    isActive: stored.isActive,
    health: stored.health,
    requestsMade: stored.requestsMade,
    requestsRemaining,
    lastError: stored.lastError,
    cooldownUntil: stored.cooldownUntil,
    lastUsed: stored.lastUsed,
    totalRequests: stored.totalRequests,
    total429s: stored.total429s,
    successRate,
  }
}
