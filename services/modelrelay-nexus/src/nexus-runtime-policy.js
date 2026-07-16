import { timingSafeEqual } from 'node:crypto'

const DEFAULT_CIRCUIT_MS = 60_000
const MIN_CIRCUIT_MS = 1_000
const MAX_CIRCUIT_MS = 24 * 60 * 60 * 1000
// NEXUS_ENTITLEMENT_AWARE: access failures are neither transient outages nor
// permanent configuration facts. Keep each exact route out of automatic
// selection for a bounded period, then permit a low-frequency recheck.
const DEFAULT_ACCESS_BLOCK_MS = 15 * 60 * 1000
const MIN_ACCESS_BLOCK_MS = 60 * 1000
const REQUEST_TERMINAL_STATUSES = new Set([400, 409, 422])
const OFFER_FAILOVER_STATUSES = new Set([401, 402, 403, 404, 429])
const ACCESS_FAILURE_STATUSES = Object.freeze({
  401: 'auth_required',
  402: 'payment_required',
  403: 'access_denied',
})
const ACCESS_FAILURE_STATUS_VALUES = new Set(Object.values(ACCESS_FAILURE_STATUSES))
const NVIDIA_MIN_START_INTERVAL_MS = 7_500
const NVIDIA_RATE_LIMIT_FLOOR_MS = 75_000
const DEFAULT_CANARY_WINDOW_MS = 60 * 60 * 1000
const DEFAULT_CANARY_MIN_SPACING_MS = 10 * 60 * 1000
const DEFAULT_CANARY_PROVIDER_COOLDOWN_MS = 30 * 60 * 1000
const NVIDIA_CANARY_PROVIDER_COOLDOWN_MS = 60 * 60 * 1000
const MIN_OFFER_FIRST_BYTE_MS = 6_000
const MAX_OFFER_FIRST_BYTE_MS = 30_000
const DEFAULT_UNVERIFIED_FIRST_BYTE_MS = 12_000
const NVIDIA_UNVERIFIED_FIRST_BYTE_MS = 18_000
const NVIDIA_HEALTHY_FIRST_BYTE_FLOOR_MS = 12_000
const NVIDIA_MEDIUM_CONTEXT_FIRST_BYTE_FLOOR_MS = 18_000
const NVIDIA_LARGE_CONTEXT_FIRST_BYTE_FLOOR_MS = 25_000
const RATE_LIMIT_SCOPES = new Set(['account', 'connection', 'model', 'offer'])
const RATE_LIMIT_SCOPE_HEADERS = ['x-nexus-rate-limit-scope', 'x-ratelimit-scope', 'x-rate-limit-scope', 'ratelimit-scope']

export const PROVIDER_STATES = Object.freeze({ CLOSED: 'CLOSED', DEGRADED: 'DEGRADED', OPEN: 'OPEN' })

export const NEXUS_SAFE_RUNTIME = process.env.MODELRELAY_NEXUS_SAFE_RUNTIME === '1'

// `nexus-resilient` is intentionally a virtual, opt-in client alias rather
// than a new default.  It is a narrow fallback lane for callers that prefer a
// clean 503 over an unverified catalogue route.  The lane names existing
// provider families only; it never discovers or registers an offer.
export const NEXUS_RESILIENT_MODEL_ID = 'nexus-resilient'
export const NEXUS_RESILIENT_PROVIDER_LANE = Object.freeze([
  'openai-compatible:ollama-cloud',
  'openai-compatible:mistral',
  'codestral',
  'opencode',
  'kilocode',
  'openrouter',
  'nvidia',
])
export const NEXUS_RESILIENT_OBSERVATION_TTL_MS = 15 * 60 * 1000
export const NEXUS_RESILIENT_WARM_OBSERVATION_TTL_MS = 48 * 60 * 60 * 1000
// A known-good fallback should be refreshed while it is still recent enough
// to represent current provider behavior.  The longer warm window is only a
// request-time safety net; it must not turn old catalogue history into an
// automatic canary target.
const NEXUS_RESILIENT_CANARY_REFRESH_MAX_AGE_MS = 2 * 60 * 60 * 1000
const NEXUS_RESILIENT_CONTEXT_RESERVE_TOKENS = 4_096
const NEXUS_RESILIENT_UNKNOWN_CONTEXT_MAX_PROMPT_TOKENS = 16_384

const NEXUS_GLM52_PRIMARY_MODEL_IDS = new Set([
  'glm-5.2',
  'z-ai/glm-5.2',
  'zai-org/glm-5.2',
])

function normalizeResilientIdentity(value) {
  return String(value || '').trim().toLowerCase()
}

export function isNexusResilientModelId(value) {
  return normalizeResilientIdentity(value) === NEXUS_RESILIENT_MODEL_ID
}

function abortError(reason = 'aborted') {
  if (reason instanceof Error) return reason
  return new DOMException(String(reason), 'AbortError')
}

function boundedMs(value, fallback = DEFAULT_CIRCUIT_MS) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.min(MAX_CIRCUIT_MS, Math.max(MIN_CIRCUIT_MS, Math.round(numeric)))
}

function boundedAccessBlockMs(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return DEFAULT_ACCESS_BLOCK_MS
  return Math.min(MAX_CIRCUIT_MS, Math.max(MIN_ACCESS_BLOCK_MS, Math.round(numeric)))
}

/**
 * Converts an upstream access response into a display-safe, non-secret health
 * state.  A 403 can have several provider-specific causes, so it is reported
 * as access denied rather than pretending it is definitively a billing fault.
 */
export function classifyOfferAccessFailure(status) {
  return ACCESS_FAILURE_STATUSES[Number(status)] || null
}

export function isOfferAccessFailureStatus(status) {
  return ACCESS_FAILURE_STATUS_VALUES.has(String(status || '').trim().toLowerCase())
}

export function parseRetryAfterMs(value, now = Date.now()) {
  if (value == null || String(value).trim() === '') return DEFAULT_CIRCUIT_MS
  const text = String(value).trim()
  const seconds = Number(text)
  if (Number.isFinite(seconds)) return boundedMs(seconds * 1000)
  const absolute = Date.parse(text)
  if (Number.isFinite(absolute)) return boundedMs(absolute - now)
  return DEFAULT_CIRCUIT_MS
}

function headerValue(headers, names) {
  for (const name of names) {
    const value = headers?.get?.(name)
    if (value != null && String(value).trim() !== '') return String(value).trim()
    if (headers && typeof headers === 'object') {
      const entry = Object.entries(headers).find(([key]) => key.toLowerCase() === name)
      if (entry && String(entry[1]).trim() !== '') return String(entry[1]).trim()
    }
  }
  return ''
}

function normalizedRateLimitScope(scope, offer = {}) {
  const candidate = String(scope || '').trim().toLowerCase()
  if (!RATE_LIMIT_SCOPES.has(candidate)) return 'offer'
  if (candidate === 'account' && !offer.accountKey) return 'offer'
  if (candidate === 'connection' && !offer.connectionKey) return 'offer'
  if (candidate === 'model' && !offer.modelId) return 'offer'
  return candidate
}

export function classifyRateLimitScope(headers, offer = {}) {
  return normalizedRateLimitScope(headerValue(headers, RATE_LIMIT_SCOPE_HEADERS), offer)
}

function rateLimitKey(offer = {}, requestedScope = 'offer') {
  const scope = normalizedRateLimitScope(requestedScope, offer)
  const providerKey = String(offer.providerKey || '')
  if (scope === 'account') return JSON.stringify([scope, providerKey, String(offer.accountKey)])
  if (scope === 'connection') return JSON.stringify([scope, providerKey, String(offer.connectionKey)])
  if (scope === 'model') return JSON.stringify([scope, providerKey, String(offer.modelId)])
  return JSON.stringify([
    scope,
    providerKey,
    String(offer.offerId || ''),
    String(offer.accountKey || ''),
    String(offer.connectionKey || ''),
    String(offer.modelId || ''),
  ])
}

function offerIdentityKey(offer = {}) {
  // Circuit selection happens before account/connection resolution.  A
  // provider-qualified route must therefore have the same identity at both
  // selection and failure time; account-aware 429 handling remains isolated
  // in rateLimitKey instead.
  return offerAccessIdentityKey(offer)
}

// Route identity intentionally excludes account and connection fingerprints.
// Selection happens before an account token is resolved; using the same stable
// provider-qualified route key at selection and failure time avoids a 402/403
// being immediately selected again with an incomplete identity.
function offerAccessIdentityKey(offer = {}) {
  return JSON.stringify([
    String(offer.providerKey || ''),
    String(offer.offerId || offer.modelId || ''),
  ])
}

