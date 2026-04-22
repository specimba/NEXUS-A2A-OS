/**
 * Enhanced Rate Limiter for NEXUS OS API calls
 *
 * Token bucket algorithm with:
 * - Per-provider rate limiting (RPM + RPD)
 * - Request queue with pending tracking
 * - Exponential backoff with jitter for retries
 * - Request deduplication (same query within TTL returns cached result)
 * - Automatic cooldown when limits approached
 * - Per-key tracking with auto cooldown
 *
 * Auto-resets daily counters at midnight UTC.
 */

import { apiCache } from './api-cache'

// ── Provider Rate Limits ──────────────────────────────────────────

export interface RateLimitConfig {
  rpm: number
  rpd: number
  description: string
  color: string
  baseUrl: string
}

export const PROVIDER_RATE_LIMITS: Record<string, RateLimitConfig> = {
  openrouter: {
    rpm: 20,
    rpd: 200,
    description: 'OpenRouter free tier — very limited daily requests',
    color: '#10b981',
    baseUrl: 'https://openrouter.ai/api/v1',
  },
  jina: {
    rpm: 10,
    rpd: 100,
    description: 'Jina Search API — moderate limits',
    color: '#3b82f6',
    baseUrl: 'https://api.jina.ai/v1',
  },
  kilocode: {
    rpm: 15,
    rpd: 150,
    description: 'Kilocode proxy — limited free tier',
    color: '#8b5cf6',
    baseUrl: 'https://proxy.kilocode.ai/v1',
  },
  cerebras: {
    rpm: 30,
    rpd: 300,
    description: 'Cerebras fast inference — generous free tier',
    color: '#f59e0b',
    baseUrl: 'https://api.cerebras.ai/v1',
  },
  openai: {
    rpm: 3,
    rpd: 30,
    description: 'OpenAI direct — most restrictive for free tier',
    color: '#ef4444',
    baseUrl: 'https://api.openai.com/v1',
  },
}

// ── Token Bucket State ─────────────────────────────────────────────

interface TokenBucket {
  tokens: number
  maxTokens: number
  lastRefill: number
  refillRate: number // tokens per ms
}

interface BucketState {
  minuteBucket: TokenBucket
  dailyCount: number
  dailyMax: number
  lastDailyReset: number
  cooldownUntil: number
  consecutive429s: number
  lastError: string | null
  totalRequests: number
  totalRejected: number
}

// ── Request Queue ──────────────────────────────────────────────────

export interface QueuedRequest {
  id: string
  provider: string
  endpoint: string
  queuedAt: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: unknown
  error?: string
}

interface RequestQueue {
  pending: QueuedRequest[]
  processing: QueuedRequest[]
  completed: QueuedRequest[]
}

// ── Deduplication ──────────────────────────────────────────────────

interface DedupEntry {
  cacheKey: string
  result: unknown
  timestamp: number
  ttl: number
}

// ── In-Memory State ────────────────────────────────────────────────

const buckets: Record<string, BucketState> = {}
const requestQueues: Record<string, RequestQueue> = {}
const dedupStore: Map<string, DedupEntry> = new Map()
const DEDUP_TTL = 60_000
const MAX_DEDUP_ENTRIES = 500
const MAX_QUEUE_SIZE = 50
const MAX_COMPLETED_QUEUE = 20

// ── Utility Functions ──────────────────────────────────────────────

function getMidnightUTC(): number {
  const now = new Date()
  return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
}

function generateId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

/** Exponential backoff with jitter */
export function exponentialBackoff(attempt: number, baseMs: number = 1000, maxMs: number = 60000): number {
  const expDelay = Math.min(baseMs * Math.pow(2, attempt), maxMs)
  const jitter = Math.random() * expDelay * 0.25
  return Math.floor(expDelay + jitter)
}

