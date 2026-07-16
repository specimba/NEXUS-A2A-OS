import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  authorizeRequest,
  buildCorsHeaders,
  isLoopbackAddress,
  sanitizeConfigResponse,
  validateBindPolicy,
} from '../src/nexus-runtime-policy.js'

test('bind policy fails closed when a non-loopback listener lacks a bearer token', () => {
  assert.doesNotThrow(() => validateBindPolicy({ bind: '127.0.0.1', bearerToken: '' }))
  assert.doesNotThrow(() => validateBindPolicy({ bind: '::1', bearerToken: '' }))
  assert.throws(
    () => validateBindPolicy({ bind: '0.0.0.0', bearerToken: '' }),
    /bearer token/i,
  )
  assert.doesNotThrow(() => validateBindPolicy({ bind: '0.0.0.0', bearerToken: 'long-enough-test-token' }))
})

test('admin API is loopback-only and remote v1 requires exact bearer auth', () => {
  assert.equal(isLoopbackAddress('::ffff:127.0.0.1'), true)
  assert.deepEqual(authorizeRequest({ path: '/api/models', remoteAddress: '127.0.0.1' }), { allowed: true })
  assert.equal(authorizeRequest({ path: '/api/models', remoteAddress: '192.168.1.7' }).status, 403)
  assert.equal(authorizeRequest({ path: '/v1/models', remoteAddress: '192.168.1.7', bearerToken: 'secret', authorization: '' }).status, 401)
  assert.equal(authorizeRequest({ path: '/v1/models', remoteAddress: '192.168.1.7', bearerToken: 'secret', authorization: 'Bearer wrong' }).status, 401)
  assert.deepEqual(authorizeRequest({ path: '/v1/models', remoteAddress: '192.168.1.7', bearerToken: 'secret', authorization: 'Bearer secret' }), { allowed: true })
  assert.deepEqual(authorizeRequest({ path: '/v1/models', remoteAddress: '127.0.0.1', bearerToken: '' }), { allowed: true })
})

test('config sanitization never returns raw provider keys, pool values, or OAuth secrets', () => {
  const raw = [{
    key: 'nvidia',
    hasKey: true,
    apiKey: 'nvapi-live-secret',
    refreshToken: 'refresh-secret',
    apiKeyPool: [
      { index: 0, masked: 'nvap...cret', key: 'nvapi-live-secret' },
      { index: 1, masked: 'nvap...ret2', key: 'nvapi-live-secret2' },
    ],
  }]
  const sanitized = sanitizeConfigResponse(raw)
  const text = JSON.stringify(sanitized)

  assert.equal(text.includes('nvapi-live-secret'), false)
  assert.equal(text.includes('refresh-secret'), false)
  assert.deepEqual(sanitized[0].apiKeyPool, [
    { index: 0, masked: 'nvap...cret' },
    { index: 1, masked: 'nvap...ret2' },
  ])
})

test('CORS only reflects configured origins and never falls back to wildcard', () => {
  assert.deepEqual(buildCorsHeaders({ origin: undefined, allowedOrigins: ['http://localhost:7356'] }), {})
  assert.deepEqual(buildCorsHeaders({ origin: 'https://evil.example', allowedOrigins: ['http://localhost:7356'] }), {})
  assert.deepEqual(buildCorsHeaders({ origin: 'http://localhost:7356', allowedOrigins: ['http://localhost:7356'] }), {
    'Access-Control-Allow-Origin': 'http://localhost:7356',
    Vary: 'Origin',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  })
})