function applicableRateLimitKeys(offer = {}) {
  const keys = [rateLimitKey(offer, 'offer')]
  if (offer.accountKey) keys.push(rateLimitKey(offer, 'account'))
  if (offer.connectionKey) keys.push(rateLimitKey(offer, 'connection'))
  if (offer.modelId) keys.push(rateLimitKey(offer, 'model'))
  return keys
}

function isNvidiaProvider(providerKey) {
  const value = String(providerKey || '').toLowerCase()
  return value === 'nvidia' || value.startsWith('nvidia-') || value.startsWith('nvidia:')
}

function isProviderTimeout(error) {
  const code = String(error?.code || '')
  return error?.name === 'TimeoutError'
    || code === 'NEXUS_FIRST_BYTE_TIMEOUT'
    || code === 'NEXUS_TOTAL_TIMEOUT'
}

function sleepWithSignal(ms, signal) {
  if (signal?.aborted) return Promise.reject(abortError(signal.reason))
  return new Promise((resolve, reject) => {
    const cleanup = () => signal?.removeEventListener('abort', onAbort)
    const timer = setTimeout(() => {
      cleanup()
      resolve()
    }, Math.max(0, ms))
    const onAbort = () => {
      clearTimeout(timer)
      cleanup()
      reject(abortError(signal.reason))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

class Semaphore {
  constructor(limit) {
    this.limit = Math.max(1, Number(limit) || 1)
    this.active = 0
    this.queue = []
  }

  async acquire(signal) {
    if (signal?.aborted) throw abortError(signal.reason)
    if (this.active < this.limit) {
      this.active += 1
      return this.releaseFactory()
    }
    return new Promise((resolve, reject) => {
      const waiter = { resolve, reject, signal, onAbort: null }
      waiter.onAbort = () => {
        const index = this.queue.indexOf(waiter)
        if (index >= 0) this.queue.splice(index, 1)
        reject(abortError(signal.reason))
      }
      signal?.addEventListener('abort', waiter.onAbort, { once: true })
      this.queue.push(waiter)
    })
  }

  releaseFactory() {
    let released = false
    return () => {
      if (released) return
      released = true
      this.active = Math.max(0, this.active - 1)
      while (this.queue.length > 0) {
        const waiter = this.queue.shift()
        waiter.signal?.removeEventListener('abort', waiter.onAbort)
        if (waiter.signal?.aborted) {
          waiter.reject(abortError(waiter.signal.reason))
          continue
        }
        this.active += 1
        waiter.resolve(this.releaseFactory())
        break
      }
    }
  }
}

export class ProviderCircuitOpenError extends Error {
  constructor(providerKey, retryAfterMs) {
    super(`Provider circuit is open for ${providerKey} (${retryAfterMs}ms remaining).`)
    this.name = 'ProviderCircuitOpenError'
    this.code = 'NEXUS_PROVIDER_CIRCUIT_OPEN'
    this.providerKey = providerKey
    this.retryAfterMs = retryAfterMs
  }
}

export class ProviderRateLimitError extends Error {
  constructor(providerKey, scope, retryAfterMs) {
    super(`Provider offer is rate-limited for ${providerKey} at ${scope} scope (${retryAfterMs}ms remaining).`)
    this.name = 'ProviderRateLimitError'
    this.code = 'NEXUS_PROVIDER_OFFER_RATE_LIMITED'
    this.providerKey = providerKey
    this.scope = scope
    this.retryAfterMs = retryAfterMs
  }
}

export class ProviderOfferCircuitOpenError extends Error {
  constructor(offer, retryAfterMs) {
    const providerKey = String(offer?.providerKey || '')
    const modelId = String(offer?.modelId || '')
    super(`Provider offer circuit is open for ${providerKey}/${modelId} (${retryAfterMs}ms remaining).`)
    this.name = 'ProviderOfferCircuitOpenError'
    this.code = 'NEXUS_PROVIDER_OFFER_CIRCUIT_OPEN'
    this.providerKey = providerKey
    this.modelId = modelId
    this.retryAfterMs = retryAfterMs
  }
}

export class ProviderOfferAccessBlockedError extends Error {
  constructor(offer, accessClass, retryAfterMs) {
    const providerKey = String(offer?.providerKey || '')
    const modelId = String(offer?.modelId || '')
    super(`Provider offer access is blocked for ${providerKey}/${modelId} (${accessClass}; ${retryAfterMs}ms remaining).`)
    this.name = 'ProviderOfferAccessBlockedError'
    this.code = 'NEXUS_PROVIDER_OFFER_ACCESS_BLOCKED'
    this.providerKey = providerKey
    this.modelId = modelId
    this.accessClass = accessClass
    this.retryAfterMs = retryAfterMs
  }
}

export class ProviderAttemptBudgetError extends Error {
  constructor(limit) {
    super(`Provider request attempt budget exhausted (${limit} total calls).`)
    this.name = 'ProviderAttemptBudgetError'
    this.code = 'NEXUS_PROVIDER_ATTEMPT_BUDGET_EXHAUSTED'
    this.limit = limit
  }
}

export class ProviderAttemptBudget {
  constructor(limit = 2) {
    this.limit = Math.min(2, Math.max(1, Number(limit) || 2))
    this.used = 0
  }

  get remaining() {
    return Math.max(0, this.limit - this.used)
  }

  async run(operation) {
    if (this.remaining === 0) throw new ProviderAttemptBudgetError(this.limit)
    this.used += 1
    return operation()
  }
}

export class ProviderGovernor {
  constructor(options = {}) {
    this.defaultConcurrency = Math.max(1, Number(options.defaultConcurrency) || 2)
    this.providerConcurrency = {
      mistral: 1,
      nvidia: 1,
      ...(options.providerConcurrency || {}),
    }
    this.providerPacingMs = {
      nvidia: NVIDIA_MIN_START_INTERVAL_MS,
      ...(options.providerPacingMs || {}),
    }
    this.providerOpenMs = boundedMs(options.providerOpenMs, DEFAULT_CIRCUIT_MS)
    this.degradedAfter = Math.max(1, Number(options.degradedAfter) || 1)
    this.openAfter = Math.max(this.degradedAfter + 1, Number(options.openAfter) || 2)
    this.now = options.now || Date.now
    this.sleep = options.sleep || sleepWithSignal
    this.semaphores = new Map()
    this.circuits = new Map()
    this.providerHealth = new Map()
    this.offerCircuits = new Map()
    this.offerHealth = new Map()
    this.offerAccessBlocks = new Map()
    this.rateLimits = new Map()
    this.lastStarts = new Map()
  }

  concurrencyFor(providerKey) {
    return Math.max(1, Number(this.providerConcurrency[providerKey]) || this.defaultConcurrency)
  }

  pacingFor(providerKey) {
    return Math.max(0, Number(this.providerPacingMs[providerKey]) || 0)
  }

  semaphoreFor(providerKey) {
    if (!this.semaphores.has(providerKey)) {
      this.semaphores.set(providerKey, new Semaphore(this.concurrencyFor(providerKey)))
    }
    return this.semaphores.get(providerKey)
  }

  circuitRemainingMs(providerKey) {
    const until = this.circuits.get(providerKey) || 0
    const remaining = Math.max(0, until - this.now())
    if (until > 0 && remaining === 0) {
      this.circuits.delete(providerKey)
      this.providerHealth.set(providerKey, {
        failures: this.degradedAfter,
        state: PROVIDER_STATES.DEGRADED,
      })
    }
    return remaining
  }

  providerState(providerKey) {
    if (this.circuitRemainingMs(providerKey) > 0) return PROVIDER_STATES.OPEN
    return this.providerHealth.get(providerKey)?.state || PROVIDER_STATES.CLOSED
  }

  isAvailable(providerKey) {
    return this.circuitRemainingMs(providerKey) === 0
  }

  openCircuit(providerKey, retryAfterMs = DEFAULT_CIRCUIT_MS) {
    const until = this.now() + boundedMs(retryAfterMs)
    this.circuits.set(providerKey, Math.max(until, this.circuits.get(providerKey) || 0))
    this.providerHealth.set(providerKey, {
      failures: this.openAfter,
      state: PROVIDER_STATES.OPEN,
    })
    return until
  }

  recordTransientFailure(providerKey, retryAfterMs = this.providerOpenMs) {
    if (this.circuitRemainingMs(providerKey) > 0) return PROVIDER_STATES.OPEN
    const previous = this.providerHealth.get(providerKey)?.failures || 0
    const failures = previous + 1
    if (failures >= this.openAfter) {
      this.openCircuit(providerKey, retryAfterMs)
      return PROVIDER_STATES.OPEN
    }
    this.providerHealth.set(providerKey, { failures, state: PROVIDER_STATES.DEGRADED })
    return PROVIDER_STATES.DEGRADED
  }

  recordSuccess(providerKey) {
    this.circuits.delete(providerKey)
    this.providerHealth.delete(providerKey)
    return PROVIDER_STATES.CLOSED
  }

  recordStatus(providerKey, status, options = {}) {
    const code = Number(status)
    if (code >= 200 && code < 400) return this.recordSuccess(providerKey)
    if (code >= 500) return this.recordTransientFailure(providerKey, options.retryAfterMs)
    return this.providerState(providerKey)
  }

  offerCircuitRemainingMs(offer) {
    const key = offerIdentityKey(offer)
    const until = this.offerCircuits.get(key) || 0
    const remaining = Math.max(0, until - this.now())
    if (until > 0 && remaining === 0) {
      this.offerCircuits.delete(key)
      this.offerHealth.set(key, {
        failures: this.degradedAfter,
        state: PROVIDER_STATES.DEGRADED,
      })
    }
    return remaining
  }

  offerAccessStatus(offer) {
    const key = offerAccessIdentityKey(offer)
    const block = this.offerAccessBlocks.get(key)
    if (!block) return { accessClass: null, until: 0, remainingMs: 0 }
    const remainingMs = Math.max(0, Number(block.until || 0) - this.now())
    if (remainingMs === 0) {
      this.offerAccessBlocks.delete(key)
      return { accessClass: null, until: 0, remainingMs: 0 }
    }
    return {
      accessClass: String(block.accessClass || 'access_denied'),
      until: Number(block.until || 0),
      remainingMs,
    }
  }

  blockOfferAccess(offer, accessClass, retryAfterMs) {
    const normalizedClass = classifyOfferAccessFailure(accessClass) || String(accessClass || '').trim().toLowerCase()
    if (!ACCESS_FAILURE_STATUS_VALUES.has(normalizedClass)) {
      throw new TypeError('accessClass must be auth_required, payment_required, or access_denied')
    }
    const key = offerAccessIdentityKey(offer)
    const until = this.now() + boundedAccessBlockMs(retryAfterMs)
    const previous = this.offerAccessBlocks.get(key)
    const nextUntil = Math.max(until, Number(previous?.until || 0))
    const next = { accessClass: normalizedClass, until: nextUntil }
    this.offerAccessBlocks.set(key, next)
    return {
      ...next,
      remainingMs: Math.max(0, nextUntil - this.now()),
    }
  }

  clearOfferAccessBlock(offer) {
    this.offerAccessBlocks.delete(offerAccessIdentityKey(offer))
  }

  offerState(offer) {
    if (this.offerAccessStatus(offer).remainingMs > 0) return PROVIDER_STATES.OPEN
    if (this.offerCircuitRemainingMs(offer) > 0) return PROVIDER_STATES.OPEN
    return this.offerHealth.get(offerIdentityKey(offer))?.state || PROVIDER_STATES.CLOSED
  }

  openOfferCircuit(offer, retryAfterMs = DEFAULT_CIRCUIT_MS) {
    const key = offerIdentityKey(offer)
    const until = this.now() + boundedMs(retryAfterMs)
    this.offerCircuits.set(key, Math.max(until, this.offerCircuits.get(key) || 0))
    this.offerHealth.set(key, {
      failures: this.openAfter,
      state: PROVIDER_STATES.OPEN,
    })
    return until
  }

  recordOfferTransientFailure(offer, retryAfterMs = this.providerOpenMs) {
    if (this.offerCircuitRemainingMs(offer) > 0) return PROVIDER_STATES.OPEN
    const key = offerIdentityKey(offer)
    const previous = this.offerHealth.get(key)?.failures || 0
    const failures = previous + 1
    if (failures >= this.openAfter) {
      this.openOfferCircuit(offer, retryAfterMs)
      return PROVIDER_STATES.OPEN
    }
    this.offerHealth.set(key, { failures, state: PROVIDER_STATES.DEGRADED })
    return PROVIDER_STATES.DEGRADED
  }

  recordOfferSuccess(offer) {
    const key = offerIdentityKey(offer)
    this.offerCircuits.delete(key)
    this.offerHealth.delete(key)
    this.clearOfferAccessBlock(offer)
    return PROVIDER_STATES.CLOSED
  }

  recordOfferStatus(offer, status, options = {}) {
    const code = Number(status)
    if (code >= 200 && code < 400) return this.recordOfferSuccess(offer)
    const accessClass = classifyOfferAccessFailure(code)
    if (accessClass) {
      this.blockOfferAccess(offer, accessClass, options.retryAfterMs)
      return PROVIDER_STATES.OPEN
    }
    if (OFFER_FAILOVER_STATUSES.has(code)) {
      this.openOfferCircuit(offer, options.retryAfterMs)
      return PROVIDER_STATES.OPEN
    }
    if (code >= 500) return this.recordOfferTransientFailure(offer, options.retryAfterMs)
    return this.offerState(offer)
  }

  rateLimitStatus(offer) {
    let status = { remainingMs: 0, scope: 'offer' }
    for (const key of applicableRateLimitKeys(offer)) {
      const entry = this.rateLimits.get(key)
      if (!entry) continue
      const candidate = Math.max(0, entry.until - this.now())
      if (candidate === 0) this.rateLimits.delete(key)
      else if (candidate > status.remainingMs) status = { remainingMs: candidate, scope: entry.scope }
    }
    return status
  }

  rateLimitRemainingMs(offer) {
    return this.rateLimitStatus(offer).remainingMs
  }

  isOfferAvailable(offer) {
    return this.offerAccessStatus(offer).remainingMs === 0
      && this.offerCircuitRemainingMs(offer) === 0
      && this.rateLimitRemainingMs(offer) === 0
  }

  openRateLimit(offer, options = {}) {
    const scope = normalizedRateLimitScope(options.scope, offer)
    const key = rateLimitKey(offer, scope)
    const requestedMs = boundedMs(options.retryAfterMs)
    const durationMs = isNvidiaProvider(offer?.providerKey)
      ? Math.max(NVIDIA_RATE_LIMIT_FLOOR_MS, requestedMs)
      : requestedMs
    const until = this.now() + durationMs
    const previous = this.rateLimits.get(key)?.until || 0
    this.rateLimits.set(key, { scope, until: Math.max(previous, until) })
    return Math.max(previous, until)
  }

  async pace(providerKey, signal) {
    const intervalMs = this.pacingFor(providerKey)
    if (intervalMs === 0) return
    if (this.lastStarts.has(providerKey)) {
      const waitMs = Math.max(0, this.lastStarts.get(providerKey) + intervalMs - this.now())
      if (waitMs > 0) await this.sleep(waitMs, signal)
    }
    this.lastStarts.set(providerKey, this.now())
  }

  async run(providerKey, operation, options = {}) {
    const remaining = this.circuitRemainingMs(providerKey)
    if (remaining > 0) throw new ProviderCircuitOpenError(providerKey, remaining)
    const access = options.offer ? this.offerAccessStatus(options.offer) : { remainingMs: 0 }
    if (access.remainingMs > 0) {
      throw new ProviderOfferAccessBlockedError(options.offer, access.accessClass, access.remainingMs)
    }
    const offerRemaining = options.offer ? this.offerCircuitRemainingMs(options.offer) : 0
    if (offerRemaining > 0) {
      throw new ProviderOfferCircuitOpenError(options.offer, offerRemaining)
    }
    const rateLimit = options.offer ? this.rateLimitStatus(options.offer) : { remainingMs: 0, scope: 'offer' }
    if (rateLimit.remainingMs > 0) {
      throw new ProviderRateLimitError(providerKey, rateLimit.scope, rateLimit.remainingMs)
    }
    const release = await this.semaphoreFor(providerKey).acquire(options.signal)
    try {
      const secondCheck = this.circuitRemainingMs(providerKey)
      if (secondCheck > 0) throw new ProviderCircuitOpenError(providerKey, secondCheck)
      const secondAccess = options.offer ? this.offerAccessStatus(options.offer) : { remainingMs: 0 }
      if (secondAccess.remainingMs > 0) {
        throw new ProviderOfferAccessBlockedError(options.offer, secondAccess.accessClass, secondAccess.remainingMs)
      }
      const secondOfferCheck = options.offer ? this.offerCircuitRemainingMs(options.offer) : 0
      if (secondOfferCheck > 0) {
        throw new ProviderOfferCircuitOpenError(options.offer, secondOfferCheck)
      }
      const secondRateLimit = options.offer ? this.rateLimitStatus(options.offer) : { remainingMs: 0, scope: 'offer' }
      if (secondRateLimit.remainingMs > 0) {
        throw new ProviderRateLimitError(providerKey, secondRateLimit.scope, secondRateLimit.remainingMs)
      }
      await this.pace(providerKey, options.signal)
      try {
        return await operation({ signal: options.signal })
      } catch (error) {
        if (isProviderTimeout(error)) {
          if (options.offer) this.openOfferCircuit(options.offer)
          else this.recordTransientFailure(providerKey)
        }
        throw error
      }
    } finally {
      release()
    }
  }
}

function linkedRequestSignal(parentSignal, totalMs) {
  const controller = new AbortController()
  let completed = false
  const abortFromParent = () => controller.abort(abortError(parentSignal.reason))
  if (parentSignal?.aborted) abortFromParent()
  else parentSignal?.addEventListener('abort', abortFromParent, { once: true })

  const totalTimer = setTimeout(() => {
    const error = new Error(`Provider request exceeded total deadline ${totalMs}ms.`)
    error.code = 'NEXUS_TOTAL_TIMEOUT'
    error.name = 'TimeoutError'
    controller.abort(error)
  }, Math.max(1, totalMs))

  return {
    signal: controller.signal,
    cleanup() {
      if (completed) return
      completed = true
      clearTimeout(totalTimer)
      parentSignal?.removeEventListener('abort', abortFromParent)
    },
  }
}

function linkedAttemptSignal(requestSignal, firstByteMs) {
  const controller = new AbortController()
  let completed = false
  const abortFromRequest = () => controller.abort(abortError(requestSignal.reason))
  if (requestSignal?.aborted) abortFromRequest()
  else requestSignal?.addEventListener('abort', abortFromRequest, { once: true })

  const firstByteTimer = setTimeout(() => {
    const error = new Error(`Provider did not return response headers within ${firstByteMs}ms.`)
    error.code = 'NEXUS_FIRST_BYTE_TIMEOUT'
    error.name = 'TimeoutError'
    controller.abort(error)
  }, Math.max(1, firstByteMs))

  return {
    signal: controller.signal,
    headersReceived() { clearTimeout(firstByteTimer) },
    cleanup() {
      if (completed) return
      completed = true
      clearTimeout(firstByteTimer)
      requestSignal?.removeEventListener('abort', abortFromRequest)
    },
  }
}

function isRequestHalt(error) {
  return error?.name === 'AbortError'
    || error?.code === 'NEXUS_TOTAL_TIMEOUT'
}

function isRetryableStatus(status) {
  const code = Number(status)
  return OFFER_FAILOVER_STATUSES.has(code) || code >= 500
}

export async function runGovernedAttempts(options) {
  const offers = Array.isArray(options.offers) ? options.offers : []
  const governor = options.governor || new ProviderGovernor()
  const maxAttempts = Math.min(2, Math.max(1, Number(options.maxAttempts) || 2))
  const deadlines = {
    firstByteMs: Math.max(1, Number(options.deadlines?.firstByteMs) || 45_000),
    totalMs: Math.max(1, Number(options.deadlines?.totalMs) || 180_000),
  }
  const attemptedOffers = new Set()
  const attempts = []
  const requestSignal = linkedRequestSignal(options.signal, deadlines.totalMs)
  let upstreamCalls = 0
  let lastError = null
  let lastResult = null

  try {
    while (upstreamCalls < maxAttempts) {
      if (requestSignal.signal.aborted) throw requestSignal.signal.reason
      const offer = offers.find(candidate => {
        const key = offerIdentityKey(candidate)
        return !attemptedOffers.has(key)
          && governor.isAvailable(candidate.providerKey)
          && governor.isOfferAvailable(candidate)
      })
      if (!offer) break

      attemptedOffers.add(offerIdentityKey(offer))
      const meta = {
        providerKey: offer.providerKey,
        modelId: offer.modelId,
        offerId: offer.offerId || null,
        accountKey: offer.accountKey || null,
        connectionKey: offer.connectionKey || null,
        status: null,
      }
      try {
        const result = await governor.run(
          offer.providerKey,
          async () => {
            const attemptSignal = linkedAttemptSignal(requestSignal.signal, deadlines.firstByteMs)
            upstreamCalls += 1
            try {
              const response = await options.attempt(offer, { signal: attemptSignal.signal })
              attemptSignal.headersReceived()
              return response
            } finally {
              attemptSignal.cleanup()
            }
          },
          { signal: requestSignal.signal, offer },
        )
        meta.status = Number(result.status)
        attempts.push(meta)
        lastResult = { response: result, offer, attempts }
        if (result.status === 429) {
          const retryAfterMs = parseRetryAfterMs(result.headers?.get?.('retry-after'), governor.now())
          governor.openRateLimit(offer, {
            scope: classifyRateLimitScope(result.headers, offer),
            retryAfterMs,
          })
        } else {
          const retryAfter = result.headers?.get?.('retry-after')
          governor.recordOfferStatus(offer, result.status, {
            retryAfterMs: retryAfter ? parseRetryAfterMs(retryAfter, governor.now()) : undefined,
          })
        }
        if (REQUEST_TERMINAL_STATUSES.has(Number(result.status)) || !isRetryableStatus(result.status)) {
          return lastResult
        }
        if (upstreamCalls >= maxAttempts) return lastResult
      } catch (error) {
        lastError = error
        meta.error = error?.code || error?.name || 'ERR'
        attempts.push(meta)
        if (isRequestHalt(error)) throw error
        if (upstreamCalls >= maxAttempts) break
      }
    }
  } finally {
    requestSignal.cleanup()
  }

  if (lastResult) return lastResult
  if (lastError) {
    lastError.attempts = attempts
    throw lastError
  }
  const error = new Error('No governed provider offer is currently available.')
  error.code = 'NEXUS_NO_PROVIDER_OFFER'
  error.attempts = attempts
  throw error
}

export class CatalogueScheduler {
  constructor(options = {}) {
    this.providers = [...(options.providers || [])]
    this.listModels = options.listModels
    this.probeChat = options.probeChat
  }

  async initialize() { return this.refresh() }

  async refresh() {
    const observations = []
    for (const provider of this.providers) observations.push(await this.listModels(provider))
    return observations
  }

  async canary(provider, model) {
    if (!provider || !model) throw new TypeError('provider and model are required for an explicit canary')
    return this.probeChat(provider, model)
  }
}

function canaryOfferKey(offer = {}) {
  return JSON.stringify([String(offer.providerKey || ''), String(offer.modelId || '')])
}

function finiteTimestamp(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0
}

function resilientProviderRank(providerKey, providerLane) {
  return providerLane.indexOf(normalizeResilientIdentity(providerKey))
}

function mostRecentPing(offer = {}) {
  if (!Array.isArray(offer.pings)) return null
  let latest = null
  for (const ping of offer.pings) {
    const at = finiteTimestamp(ping?.ts)
    if (!at || (latest && at <= latest.at)) continue
    latest = {
      at,
      code: String(ping?.code || '').trim(),
      latencyMs: Number.isFinite(Number(ping?.ms)) ? Number(ping.ms) : null,
    }
  }
  return latest
}

function isSuccessfulObservedCode(code) {
  return /^2\d\d$/.test(String(code || '').trim())
}

function hasCurrentObservedFailure(offer = {}) {
  const code = String(offer.httpCode || offer.lastError?.code || '').trim()
  return Boolean(code) && !isSuccessfulObservedCode(code)
}

function resilientHealthEvidence(offer = {}) {
  if (String(offer.status || '').trim().toLowerCase() !== 'up') return null
  if (hasCurrentObservedFailure(offer)) return null

  const ping = mostRecentPing(offer)
  // Real client traffic records a successful model-response timestamp even
  // when older relay versions did not retain a ping row.  It is still exact
  // provider-model evidence, never a catalogue inference.
  const responseAt = finiteTimestamp(offer.lastModelResponseAt)
  if (ping && ping.at > responseAt) {
    if (!isSuccessfulObservedCode(ping.code)) return null
    return ping
  }
  if (responseAt) return { at: responseAt, code: '200', latencyMs: null }
  if (ping) {
    if (!isSuccessfulObservedCode(ping.code)) return null
    return ping
  }

  const pingAt = finiteTimestamp(offer.lastPingAt)
  if (pingAt && isSuccessfulObservedCode(offer.httpCode)) {
    return { at: pingAt, code: String(offer.httpCode), latencyMs: null }
  }
  return null
}

function boundedResilientObservationTtl(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return NEXUS_RESILIENT_OBSERVATION_TTL_MS
  return Math.min(60 * 60 * 1000, Math.max(60_000, Math.round(numeric)))
}

function boundedResilientWarmObservationTtl(value, freshTtlMs) {
  const numeric = Number(value)
  const fallback = NEXUS_RESILIENT_WARM_OBSERVATION_TTL_MS
  const requested = Number.isFinite(numeric) && numeric > 0 ? Math.round(numeric) : fallback
  return Math.min(7 * 24 * 60 * 60 * 1000, Math.max(freshTtlMs, requested))
}

function parseContextWindowTokens(value) {
  const raw = String(value || '').trim().toLowerCase().replace(/,/g, '')
  const match = raw.match(/^(\d+(?:\.\d+)?)\s*([km])?$/)
  if (!match) return 0
  const numeric = Number(match[1])
  if (!Number.isFinite(numeric) || numeric <= 0) return 0
  const multiplier = match[2] === 'm' ? 1_000_000 : match[2] === 'k' ? 1_000 : 1
  return Math.max(0, Math.floor(numeric * multiplier))
}

// `intell` is router control-plane metadata, not a benchmark claim.  It is
// deliberately used only after an exact successful observation has admitted
// an offer to the resilient lane.  This prevents a newly pinged low-capacity
// code endpoint from becoming the generic Hermes fallback solely because it
// happened to answer a few seconds more recently than a healthier frontier
// route.
function resilientRoutingQuality(offer = {}) {
  const value = Number(offer.intell)
  return Number.isFinite(value) && value > 0 ? value : -1
}

function resilientRequiredContextTokens(options = {}) {
  const prompt = Math.max(0, Math.floor(Number(options.estimatedPromptTokens) || 0))
  if (prompt === 0) return 0
  const reserve = Math.max(
    NEXUS_RESILIENT_CONTEXT_RESERVE_TOKENS,
    Math.min(16_384, Math.floor(Number(options.outputReserveTokens) || 0)),
  )
  return prompt + reserve
}

function offerFitsResilientContext(offer, requiredTokens) {
  if (requiredTokens <= 0) return true
  const contextTokens = parseContextWindowTokens(offer?.ctx)
  if (contextTokens > 0) return contextTokens >= requiredTokens
  return requiredTokens <= NEXUS_RESILIENT_UNKNOWN_CONTEXT_MAX_PROMPT_TOKENS
}

/**
 * Resolves the opt-in `nexus-resilient` alias without touching the normal
 * canonical-model route.  This is deliberately stricter than auto-fastest:
 * every candidate must be an exact 2xx observation inside the explicit
 * provider lane and must clear the live provider/offer governor. Fresh
 * observations rank first; a bounded warm window exists so an active long
 * session does not collapse to a 503 merely because the low-rate sampler has
 * not revisited every provider. Catalogue-only and failed observations remain
 * excluded rather than guessed.
 *
 * GLM-5.2 is intentionally excluded so a caller can retain `glm-5.2` as its
 * locked primary and use this alias only as a separately chosen fallback.
 */
export function selectNexusResilientOffers(offers = [], options = {}) {
  const governor = options.governor
  if (!governor || typeof governor.isAvailable !== 'function' || typeof governor.isOfferAvailable !== 'function') {
    return []
  }

  const now = finiteTimestamp(options.now) || Date.now()
  const freshAgeMs = boundedResilientObservationTtl(options.maxObservationAgeMs)
  const warmAgeMs = boundedResilientWarmObservationTtl(options.maxWarmObservationAgeMs, freshAgeMs)
  const requiredContextTokens = resilientRequiredContextTokens(options)
  const providerLane = Array.from(options.providerLane || NEXUS_RESILIENT_PROVIDER_LANE)
    .map(normalizeResilientIdentity)
    .filter(Boolean)
  if (providerLane.length === 0) return []

  const candidates = []
  for (const offer of Array.isArray(offers) ? offers : []) {
    const providerKey = normalizeResilientIdentity(offer?.providerKey)
    const modelId = normalizeResilientIdentity(offer?.modelId)
    const providerRank = resilientProviderRank(providerKey, providerLane)
    if (!providerKey || !modelId || providerRank < 0) continue
    if (NEXUS_GLM52_PRIMARY_MODEL_IDS.has(modelId)) continue
    if (['banned', 'disabled', 'excluded', 'noauth'].includes(String(offer.status || '').trim().toLowerCase())) continue

    const evidence = resilientHealthEvidence(offer)
    if (!evidence || evidence.at > now) continue
    const ageMs = now - evidence.at
    if (ageMs > warmAgeMs) continue
    if (!offerFitsResilientContext(offer, requiredContextTokens)) continue

    try {
      if (!governor.isAvailable(offer.providerKey) || !governor.isOfferAvailable(offer)) continue
    } catch {
      // A malformed governor/offer relationship is not evidence of safety.
      continue
    }

    candidates.push({
      offer,
      providerKey,
      modelId,
      providerRank,
      observedAt: evidence.at,
      latencyMs: evidence.latencyMs,
      freshnessRank: ageMs <= freshAgeMs ? 0 : 1,
      routingQuality: resilientRoutingQuality(offer),
    })
  }

  candidates.sort((left, right) => (
    (left.freshnessRank - right.freshnessRank)
    // Health is the admission gate.  Within the same fresh/warm health band,
    // use the existing routing-quality prior before recency and latency.
    || (right.routingQuality - left.routingQuality)
    || (right.observedAt - left.observedAt)
    || ((left.latencyMs ?? Number.POSITIVE_INFINITY) - (right.latencyMs ?? Number.POSITIVE_INFINITY))
    || (left.providerRank - right.providerRank)
    || `${left.providerKey}/${left.modelId}`.localeCompare(`${right.providerKey}/${right.modelId}`)
  ))

  const exactOffers = []
  const seenOfferIds = new Set()
  for (const candidate of candidates) {
    const offerId = `${candidate.providerKey}/${candidate.modelId}`
    if (seenOfferIds.has(offerId)) continue
    seenOfferIds.add(offerId)
    exactOffers.push(candidate)
  }

  // Put a distinct provider second when one exists.  The relay's two-call
  // budget can then fail over across a provider boundary without trying a
  // stale, unknown, or duplicate catalogue row.
  const firstPass = []
  const remainder = []
  const seenProviders = new Set()
  for (const candidate of exactOffers) {
    if (seenProviders.has(candidate.providerKey)) remainder.push(candidate)
    else {
      seenProviders.add(candidate.providerKey)
      firstPass.push(candidate)
    }
  }
  return [...firstPass, ...remainder].map(candidate => candidate.offer)
}

/**
 * Chooses a bounded first-byte deadline from exact provider-model evidence.
 * The request-level remaining budget is always the hard ceiling.
 */
export function computeOfferFirstByteDeadlineMs(offer = {}, options = {}) {
  const configuredMs = Math.max(1, Number(options.configuredMs) || 45_000)
  const rawRemainingMs = Number(options.remainingMs)
  const remainingMs = Number.isFinite(rawRemainingMs)
    ? Math.max(1, Math.floor(rawRemainingMs))
    : configuredMs
  const rawMaximumMs = Number(options.maximumMs)
  const maximumMs = Number.isFinite(rawMaximumMs)
    ? Math.max(1, Math.floor(rawMaximumMs))
    : MAX_OFFER_FIRST_BYTE_MS
  const ceilingMs = Math.max(1, Math.min(configuredMs, remainingMs, maximumMs))
  const rawMinimumMs = Number(options.minimumMs)
  const minimumMs = Math.min(
    ceilingMs,
    Number.isFinite(rawMinimumMs)
      ? Math.max(1, Math.floor(rawMinimumMs))
      : MIN_OFFER_FIRST_BYTE_MS,
  )
  const pings = (Array.isArray(offer.pings) ? offer.pings : []).slice(-10)
  const latestPing = pings[pings.length - 1]
  const successLatencies = pings
    .filter(ping => /^2\d\d$/.test(String(ping?.code || '')))
    .map(ping => Number(ping?.ms))
    .filter(ms => Number.isFinite(ms) && ms >= 0)
    .sort((left, right) => left - right)
  const failed = new Set(['timeout', 'down', 'noauth']).has(String(offer.status || '').toLowerCase())
    || (latestPing && !/^2\d\d$/.test(String(latestPing.code || '')))
  const providerKey = String(offer.providerKey || '').toLowerCase()
  const estimatedPromptTokens = Math.max(0, Math.floor(Number(options.estimatedPromptTokens) || 0))
  const nvidiaContextFloorMs = providerKey.includes('nvidia')
    ? (estimatedPromptTokens >= 64_000
        ? NVIDIA_LARGE_CONTEXT_FIRST_BYTE_FLOOR_MS
        : estimatedPromptTokens >= 16_000
          ? NVIDIA_MEDIUM_CONTEXT_FIRST_BYTE_FLOOR_MS
          : NVIDIA_HEALTHY_FIRST_BYTE_FLOOR_MS)
    : 0

  let targetMs
  if (failed) {
    targetMs = minimumMs
  } else if (successLatencies.length > 0) {
    const p90Index = Math.max(0, Math.ceil(successLatencies.length * 0.9) - 1)
    targetMs = Math.round((successLatencies[p90Index] * 2) + 2_000)
  } else {
    targetMs = providerKey.includes('nvidia')
      ? NVIDIA_UNVERIFIED_FIRST_BYTE_MS
      : DEFAULT_UNVERIFIED_FIRST_BYTE_MS
  }
  return Math.max(1, Math.min(ceilingMs, Math.max(minimumMs, targetMs, nvidiaContextFloorMs)))
}

function canaryObservationAt(offer = {}) {
  const pingAt = finiteTimestamp(offer.lastPingAt)
  const responseAt = finiteTimestamp(offer.lastModelResponseAt)
  const latestPingAt = Array.isArray(offer.pings)
    ? offer.pings.reduce((latest, ping) => Math.max(latest, finiteTimestamp(ping?.ts)), 0)
    : 0
  return Math.max(pingAt, responseAt, latestPingAt)
}

function canaryScore(offer = {}) {
  const value = Number(offer.intell)
  return Number.isFinite(value) ? value : -1
}

function resilientCanaryRefreshCandidate(offer = {}, options = {}) {
  const now = finiteTimestamp(options.now) || Date.now()
  const providerKey = normalizeResilientIdentity(offer.providerKey)
  const modelId = normalizeResilientIdentity(offer.modelId)
  const providerLane = Array.from(options.providerLane || NEXUS_RESILIENT_PROVIDER_LANE)
    .map(normalizeResilientIdentity)
    .filter(Boolean)
  if (!providerKey || !modelId || resilientProviderRank(providerKey, providerLane) < 0) return null
  // The locked GLM-5.2 request path has independent health handling.  It is
  // intentionally not eligible to consume fallback-refresh capacity.
  if (NEXUS_GLM52_PRIMARY_MODEL_IDS.has(modelId)) return null

  const evidence = resilientHealthEvidence(offer)
  if (!evidence || evidence.at > now) return null
  const ageMs = now - evidence.at
  const freshAgeMs = boundedResilientObservationTtl(options.resilientObservationTtlMs)
  const refreshDueAgeMs = Math.max(0, freshAgeMs - Math.max(0, Number(options.minSpacingMs) || 0))
  if (ageMs < refreshDueAgeMs || ageMs > NEXUS_RESILIENT_CANARY_REFRESH_MAX_AGE_MS) return null

  return {
    observedAt: evidence.at,
    routingQuality: resilientRoutingQuality(offer),
  }
}

function compareRoutineCanaryOffers(left, right, sampler, now) {
  const providerAgeLeft = now - (sampler.providerLastAt.get(left.providerKey) || 0)
  const providerAgeRight = now - (sampler.providerLastAt.get(right.providerKey) || 0)
  if (providerAgeLeft !== providerAgeRight) return providerAgeRight - providerAgeLeft
  const attemptLeft = sampler.offerLastAt.get(canaryOfferKey(left)) || 0
  const attemptRight = sampler.offerLastAt.get(canaryOfferKey(right)) || 0
  if ((attemptLeft === 0) !== (attemptRight === 0)) return attemptLeft === 0 ? -1 : 1
  const observationLeft = canaryObservationAt(left)
  const observationRight = canaryObservationAt(right)
  if ((observationLeft === 0) !== (observationRight === 0)) return observationLeft === 0 ? -1 : 1
  if (canaryScore(left) !== canaryScore(right)) return canaryScore(right) - canaryScore(left)
  if (observationLeft !== observationRight) return observationLeft - observationRight
  return canaryOfferKey(left).localeCompare(canaryOfferKey(right))
}

function latestCanarySelection(events = []) {
  return events.reduce((latest, event) => (
    !latest || Number(event?.at) > Number(latest.at) ? event : latest
  ), null)
}

function isTerminalCanaryOffer(offer = {}) {
  // A provider's repeated 400 from the fixed canary body, a 404, or a 410 is
  // normally deterministic for that exact canary route.  NVIDIA's gateway
  // also uses HTTP 400 for a temporary "DEGRADED function cannot be invoked"
  // response.  That is provider availability evidence, not a malformed
  // request, so retain it for the next bounded health recheck.
  const code = String(offer.httpCode || offer.lastError?.code || '').trim()
  const nvidiaDegradedFunction = isNvidiaProvider(offer?.providerKey)
    && /(?:degraded\s+function|function(?:\s+\w+){0,5}\s+degraded|function\s+cannot\s+be\s+invoked)/i.test(String(offer?.lastError?.message || ''))
  if (nvidiaDegradedFunction) return false
  return ['400', '404', '410'].includes(code)
}

/**
 * Selects at most one low-cost health canary at a time. State is plain JSON so
 * the relay can persist it across restarts without storing provider secrets.
 */
export class BoundedCanarySampler {
  constructor(options = {}) {
    this.now = options.now || Date.now
    this.windowMs = Math.max(60_000, Number(options.windowMs) || DEFAULT_CANARY_WINDOW_MS)
    this.globalLimit = Math.max(1, Number(options.globalLimit) || 6)
    this.minSpacingMs = Math.max(60_000, Number(options.minSpacingMs) || DEFAULT_CANARY_MIN_SPACING_MS)
    this.defaultProviderCooldownMs = Math.max(
      this.minSpacingMs,
      Number(options.defaultProviderCooldownMs) || DEFAULT_CANARY_PROVIDER_COOLDOWN_MS,
    )
    this.providerCooldownMs = {
      nvidia: NVIDIA_CANARY_PROVIDER_COOLDOWN_MS,
      ...(options.providerCooldownMs || {}),
    }
    const state = options.state && typeof options.state === 'object' ? options.state : {}
    this.events = Array.isArray(state.events)
      ? state.events.filter(event => Number.isFinite(Number(event?.at)))
        .map(event => ({ ...event, at: Number(event.at) }))
      : []
    this.providerLastAt = new Map(Object.entries(state.providerLastAt || {}).map(([key, value]) => [key, finiteTimestamp(value)]))
    this.offerLastAt = new Map(Object.entries(state.offerLastAt || {}).map(([key, value]) => [key, finiteTimestamp(value)]))
    this.providerBlockedUntil = new Map(Object.entries(state.providerBlockedUntil || {}).map(([key, value]) => [key, finiteTimestamp(value)]))
    this.observations = new Map(Object.entries(state.observations || {}).filter(([, value]) => value && typeof value === 'object'))
  }

  prune(now = this.now()) {
    this.events = this.events.filter(event => now - event.at < this.windowMs)
    for (const [providerKey, until] of this.providerBlockedUntil) {
      if (until <= now) this.providerBlockedUntil.delete(providerKey)
    }
  }

  cooldownFor(providerKey) {
    return Math.max(
      this.minSpacingMs,
      Number(this.providerCooldownMs[providerKey]) || this.defaultProviderCooldownMs,
    )
  }

  claim(offers = [], options = {}) {
    const now = this.now()
    this.prune(now)
    const latestEventAt = this.events.reduce((latest, event) => Math.max(latest, event.at), 0)
    if (this.events.length >= this.globalLimit || (latestEventAt > 0 && now - latestEventAt < this.minSpacingMs)) {
      return null
    }

    const governor = options.governor
    const eligible = (Array.isArray(offers) ? offers : []).filter(offer => {
      if (!offer?.providerKey || !offer?.modelId) return false
      if (isTerminalCanaryOffer(offer)) return false
      if (['banned', 'excluded', 'disabled', 'noauth'].includes(String(offer.status || '').toLowerCase())) return false
      const accessUntil = finiteTimestamp(offer.accessUntil)
      if (String(offer.accessClass || '').trim() && accessUntil > now) return false
      if ((this.providerBlockedUntil.get(offer.providerKey) || 0) > now) return false
      if (now - (this.providerLastAt.get(offer.providerKey) || 0) < this.cooldownFor(offer.providerKey)) return false
      if (governor && (!governor.isAvailable(offer.providerKey) || !governor.isOfferAvailable(offer))) return false
      return true
    })
    if (eligible.length === 0) return null

    const source = String(options.source || 'scheduled')
    const priorityRefreshes = source === 'scheduled' && options.prioritizeResilientRefresh !== false
      ? new Map(eligible.map(offer => [offer, resilientCanaryRefreshCandidate(offer, {
        now,
        minSpacingMs: this.minSpacingMs,
        providerLane: options.resilientProviderLane,
        resilientObservationTtlMs: options.resilientObservationTtlMs,
      })]).filter(([, priority]) => priority))
      : new Map()
    const priorityOffers = [...priorityRefreshes.keys()]
    const routineOffers = eligible.filter(offer => !priorityRefreshes.has(offer))
    const previousSelection = latestCanarySelection(this.events)
    // At most every other scheduled canary refreshes an exact known-good
    // fallback.  This preserves discovery across provider families while
    // preventing one recently pinged code endpoint from becoming the only
    // fresh fallback merely because the scheduler keeps selecting unverified
    // catalogue rows.  The global budget, spacing, provider cooldown, access
    // holds, and governor gates above still apply before this choice.
    const usePriorityRefresh = priorityOffers.length > 0
      && (routineOffers.length === 0 || previousSelection?.selectionClass !== 'resilient_refresh')
    const selectionClass = usePriorityRefresh ? 'resilient_refresh' : 'routine'
    const pool = usePriorityRefresh ? priorityOffers : routineOffers.length > 0 ? routineOffers : priorityOffers

    pool.sort((left, right) => {
      if (selectionClass === 'resilient_refresh') {
        const leftPriority = priorityRefreshes.get(left)
        const rightPriority = priorityRefreshes.get(right)
        // A policy score only breaks ties after a prior exact 2xx observation
        // admitted both offers to this refresh pool.  It is not availability
        // or benchmark evidence.
        if (leftPriority.routingQuality !== rightPriority.routingQuality) {
          return rightPriority.routingQuality - leftPriority.routingQuality
        }
        if (leftPriority.observedAt !== rightPriority.observedAt) {
          return leftPriority.observedAt - rightPriority.observedAt
        }
      }
      return compareRoutineCanaryOffers(left, right, this, now)
    })

    const selected = pool[0]
    const event = {
      at: now,
      providerKey: selected.providerKey,
      modelId: selected.modelId,
      source,
      selectionClass,
      outcome: 'reserved',
    }
    this.events.push(event)
    this.providerLastAt.set(selected.providerKey, now)
    this.offerLastAt.set(canaryOfferKey(selected), now)
    return selected
  }

  record(offer, options = {}) {
    if (!offer?.providerKey || !offer?.modelId) return
    const matching = [...this.events].reverse().find(event => (
      event.providerKey === offer.providerKey && event.modelId === offer.modelId && event.outcome === 'reserved'
    ))
    if (matching) {
      matching.outcome = String(options.outcome || 'unknown')
      matching.status = options.status == null ? null : Number(options.status)
      matching.latencyMs = Number.isFinite(Number(options.latencyMs)) ? Number(options.latencyMs) : null
    }
    const retryAfterMs = Number(options.retryAfterMs)
    if (Number.isFinite(retryAfterMs) && retryAfterMs > 0) {
      const until = this.now() + retryAfterMs
      this.providerBlockedUntil.set(
        offer.providerKey,
        Math.max(until, this.providerBlockedUntil.get(offer.providerKey) || 0),
      )
    }
  }

  observe(offer, observation = {}) {
    if (!offer?.providerKey || !offer?.modelId) return null
    const key = canaryOfferKey(offer)
    const previous = this.observations.get(key) || {}
    const mergedPings = [...(Array.isArray(previous.pings) ? previous.pings : []), ...(Array.isArray(observation.pings) ? observation.pings : [])]
      .filter(ping => ping && finiteTimestamp(ping.ts) > 0)
      .map(ping => ({
        code: String(ping.code || ''),
        ms: Number.isFinite(Number(ping.ms)) ? Number(ping.ms) : null,
        ts: finiteTimestamp(ping.ts),
      }))
      .sort((a, b) => a.ts - b.ts)
      .filter((ping, index, rows) => index === rows.findIndex(candidate => (
        candidate.ts === ping.ts && candidate.code === ping.code && candidate.ms === ping.ms
      )))
      .slice(-50)
    const latestPingAt = mergedPings.reduce((latest, ping) => Math.max(latest, ping.ts), 0)
    const lastPingAt = Math.max(
      finiteTimestamp(previous.lastPingAt),
      finiteTimestamp(observation.lastPingAt),
      latestPingAt,
    )
    const lastModelResponseAt = Math.max(
      finiteTimestamp(previous.lastModelResponseAt),
      finiteTimestamp(observation.lastModelResponseAt),
    )
    const lastError = observation.lastError && typeof observation.lastError === 'object'
      ? {
          code: String(observation.lastError.code || ''),
          message: String(observation.lastError.message || '').slice(0, 500),
          updatedAt: finiteTimestamp(observation.lastError.updatedAt),
        }
      : observation.lastError === null
        ? null
        : previous.lastError || null
    const hasAccessClass = Object.prototype.hasOwnProperty.call(observation, 'accessClass')
    const requestedAccessClass = hasAccessClass
      ? String(observation.accessClass || '').trim().toLowerCase()
      : String(previous.accessClass || '').trim().toLowerCase()
    const accessClass = ACCESS_FAILURE_STATUS_VALUES.has(requestedAccessClass)
      ? requestedAccessClass
      : null
    const accessUntil = hasAccessClass && !accessClass
      ? 0
      : (Object.prototype.hasOwnProperty.call(observation, 'accessUntil')
        ? finiteTimestamp(observation.accessUntil)
        : finiteTimestamp(previous.accessUntil))
    const row = {
      providerKey: String(offer.providerKey),
      modelId: String(offer.modelId),
      status: String(observation.status || previous.status || 'pending'),
      httpCode: Object.prototype.hasOwnProperty.call(observation, 'httpCode')
        ? (observation.httpCode == null ? null : String(observation.httpCode))
        : (previous.httpCode ?? null),
      lastPingAt,
      lastModelResponseAt,
      pings: mergedPings,
      lastError,
      cooldownUntil: Math.max(
        finiteTimestamp(previous.cooldownUntil),
        finiteTimestamp(observation.cooldownUntil),
      ),
      accessClass,
      accessUntil,
      observedAt: Math.max(lastPingAt, lastModelResponseAt, finiteTimestamp(previous.observedAt)),
    }
    this.observations.set(key, row)
    return { ...row, pings: row.pings.map(ping => ({ ...ping })) }
  }

  hydrate(offers = []) {
    const now = this.now()
    for (const offer of Array.isArray(offers) ? offers : []) {
      const persisted = this.observations.get(canaryOfferKey(offer))
      if (!persisted) continue
      const currentAt = canaryObservationAt(offer)
      const persistedAt = Math.max(
        finiteTimestamp(persisted.lastPingAt),
        finiteTimestamp(persisted.lastModelResponseAt),
        finiteTimestamp(persisted.observedAt),
      )
      if (currentAt > persistedAt) continue
      const accessClass = ACCESS_FAILURE_STATUS_VALUES.has(String(persisted.accessClass || '').toLowerCase())
        ? String(persisted.accessClass).toLowerCase()
        : null
      const accessUntil = finiteTimestamp(persisted.accessUntil)
      const accessActive = Boolean(accessClass) && accessUntil > now
      offer.accessClass = accessActive ? accessClass : null
      offer.accessUntil = accessActive ? accessUntil : 0
      // Once the bounded access hold expires, do not leave a historical 401,
      // 402, or 403 masquerading as a permanent eligibility decision. The
      // subsequent governed canary/request can establish a fresh observation.
      if (isOfferAccessFailureStatus(persisted.status) && !accessActive) {
        offer.status = 'pending'
        offer.httpCode = null
        offer.lastError = null
        continue
      }
      offer.status = persisted.status || offer.status
      offer.httpCode = persisted.httpCode ?? offer.httpCode ?? null
      offer.lastPingAt = finiteTimestamp(persisted.lastPingAt)
      offer.lastModelResponseAt = finiteTimestamp(persisted.lastModelResponseAt)
      offer.pings = Array.isArray(persisted.pings) ? persisted.pings.map(ping => ({ ...ping })) : []
      offer.lastError = persisted.lastError ? { ...persisted.lastError } : null
    }
    return offers
  }

  restoreCooldowns(governor, offers = []) {
    if (!governor?.openRateLimit) return
    const now = this.now()
    const byKey = new Map((Array.isArray(offers) ? offers : []).map(offer => [canaryOfferKey(offer), offer]))
    for (const [key, observation] of this.observations) {
      const offer = byKey.get(key)
      const cooldownUntil = finiteTimestamp(observation.cooldownUntil)
      if (!offer || cooldownUntil <= now) continue
      governor.openRateLimit(offer, {
        scope: 'offer',
        retryAfterMs: cooldownUntil - now,
      })
    }
    if (!governor.blockOfferAccess) return
    for (const [key, observation] of this.observations) {
      const offer = byKey.get(key)
      const accessClass = String(observation.accessClass || '').toLowerCase()
      const accessUntil = finiteTimestamp(observation.accessUntil)
      if (!offer || !ACCESS_FAILURE_STATUS_VALUES.has(accessClass) || accessUntil <= now) continue
      governor.blockOfferAccess(offer, accessClass, accessUntil - now)
    }
  }

  exportState() {
    this.prune(this.now())
    return {
      schemaVersion: 3,
      events: this.events.map(event => ({ ...event })),
      providerLastAt: Object.fromEntries(this.providerLastAt),
      offerLastAt: Object.fromEntries(this.offerLastAt),
      providerBlockedUntil: Object.fromEntries(this.providerBlockedUntil),
      observations: Object.fromEntries(
        [...this.observations].map(([key, value]) => [
          key,
          {
            ...value,
            pings: Array.isArray(value.pings) ? value.pings.map(ping => ({ ...ping })) : [],
          },
        ]),
      ),
    }
  }

  snapshot() {
    const now = this.now()
    this.prune(now)
    const latestEventAt = this.events.reduce((latest, event) => Math.max(latest, event.at), 0)
    const spacingReadyAt = latestEventAt > 0 ? latestEventAt + this.minSpacingMs : now
    const windowReadyAt = this.events.length >= this.globalLimit
      ? Math.min(...this.events.map(event => event.at + this.windowMs))
      : now
    return {
      policy: 'bounded_provider_aware_canary_v1',
      globalLimitPerWindow: this.globalLimit,
      windowSeconds: Math.round(this.windowMs / 1000),
      minimumSpacingSeconds: Math.round(this.minSpacingMs / 1000),
      defaultProviderCooldownSeconds: Math.round(this.defaultProviderCooldownMs / 1000),
      usedInWindow: this.events.length,
      remainingInWindow: Math.max(0, this.globalLimit - this.events.length),
      resilientRefreshSelectionsInWindow: this.events
        .filter(event => event.selectionClass === 'resilient_refresh').length,
      persistedObservations: this.observations.size,
      // This is deliberately an aggregate only: it lets the controlled reload
      // gate prove that the exact-route retirement exclusion is in the live
      // sampler without exposing model/provider observations or provider data.
      terminalCanaryExclusions: [...this.observations.values()]
        .filter(row => isTerminalCanaryOffer(row)).length,
      activePersistedCooldowns: [...this.observations.values()]
        .filter(row => finiteTimestamp(row.cooldownUntil) > now).length,
      activePersistedAccessBlocks: [...this.observations.values()]
        .filter(row => (
          ACCESS_FAILURE_STATUS_VALUES.has(String(row.accessClass || '').toLowerCase())
          && finiteTimestamp(row.accessUntil) > now
        )).length,
      lastObservedAt: this.observations.size > 0
        ? new Date(Math.max(...[...this.observations.values()].map(row => finiteTimestamp(row.observedAt)))).toISOString()
        : null,
      nextEligibleAt: new Date(Math.max(now, spacingReadyAt, windowReadyAt)).toISOString(),
      lastEvent: this.events.length > 0 ? { ...this.events[this.events.length - 1] } : null,
    }
  }
}


/**
 * Retain a compact canonical catalogue while making multi-offer routes explicitly
 * addressable by OpenAI-compatible clients. Provider-qualified IDs are emitted
 * only for logical model groups with more than one distinct offer.
 */
export function projectRoutableModelIds(groups = []) {
  const projected = []
  const seen = new Set()
  // An operator-locked primary must remain addressable even if catalogue churn
  // temporarily leaves it as the only offer in its logical model group.  This
  // is intentionally a tiny allow-list, not a rule that expands every
  // singleton offer into the public client catalogue.
  const protectedExactRouteIds = new Set(['nvidia/z-ai/glm-5.2'])
  const add = row => {
    const id = String(row?.id || '').trim().toLowerCase()
    if (!id || seen.has(id)) return
    seen.add(id)
    projected.push({ ...row, id })
  }

  for (const group of Array.isArray(groups) ? groups : []) {
    const canonicalId = String(group?.id || '').trim().toLowerCase()
    if (!canonicalId) continue
    const label = String(group?.label || group.id).trim() || canonicalId
    add({ id: canonicalId, name: label, providerQualified: false })

    const offers = Array.from(new Map(
      (Array.isArray(group?.models) ? group.models : [])
        .map(model => {
          const providerKey = String(model?.providerKey || '').trim().toLowerCase()
          const modelId = String(model?.modelId || '').trim().toLowerCase()
          return providerKey && modelId ? [`${providerKey}/${modelId}`, { providerKey, modelId }] : null
        })
        .filter(Boolean),
    ).values()).sort((left, right) => (
      `${left.providerKey}/${left.modelId}`.localeCompare(`${right.providerKey}/${right.modelId}`)
    ))
    const protectedOffers = offers.filter(offer => (
      protectedExactRouteIds.has(`${offer.providerKey}/${offer.modelId}`)
    ))
    if (offers.length < 2 && protectedOffers.length === 0) continue

    for (const offer of offers) {
      const exactRouteId = `${offer.providerKey}/${offer.modelId}`
      if (offers.length < 2 && !protectedExactRouteIds.has(exactRouteId)) continue
      add({
        id: exactRouteId,
        name: `${label} via ${offer.providerKey}`,
        providerQualified: true,
      })
    }
  }
  return projected
}
export function isLoopbackAddress(address) {
  const value = String(address || '').trim().toLowerCase()
  if (value === '::1' || value === 'localhost') return true
  const normalized = value.startsWith('::ffff:') ? value.slice(7) : value
  const parts = normalized.split('.')
  return parts.length === 4 && parts.every(part => /^\d+$/.test(part)) && Number(parts[0]) === 127
}

export function validateBindPolicy({ bind, bearerToken }) {
  const address = String(bind || '127.0.0.1').trim()
  if (!isLoopbackAddress(address) && !String(bearerToken || '')) {
    throw new Error(`Non-loopback bind ${address} requires a bearer token.`)
  }
  return address
}

function bearerMatches(expected, authorization) {
  const supplied = String(authorization || '').replace(/^Bearer\s+/i, '')
  const wanted = Buffer.from(String(expected || ''), 'utf8')
  const got = Buffer.from(supplied, 'utf8')
  return wanted.length > 0 && wanted.length === got.length && timingSafeEqual(wanted, got)
}

export function authorizeRequest({ path, remoteAddress, bearerToken, authorization }) {
  const local = isLoopbackAddress(remoteAddress)
  const requestPath = String(path || '/')
  if (requestPath === '/api' || requestPath.startsWith('/api/')) {
    return local ? { allowed: true } : { allowed: false, status: 403, code: 'NEXUS_ADMIN_LOOPBACK_ONLY' }
  }
  if (requestPath === '/v1' || requestPath.startsWith('/v1/')) {
    if (local) return { allowed: true }
    return bearerMatches(bearerToken, authorization)
      ? { allowed: true }
      : { allowed: false, status: 401, code: 'NEXUS_BEARER_REQUIRED' }
  }
  return { allowed: true }
}

const SECRET_FIELDS = /^(apiKey|token|accessToken|refreshToken|clientSecret|authorization|payload)$/i

function sanitizeValue(value, parentKey = '') {
  if (Array.isArray(value)) return value.map(item => sanitizeValue(item, parentKey))
  if (!value || typeof value !== 'object') return value
  const output = {}
  for (const [key, child] of Object.entries(value)) {
    if (SECRET_FIELDS.test(key) || (key === 'key' && parentKey === 'apiKeyPool')) continue
    output[key] = sanitizeValue(child, key)
  }
  return output
}

export function sanitizeConfigResponse(value) { return sanitizeValue(value) }

export function buildCorsHeaders({ origin, allowedOrigins = [] }) {
  if (!origin || !allowedOrigins.includes(origin)) return {}
  return {
    'Access-Control-Allow-Origin': origin,
    Vary: 'Origin',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  }
}

export function installNexusSecurityMiddleware(app, options = {}) {
  const allowedOrigins = String(options.allowedOrigins || '')
    .split(',')
    .map(value => value.trim())
    .filter(Boolean)
  const bearerToken = String(options.bearerToken || '')
  app.use((req, res, next) => {
    const corsHeaders = buildCorsHeaders({ origin: req.headers.origin, allowedOrigins })
    for (const [key, value] of Object.entries(corsHeaders)) res.setHeader(key, value)
    if (req.method === 'OPTIONS') {
      if (req.headers.origin && Object.keys(corsHeaders).length === 0) return res.sendStatus(403)
      return res.sendStatus(204)
    }
    const auth = authorizeRequest({
      path: req.path,
      remoteAddress: req.socket?.remoteAddress,
      bearerToken,
      authorization: req.headers.authorization,
    })
    if (!auth.allowed) return res.status(auth.status).json({ error: { code: auth.code, message: 'Request is not authorized.' } })
    next()
  })
}