/** Simple hash for request deduplication */
function hashRequest(provider: string, endpoint: string, body?: string): string {
  const raw = `${provider}:${endpoint}:${body ?? ''}`
  let hash = 0
  for (let i = 0; i < raw.length; i++) {
    const char = raw.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return `dedup_${Math.abs(hash).toString(36)}`
}

// ── Token Bucket Core ──────────────────────────────────────────────

function createTokenBucket(rpm: number): TokenBucket {
  return {
    tokens: rpm,
    maxTokens: rpm,
    lastRefill: Date.now(),
    refillRate: rpm / 60_000,
  }
}

function refillBucket(bucket: TokenBucket): void {
  const now = Date.now()
  const elapsed = now - bucket.lastRefill
  const tokensToAdd = elapsed * bucket.refillRate
  bucket.tokens = Math.min(bucket.maxTokens, bucket.tokens + tokensToAdd)
  bucket.lastRefill = now
}

function consumeToken(bucket: TokenBucket): boolean {
  refillBucket(bucket)
  if (bucket.tokens >= 1) {
    bucket.tokens -= 1
    return true
  }
  return false
}

function getBucket(provider: string): BucketState {
  const key = provider.toLowerCase()
  if (!buckets[key]) {
    const config = PROVIDER_RATE_LIMITS[key] || { rpm: 10, rpd: 200 }
    buckets[key] = {
      minuteBucket: createTokenBucket(config.rpm),
      dailyCount: 0,
      dailyMax: config.rpd,
      lastDailyReset: getMidnightUTC(),
      cooldownUntil: 0,
      consecutive429s: 0,
      lastError: null,
      totalRequests: 0,
      totalRejected: 0,
    }
  }
  return buckets[key]
}

function getQueue(provider: string): RequestQueue {
  const key = provider.toLowerCase()
  if (!requestQueues[key]) {
    requestQueues[key] = { pending: [], processing: [], completed: [] }
  }
  return requestQueues[key]
}

function resetDailyIfNeeded(bucket: BucketState): void {
  const currentMidnight = getMidnightUTC()
  if (currentMidnight > bucket.lastDailyReset) {
    bucket.dailyCount = 0
    bucket.lastDailyReset = currentMidnight
    bucket.consecutive429s = 0
  }
}

// ── Deduplication ──────────────────────────────────────────────────

function checkDedup(cacheKey: string): DedupEntry | null {
  const entry = dedupStore.get(cacheKey)
  if (!entry) return null
  const now = Date.now()
  if (now - entry.timestamp > entry.ttl) {
    dedupStore.delete(cacheKey)
    return null
  }
  return entry
}

function storeDedup(cacheKey: string, result: unknown, ttl: number = DEDUP_TTL): void {
  if (dedupStore.size >= MAX_DEDUP_ENTRIES) {
    const oldest = Array.from(dedupStore.entries())
      .sort((a, b) => a[1].timestamp - b[1].timestamp)
      .slice(0, Math.floor(MAX_DEDUP_ENTRIES * 0.2))
    oldest.forEach(([key]) => dedupStore.delete(key))
  }
  dedupStore.set(cacheKey, { cacheKey, result, timestamp: Date.now(), ttl })
}

function cleanupDedup(): void {
  const now = Date.now()
  for (const [key, entry] of dedupStore.entries()) {
    if (now - entry.timestamp > entry.ttl) {
      dedupStore.delete(key)
    }
  }
}

if (typeof setInterval !== 'undefined') {
  setInterval(cleanupDedup, 300_000)
}

// ── Public API ────────────────────────────────────────────────────

export interface RateLimitResult {
  allowed: boolean
  retryAfterMs: number
  remaining: { rpm: number; rpd: number }
  limits: RateLimitConfig
  isCooldown: boolean
  isDedup: boolean
  dedupResult?: unknown
  queuePosition?: number
  queueId?: string
}

export function checkRateLimit(
  provider: string,
  endpoint?: string,
  body?: string,
  dedupTtl?: number
): RateLimitResult {
  const key = provider.toLowerCase()
  const config = PROVIDER_RATE_LIMITS[key] || {
    rpm: 10, rpd: 200, description: 'Default limits', color: '#6b7280', baseUrl: '',
  }
  const bucket = getBucket(key)

  resetDailyIfNeeded(bucket)

  // Check dedup first
  if (endpoint && dedupTtl !== 0) {
    const cacheKey = hashRequest(key, endpoint, body)
    const dedupEntry = checkDedup(cacheKey)
    if (dedupEntry) {
      return {
        allowed: true,
        retryAfterMs: 0,
        remaining: {
          rpm: Math.floor(bucket.minuteBucket.tokens),
          rpd: Math.max(0, config.rpd - bucket.dailyCount),
        },
        limits: config,
        isCooldown: false,
        isDedup: true,
        dedupResult: dedupEntry.result,
      }
    }
  }

  // Check cooldown
  const now = Date.now()
  if (now < bucket.cooldownUntil) {
    const queueId = enqueueRequest(key, endpoint ?? '/', body)
    return {
      allowed: false,
      retryAfterMs: bucket.cooldownUntil - now,
      remaining: {
        rpm: Math.floor(bucket.minuteBucket.tokens),
        rpd: Math.max(0, config.rpd - bucket.dailyCount),
      },
      limits: config,
      isCooldown: true,
      isDedup: false,
      queueId,
      queuePosition: getQueuePosition(key, queueId),
    }
  }

  const rpmRemaining = Math.floor(bucket.minuteBucket.tokens)
  const rpdRemaining = Math.max(0, config.rpd - bucket.dailyCount)

  // Check token bucket (RPM)
  if (bucket.minuteBucket.tokens < 1) {
    const timeToNextToken = (1 - bucket.minuteBucket.tokens) / bucket.minuteBucket.refillRate
    const retryAfter = Math.ceil(timeToNextToken)
    const queueId = enqueueRequest(key, endpoint ?? '/', body)
    return {
      allowed: false,
      retryAfterMs: Math.max(1000, retryAfter),
      remaining: { rpm: 0, rpd: rpdRemaining },
      limits: config,
      isCooldown: false,
      isDedup: false,
      queueId,
      queuePosition: getQueuePosition(key, queueId),
    }
  }

  // Check daily limit
  if (bucket.dailyCount >= config.rpd) {
    const nextMidnight = getMidnightUTC() + 86_400_000
    bucket.cooldownUntil = nextMidnight
    const queueId = enqueueRequest(key, endpoint ?? '/', body)
    return {
      allowed: false,
      retryAfterMs: nextMidnight - now,
      remaining: { rpm: rpmRemaining, rpd: 0 },
      limits: config,
      isCooldown: true,
      isDedup: false,
      queueId,
      queuePosition: getQueuePosition(key, queueId),
    }
  }

  consumeToken(bucket.minuteBucket)

  return {
    allowed: true,
    retryAfterMs: 0,
    remaining: {
      rpm: Math.floor(bucket.minuteBucket.tokens),
      rpd: rpdRemaining - 1,
    },
    limits: config,
    isCooldown: false,
    isDedup: false,
  }
}

export function recordRequest(provider: string, endpoint?: string, body?: string, result?: unknown, dedupTtl?: number): void {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)

  resetDailyIfNeeded(bucket)
  bucket.dailyCount++
  bucket.totalRequests++

  if (endpoint && dedupTtl !== 0 && result !== undefined) {
    const cacheKey = hashRequest(key, endpoint, body)
    storeDedup(cacheKey, result, dedupTtl ?? DEDUP_TTL)
  }

  if (endpoint && result !== undefined) {
    const cacheKey = `${key}:${endpoint}:${body ?? ''}`
    apiCache.set(cacheKey, result, 300_000)
  }
}

