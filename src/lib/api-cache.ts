/**
 * Simple in-memory API cache for NEXUS OS rate limiter.
 * Stores API responses with TTL-based expiration and LRU eviction.
 */

/** Cache TTL presets (in milliseconds) */
export const CACHE_TTL = {
  /** Short TTL for real-time data (1 minute) */
  SHORT: 60_000,
  /** Default TTL for most API responses (5 minutes) */
  DEFAULT: 300_000,
  /** Long TTL for static/slowly-changing data (30 minutes) */
  LONG: 1_800_000,
  /** Very long TTL for rarely-changing data (1 hour) */
  VERY_LONG: 3_600_000,
} as const

interface CacheEntry<T = unknown> {
  value: T
  expiresAt: number
  createdAt: number
  size: number // approximate size in bytes
}

class ApiCache {
  private cache = new Map<string, CacheEntry>()
  private hits = 0
  private misses = 0
  private evictions = 0
  private maxSize: number
  private maxMemoryBytes: number

  constructor(maxSize: number = 500, maxMemoryMB: number = 50) {
    this.maxSize = maxSize
    this.maxMemoryBytes = maxMemoryMB * 1024 * 1024
  }

  set<T = unknown>(key: string, value: T, ttlMs: number): void {
    // Evict if at capacity
    if (this.cache.size >= this.maxSize) {
      this.evictOldest()
    }

    const size = this.estimateSize(value)
    this.cache.set(key, {
      value,
      expiresAt: Date.now() + ttlMs,
      createdAt: Date.now(),
      size,
    })
  }

  get<T = unknown>(key: string): T | undefined {
    const entry = this.cache.get(key)
    if (!entry) {
      this.misses++
      return undefined
    }
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key)
      this.misses++
      return undefined
    }
    this.hits++
    return entry.value as T
  }

  has(key: string): boolean {
    const entry = this.cache.get(key)
    if (!entry) return false
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key)
      return false
    }
    return true
  }

  delete(key: string): boolean {
    return this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
    this.hits = 0
    this.misses = 0
    this.evictions = 0
  }

  purgeExpired(): number {
    const now = Date.now()
    let purged = 0
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiresAt) {
        this.cache.delete(key)
        purged++
      }
    }
    return purged
  }

  getStats(): {
    size: number
    maxSize: number
    hits: number
    misses: number
    hitRate: number
    evictions: number
  } {
    const total = this.hits + this.misses
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hits: this.hits,
      misses: this.misses,
      hitRate: total > 0 ? this.hits / total : 0,
      evictions: this.evictions,
    }
  }

  private evictOldest(): void {
    let oldestKey: string | null = null
    let oldestTime = Infinity
    for (const [key, entry] of this.cache.entries()) {
      if (entry.createdAt < oldestTime) {
        oldestTime = entry.createdAt
        oldestKey = key
      }
    }
    if (oldestKey) {
      this.cache.delete(oldestKey)
      this.evictions++
    }
  }

  private estimateSize(value: unknown): number {
    try {
      return JSON.stringify(value).length * 2 // rough UTF-16 estimate
    } catch {
      return 1024 // default 1KB estimate
    }
  }
}

/** Singleton API cache instance */
export const apiCache = new ApiCache()

/**
 * Build a cache key from provider, endpoint, and body.
 * Uses a simple hash for the body to keep keys short.
 */
export function buildCacheKey(provider: string, endpoint: string, body?: string): string {
  let bodyHash = 0
  if (body) {
    for (let i = 0; i < body.length; i++) {
      const char = body.charCodeAt(i)
      bodyHash = ((bodyHash << 5) - bodyHash) + char
      bodyHash = bodyHash & bodyHash
    }
  }
  return `${provider}:${endpoint}:${Math.abs(bodyHash).toString(36)}`
}

// Purge expired entries every 5 minutes
if (typeof setInterval !== 'undefined') {
  setInterval(() => apiCache.purgeExpired(), 300_000)
}
