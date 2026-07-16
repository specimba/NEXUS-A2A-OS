import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const EXPECTED_VERSION = '1.18.0'
const EXPECTED_INTEGRITY = 'sha512-CGVYom1ehfcQIIDLhXwOXPwN1Jf2dk8MZoako6KZahADDfyq2NcvmkamlRFY16qbJFyDt0dEmRiHwZEeKBmTog=='

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'))
}

function requireEqual(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`${label} mismatch: expected ${expected}, got ${String(actual)}`)
  }
}

function requireMarker(body, marker, label) {
  if (!body.includes(marker)) throw new Error(`Missing ${label} marker: ${marker}`)
  return true
}

export async function verifyRuntime(options = {}) {
  const serviceRoot = resolve(options.serviceRoot || fileURLToPath(new URL('..', import.meta.url)))
  const packagePath = join(serviceRoot, 'package.json')
  const lockPath = join(serviceRoot, 'package-lock.json')
  const installedRoot = join(serviceRoot, 'node_modules', 'modelrelay')
  const installedPackagePath = join(installedRoot, 'package.json')
  const serverPath = join(installedRoot, 'lib', 'server.js')
  const publicPath = join(installedRoot, 'public', 'index.html')
  const configPath = join(installedRoot, 'lib', 'config.js')
  const utilsPath = join(installedRoot, 'lib', 'utils.js')
  const scoresPath = join(installedRoot, 'scores.js')
  const sourcesPath = join(installedRoot, 'sources.js')
  const policyPath = join(serviceRoot, 'src', 'nexus-runtime-policy.js')
  const patchPath = join(serviceRoot, 'patches', `modelrelay+${EXPECTED_VERSION}.patch`)

  const [manifest, lock, installed, server, publicDashboard, config, utils, scores, sources, policy, patch] = await Promise.all([
    readJson(packagePath),
    readJson(lockPath),
    readJson(installedPackagePath),
    readFile(serverPath, 'utf8'),
    readFile(publicPath, 'utf8'),
    readFile(configPath, 'utf8'),
    readFile(utilsPath, 'utf8'),
    readFile(scoresPath, 'utf8'),
    readFile(sourcesPath, 'utf8'),
    readFile(policyPath, 'utf8'),
    readFile(patchPath, 'utf8'),
  ])
  const locked = lock.packages?.['node_modules/modelrelay']
  if (!locked) throw new Error('package-lock.json has no modelrelay package record')

  requireEqual(manifest.dependencies?.modelrelay, EXPECTED_VERSION, 'manifest modelrelay version')
  requireEqual(installed.version, EXPECTED_VERSION, 'installed modelrelay version')
  requireEqual(locked.version, EXPECTED_VERSION, 'locked modelrelay version')
  requireEqual(locked.integrity, EXPECTED_INTEGRITY, 'locked modelrelay integrity')
  requireEqual(installed.license, 'MIT', 'installed modelrelay license')

  const patchMarkers = {
    safeRuntime: requireMarker(server, 'NEXUS_SAFE_RUNTIME', 'safe runtime'),
    configPath: requireMarker(config, 'NEXUS_CONFIG_PATH_MARKER', 'isolated config path'),
    nullUnknownScore: requireMarker(server, 'NEXUS_NULL_UNKNOWN_SCORE_MARKER', 'null unknown score'),
    unscoredStatic: requireMarker(scores, 'NEXUS_UNSCORED_STATIC_MARKER', 'unscored static model'),
    loopbackAdmin: requireMarker(server, 'installNexusSecurityMiddleware', 'security middleware'),
    governedProvider: requireMarker(server, 'nexusGovernor', 'provider governor'),
    twoCallBudget: requireMarker(server, 'new ProviderAttemptBudget(2)', 'two-call attempt budget'),
    scoped429: requireMarker(server, 'classifyRateLimitScope', 'scoped 429 handling'),
    entitlementAware: requireMarker(server, 'NEXUS_ENTITLEMENT_AWARE', 'bounded entitlement-aware routing'),
    entitlementVerdicts: requireMarker(utils, "'Subscription Required'", 'entitlement-aware API verdicts'),
    nvidiaPacing: requireMarker(policy, 'NVIDIA_MIN_START_INTERVAL_MS = 7_500', 'NVIDIA 8 RPM pacing'),
    nvidiaCooldown: requireMarker(policy, 'NVIDIA_RATE_LIMIT_FLOOR_MS = 75_000', 'NVIDIA cooldown floor'),
    nvidiaDegradedFunction: requireMarker(server, 'NEXUS_NIM_DEGRADED_FUNCTION', 'NVIDIA degraded-function failover'),
    actionableNimUnavailable: requireMarker(server, 'NEXUS_NIM_FUNCTION_DEGRADED', 'actionable NVIDIA degraded-function error'),
    inferenceFreeRefresh: requireMarker(server, 'Catalogue refresh is inference-free', 'inference-free refresh'),
    leanstralAlias: requireMarker(sources, "'leanstral': 'labs-leanstral-1-5-1'", 'Leanstral alias'),
    glm52Context: requireMarker(sources, "'z-ai/glm-5.2': '1M'", 'GLM-5.2 context'),
    canonicalDedup: requireMarker(utils, 'const deduped = new Map()', 'canonical model de-duplication'),
    providerQualifiedRoutes: requireMarker(server, 'projectRoutableModelIds(groups)', 'provider-qualified model projection'),
    logicalOfferGroups: requireMarker(utils, 'const matchedGroup = groups.find(group => {', 'logical offer group routing'),
    offerScopedAbort: requireMarker(server, 'createOfferScopedAbortSignal(requestAbort.signal', 'offer-scoped first-byte abort'),
    adaptiveFirstByteDeadline: requireMarker(policy, 'computeOfferFirstByteDeadlineMs', 'evidence-aware first-byte deadline'),
    routeFirstByteBudget: requireMarker(server, 'MODELRELAY_ROUTE_FIRST_BYTE_BUDGET_MS', 'request route first-byte budget'),
    structuredRouteReceipt: requireMarker(server, 'NEXUS_NO_HEALTHY_MODEL_OFFER', 'structured route receipt'),
    immediateTimeoutQuarantine: requireMarker(policy, 'if (options.offer) this.openOfferCircuit(options.offer)', 'immediate timeout quarantine'),
    boundedCanarySampler: requireMarker(server, 'new BoundedCanarySampler', 'bounded canary sampler'),
    healthSamplerEndpoint: requireMarker(server, "app.get('/api/health-sampler'", 'health sampler endpoint'),
    terminalCanaryExclusion: requireMarker(policy, 'terminalCanaryExclusions', 'terminal 410 canary exclusion telemetry'),
    providerAwareManualPing: requireMarker(server, 'providerKey is required', 'provider-aware manual ping'),
    truthfulDashboardHealth: requireMarker(publicDashboard, 'function modelHealthView(model)', 'fresh stale unverified dashboard health'),
    providerQualifiedDashboardRows: requireMarker(publicDashboard, 'currentRenderedOrder = sorted.map(m => getModelRowKey(m))', 'provider-qualified dashboard rows'),
    persistentHealthObservations: requireMarker(server, 'nexusHealthSampler.observe(best', 'persistent real-traffic health observations'),
    healthHydration: requireMarker(server, 'nexusHealthSampler.hydrate(results)', 'health observation hydration'),
    persistentCooldownRestore: requireMarker(policy, 'restoreCooldowns(governor', 'persistent exact-offer cooldown restore'),
    resilientAlias: requireMarker(server, 'NEXUS_RESILIENT_ALIAS', 'fresh-health-only resilient alias'),
  }
  requireMarker(patch, 'NEXUS_SAFE_RUNTIME', 'patch payload')
  requireMarker(patch, 'ProviderAttemptBudget', 'patch attempt budget')
  requireMarker(patch, 'NEXUS_ENTITLEMENT_AWARE', 'patch bounded entitlement-aware routing')
  requireMarker(patch, "'Subscription Required'", 'patch entitlement-aware API verdicts')
  requireMarker(patch, 'labs-leanstral-1-5-1', 'patch Leanstral alias')
  requireMarker(patch, 'createOfferScopedAbortSignal', 'patch offer-scoped abort')
  requireMarker(patch, 'computeOfferFirstByteDeadlineMs', 'patch evidence-aware first-byte deadline')
  requireMarker(patch, 'MODELRELAY_ROUTE_FIRST_BYTE_BUDGET_MS', 'patch route first-byte budget')
  requireMarker(patch, 'sanitizeProxyAttempts', 'patch sanitized route receipt')
  requireMarker(patch, 'NEXUS_NO_HEALTHY_MODEL_OFFER', 'patch structured failure code')
  requireMarker(patch, 'BoundedCanarySampler', 'patch bounded canary sampler')
  requireMarker(patch, "/api/health-sampler", 'patch health sampler endpoint')
  requireMarker(patch, 'function modelHealthView(model)', 'patch truthful dashboard health')
  requireMarker(patch, 'nexusHealthSampler.observe(best', 'patch persistent real-traffic health')
  requireMarker(patch, 'NEXUS_RESILIENT_ALIAS', 'patch resilient alias')
  requireMarker(patch, 'NEXUS_NIM_DEGRADED_FUNCTION', 'patch NVIDIA degraded-function failover')
  requireMarker(patch, 'NEXUS_NIM_FUNCTION_DEGRADED', 'patch actionable NVIDIA degraded-function error')

  return {
    ok: true,
    version: installed.version,
    integrity: locked.integrity,
    patchSha256: createHash('sha256').update(patch).digest('hex'),
    patchMarkers,
  }
}

async function main() {
  const report = await verifyRuntime()
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  main().catch(error => {
    process.stderr.write(`ModelRelay runtime verification failed: ${error.message}\n`)
    process.exitCode = 1
  })
}