export function enterCooldown(provider: string, retryAfterSeconds: number = 60): void {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)
  bucket.consecutive429s++
  bucket.lastError = `429 Too Many Requests (attempt ${bucket.consecutive429s})`
  const backoffMs = exponentialBackoff(bucket.consecutive429s - 1, Math.max(retryAfterSeconds * 1000, 5000))
  bucket.cooldownUntil = Date.now() + backoffMs
}

export function clearCooldown(provider: string): void {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)
  bucket.cooldownUntil = 0
  bucket.consecutive429s = 0
  bucket.lastError = null
}

export function recordSuccess(provider: string): void {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)
  bucket.consecutive429s = 0
  bucket.lastError = null
}

export function recordError(provider: string, error: string): void {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)
  bucket.lastError = error
}

// ── Queue Management ───────────────────────────────────────────────

function enqueueRequest(provider: string, endpoint: string, body?: string): string {
  const queue = getQueue(provider)
  const id = generateId()
  if (queue.pending.length >= MAX_QUEUE_SIZE) {
    queue.pending.shift()
  }
  queue.pending.push({ id, provider, endpoint, queuedAt: Date.now(), status: 'pending' })
  return id
}

function getQueuePosition(provider: string, queueId: string): number {
  const queue = getQueue(provider)
  const idx = queue.pending.findIndex(r => r.id === queueId)
  return idx >= 0 ? idx + 1 : -1
}

export function dequeueNextRequest(provider: string): QueuedRequest | null {
  const queue = getQueue(provider)
  if (queue.pending.length === 0) return null
  const request = queue.pending.shift()!
  request.status = 'processing'
  queue.processing.push(request)
  return request
}

export function completeQueuedRequest(provider: string, requestId: string, result?: unknown): void {
  const queue = getQueue(provider)
  const idx = queue.processing.findIndex(r => r.id === requestId)
  if (idx >= 0) {
    const request = queue.processing.splice(idx, 1)[0]
    request.status = 'completed'
    request.result = result
    queue.completed.unshift(request)
    if (queue.completed.length > MAX_COMPLETED_QUEUE) queue.completed.pop()
  }
}

export function failQueuedRequest(provider: string, requestId: string, error: string): void {
  const queue = getQueue(provider)
  const idx = queue.processing.findIndex(r => r.id === requestId)
  if (idx >= 0) {
    const request = queue.processing.splice(idx, 1)[0]
    request.status = 'failed'
    request.error = error
    queue.completed.unshift(request)
    if (queue.completed.length > MAX_COMPLETED_QUEUE) queue.completed.pop()
  }
}

// ── Status APIs ────────────────────────────────────────────────────

export function getAllRateLimitStatus(): Record<string, RateLimitResult> {
  const result: Record<string, RateLimitResult> = {}
  for (const provider of Object.keys(PROVIDER_RATE_LIMITS)) {
    result[provider] = checkRateLimit(provider)
  }
  return result
}

export function getRateLimitStatus(provider: string): RateLimitResult {
  return checkRateLimit(provider)
}

export interface ProviderFullStatus {
  provider: string
  config: RateLimitConfig
  rpm: { used: number; limit: number; remaining: number; percentUsed: number }
  rpd: { used: number; limit: number; remaining: number; percentUsed: number }
  isCooldown: boolean
  cooldownUntil: number
  cooldownRemainingMs: number
  consecutive429s: number
  lastError: string | null
  totalRequests: number
  totalRejected: number
  queue: { pending: number; processing: number; completed: number }
  dedup: { size: number; hitRate: number }
  cache: { size: number; hitRate: number; hits: number; misses: number }
  keyHealth: { hasKey: boolean; keyMasked: string; lastUsed: number | null }
}

export function getProviderFullStatus(provider: string): ProviderFullStatus {
  const key = provider.toLowerCase()
  const bucket = getBucket(key)
  const config = PROVIDER_RATE_LIMITS[key] || {
    rpm: 10, rpd: 200, description: 'Default limits', color: '#6b7280', baseUrl: '',
  }
  const queue = getQueue(key)
  const now = Date.now()

  resetDailyIfNeeded(bucket)
  refillBucket(bucket.minuteBucket)

  const rpmUsed = config.rpm - Math.floor(bucket.minuteBucket.tokens)
  const rpdUsed = bucket.dailyCount

  const envKeyMap: Record<string, string> = {
    openrouter: process.env.OPENROUTER_API_KEY ?? '',
    jina: process.env.JINA_API_KEY ?? '',
    kilocode: process.env.KILOCODE_API_KEY ?? '',
    cerebras: process.env.CEREBRAS_API_KEY ?? '',
    openai: process.env.OPENAI_API_KEY ?? '',
  }
  const apiKey = envKeyMap[key] ?? ''
  const hasKey = Boolean(apiKey)
  const keyMasked = hasKey ? apiKey.slice(0, 8) + '...' + apiKey.slice(-4) : 'N/A'

  const cacheStats = apiCache.getStats()

  return {
    provider: key,
    config,
    rpm: {
      used: Math.max(0, rpmUsed),
      limit: config.rpm,
      remaining: Math.max(0, Math.floor(bucket.minuteBucket.tokens)),
      percentUsed: Math.min(100, (rpmUsed / config.rpm) * 100),
    },
    rpd: {
      used: rpdUsed,
      limit: config.rpd,
      remaining: Math.max(0, config.rpd - rpdUsed),
      percentUsed: Math.min(100, (rpdUsed / config.rpd) * 100),
    },
    isCooldown: now < bucket.cooldownUntil,
    cooldownUntil: bucket.cooldownUntil,
    cooldownRemainingMs: Math.max(0, bucket.cooldownUntil - now),
    consecutive429s: bucket.consecutive429s,
    lastError: bucket.lastError,
    totalRequests: bucket.totalRequests,
    totalRejected: bucket.totalRejected,
    queue: {
      pending: queue.pending.length,
      processing: queue.processing.length,
      completed: queue.completed.length,
    },
    dedup: { size: dedupStore.size, hitRate: 0 },
    cache: {
      size: cacheStats.size,
      hitRate: cacheStats.hitRate,
      hits: cacheStats.hits,
      misses: cacheStats.misses,
    },
    keyHealth: {
      hasKey,
      keyMasked,
      lastUsed: bucket.totalRequests > 0 ? Date.now() : null,
    },
  }
}

export function getAllProviderFullStatus(): ProviderFullStatus[] {
  return Object.keys(PROVIDER_RATE_LIMITS).map(getProviderFullStatus)
}

export function getQueueDetails(provider: string): QueuedRequest[] {
  const queue = getQueue(provider)
  return [...queue.processing, ...queue.pending]
}

export function getAllQueueDetails(): Record<string, QueuedRequest[]> {
  const result: Record<string, QueuedRequest[]> = {}
  for (const provider of Object.keys(PROVIDER_RATE_LIMITS)) {
    const details = getQueueDetails(provider)
    if (details.length > 0) result[provider] = details
  }
  return result
}

export function getDedupStats(): { size: number; maxEntries: number } {
  return { size: dedupStore.size, maxEntries: MAX_DEDUP_ENTRIES }
}
