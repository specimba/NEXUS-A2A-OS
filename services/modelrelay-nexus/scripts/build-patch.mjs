import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const configPath = join(root, 'node_modules', 'modelrelay', 'lib', 'config.js')
const serverPath = join(root, 'node_modules', 'modelrelay', 'lib', 'server.js')
const utilsPath = join(root, 'node_modules', 'modelrelay', 'lib', 'utils.js')
const scoresPath = join(root, 'node_modules', 'modelrelay', 'scores.js')
const sourcesPath = join(root, 'node_modules', 'modelrelay', 'sources.js')

function lines(...values) {
  return values.join('\n')
}

function replaceExact(body, label, before, after, expected = 1) {
  const count = body.split(before).length - 1
  if (count !== expected) throw new Error(`${label}: expected ${expected} preimage(s), found ${count}`)
  return body.split(before).join(after)
}

let config = await readFile(configPath, 'utf8')

async function runtimeIsVerified() {
  try {
    const { verifyRuntime } = await import('../src/verify-runtime.mjs')
    await verifyRuntime({ serviceRoot: root })
    return true
  } catch {
    return false
  }
}

// Historical exact transforms below are deliberately unreachable. The reviewed
// patch-package payload is the only mutation path; this file now verifies an
// already-patched tree and fails closed on pristine or partially patched input.
if (!(await runtimeIsVerified())) {
  throw new Error('Legacy patch builder is disabled; run npm run patch:apply-reviewed.')
}
process.stdout.write('Verified reviewed NEXUS ModelRelay 1.18.0 patch.\n')
process.exit(0)
config = replaceExact(
  config,
  'isolated config path',
  "export const CONFIG_PATH = join(homedir(), '.modelrelay.json')",
  lines(
    '// NEXUS_CONFIG_PATH_MARKER: the pinned runtime may use an isolated fixture.',
    'export const CONFIG_PATH = process.env.MODELRELAY_CONFIG_PATH',
    '  ? process.env.MODELRELAY_CONFIG_PATH',
    "  : join(homedir(), '.modelrelay.json')",
  ),
)
await writeFile(configPath, config, 'utf8')

let scores = await readFile(scoresPath, 'utf8')
scores = replaceExact(
  scores,
  'remove inherited 45 percent placeholder',
  '  "mistralai/magistral-small-2506": 0.45,',
  '  "mistralai/magistral-small-2506": null, // NEXUS_UNSCORED_STATIC_MARKER',
)
await writeFile(scoresPath, scores, 'utf8')

let sources = await readFile(sourcesPath, 'utf8')
sources = replaceExact(
  sources,
  'Leanstral canonical aliases',
  lines(
    "  'glm-5.2': 'z-ai/glm-5.2',",
    "  'kimi-k2': 'moonshotai/kimi-k2-instruct',",
  ),
  lines(
    "  'glm-5.2': 'z-ai/glm-5.2',",
    "  'labs-leanstral-1-5': 'labs-leanstral-1-5-1',",
    "  'leanstral': 'labs-leanstral-1-5-1',",
    "  'mistralai/Leanstral-1.5-119B-A6B': 'labs-leanstral-1-5-1',",
    "  'kimi-k2': 'moonshotai/kimi-k2-instruct',",
  ),
)
sources = replaceExact(
  sources,
  'Leanstral labels',
  lines(
    "  'glm-5.2': 'GLM 5.2',",
    "  'hy3-free': 'Hy3',",
  ),
  lines(
    "  'glm-5.2': 'GLM 5.2',",
    "  'labs-leanstral-1-5-1': 'Leanstral 1.5',",
    "  'labs-leanstral-1-5': 'Leanstral 1.5',",
    "  'leanstral': 'Leanstral 1.5',",
    "  'mistralai/Leanstral-1.5-119B-A6B': 'Leanstral 1.5',",
    "  'hy3-free': 'Hy3',",
  ),
)
sources = replaceExact(
  sources,
  'canonical context overrides',
  'export const MODEL_CONTEXT_OVERRIDES = {',
  lines(
    'export const MODEL_CONTEXT_OVERRIDES = {',
    "  'labs-leanstral-1-5-1': '256k',",
    "  'z-ai/glm-5.2': '1M',",
    "  'zai-org/GLM-5.2': '1M',",
  ),
)
await writeFile(sourcesPath, sources, 'utf8')

let utils = await readFile(utilsPath, 'utf8')
utils = replaceExact(
  utils,
  'canonical group de-duplication',
  '  return Array.from(groups.values())',
  lines(
    '  const deduped = new Map()',
    '  for (const group of groups.values()) {',
    '    const existing = deduped.get(group.id)',
    '    if (!existing) {',
    '      deduped.set(group.id, group)',
    '      continue',
    '    }',
    '    for (const alias of group.aliases) existing.aliases.add(alias)',
    '    existing.models.push(...group.models)',
    '  }',
    '  return Array.from(deduped.values())',
  ),
)
utils = replaceExact(
  utils,
  'canonical alias precedence before raw exact IDs',
  lines(
    '  const requested = normalizeModelAlias(requestedModel)',
    '  const providerQualifiedMatches = results.filter(r => getRoutingModelKey(r) === requested)',
    '  if (providerQualifiedMatches.length > 0) return providerQualifiedMatches',
    '',
    '  const exactMatches = results.filter(r => normalizeModelAlias(r.modelId) === requested)',
  ),
  lines(
    '  const requested = normalizeModelAlias(requestedModel)',
    '  const providerQualifiedMatches = results.filter(r => getRoutingModelKey(r) === requested)',
    '  if (providerQualifiedMatches.length > 0) return providerQualifiedMatches',
    '',
    "  const canonicalTarget = typeof canonicalizeFn === 'function'",
    '    ? normalizeModelAlias(canonicalizeFn(requestedModel).base)',
    "    : ''",
    '  if (canonicalTarget && canonicalTarget !== requested) {',
    '    const canonicalMatches = results.filter(r => normalizeModelAlias(r.modelId) === canonicalTarget)',
    '    if (canonicalMatches.length > 0) return canonicalMatches',
    '  }',
    '',
    '  const exactMatches = results.filter(r => normalizeModelAlias(r.modelId) === requested)',
  ),
)

let server = await readFile(serverPath, 'utf8')
server = replaceExact(
  server,
  'policy import',
  "import { buildWindowsPostUpdateRestartCommand, fetchLatestNpmVersion, isRunningFromSource, isVersionNewer, runUpdateCommand } from './update.js';",
  lines(
    "import { buildWindowsPostUpdateRestartCommand, fetchLatestNpmVersion, isRunningFromSource, isVersionNewer, runUpdateCommand } from './update.js';",
    "import { NEXUS_SAFE_RUNTIME, ProviderAttemptBudget, ProviderGovernor, classifyRateLimitScope, installNexusSecurityMiddleware, parseRetryAfterMs, projectRoutableModelIds, sanitizeConfigResponse, validateBindPolicy } from '../../../src/nexus-runtime-policy.js';",
  ),
)
server = replaceExact(server, 'attempt cap', 'const MAX_PROACTIVE_RETRIES = 5;', 'const MAX_PROACTIVE_RETRIES = NEXUS_SAFE_RUNTIME ? 1 : 5;')
server = replaceExact(
  server,
  'null unknown score',
  'const DEFAULT_DYNAMIC_MODEL_INTELL = 0.45;',
  lines(
    '// NEXUS_NULL_UNKNOWN_SCORE_MARKER: unknown evidence is never a synthetic 45%.',
    'const DEFAULT_DYNAMIC_MODEL_INTELL = NEXUS_SAFE_RUNTIME ? null : 0.45;',
  ),
)
server = replaceExact(
  server,
  'configured model canonical context',
  '    ctx: known?.ctx || DEFAULT_DYNAMIC_MODEL_CTX,',
  '    ctx: getPreferredModelContext(modelId, known?.ctx || DEFAULT_DYNAMIC_MODEL_CTX),',
)
server = replaceExact(
  server,
  'discovered model canonical context',
  lines(
    '  const ctxRaw = record && typeof record === \'object\'',
    '    ? (record.context_length ?? record.contextLength ?? record.ctx ?? null)',
    '    : null;',
    '  const ctx = parseKiloCodeContext(ctxRaw) || known?.ctx || DEFAULT_DYNAMIC_MODEL_CTX;',
  ),
  lines(
    '  const ctxRaw = record && typeof record === \'object\'',
    '    ? (record.context_length ?? record.contextLength ?? record.ctx ?? null)',
    '    : null;',
    '  const observedContext = ctxRaw == null',
    '    ? (known?.ctx || DEFAULT_DYNAMIC_MODEL_CTX)',
    '    : parseKiloCodeContext(ctxRaw);',
    '  const ctx = getPreferredModelContext(scoreLookupId, observedContext);',
  ),
)
server = replaceExact(
  server,
  'configured and discovered alias merge',
  lines(
    '    providerUrl: providerUrl || undefined,',
    '  };',
    '}',
    '',
    'export async function fetchOpenAICompatibleDiscoveredModels(config, instanceKey) {',
  ),
  lines(
    '    providerUrl: providerUrl || undefined,',
    '  };',
    '}',
    '',
    'export function mergeConfiguredAndDiscoveredModels(configured, discovered = []) {',
    '  const merged = [];',
    '  const seen = new Set();',
    '  for (const model of [...discovered, ...(configured ? [configured] : [])]) {',
    '    const canonicalId = resolveAliasedModelId(model?.modelId);',
    '    if (!model?.modelId || seen.has(canonicalId)) continue;',
    '    seen.add(canonicalId);',
    '    merged.push(model);',
    '  }',
    '  return merged;',
    '}',
    '',
    'export async function fetchOpenAICompatibleDiscoveredModels(config, instanceKey) {',
  ),
)
server = replaceExact(
  server,
  'static model canonical context',
  lines(
    '      isEstimatedScore: isEstimatedScoreOverride ?? !hasScore,',
    '      ctx,',
    '      providerKey,',
  ),
  lines(
    '      isEstimatedScore: isEstimatedScoreOverride ?? !hasScore,',
    '      ctx: getPreferredModelContext(modelId, ctx),',
    '      providerKey,',
  ),
)
server = replaceExact(
  server,
  'dynamic alias de-duplication',
  lines(
    '      const merged = fallbackModel',
    '        ? [fallbackModel, ...discovered.filter(m => m.modelId !== fallbackModel.modelId)]',
    '        : discovered;',
  ),
  '      const merged = mergeConfiguredAndDiscoveredModels(fallbackModel, discovered);',
)
server = replaceExact(
  server,
  'bind and governor',
  lines(
    '  let pinnedModelId = null;',
    '  let pinnedProviderKey = null;',
  ),
  lines(
    '  let pinnedModelId = null;',
    '  let pinnedProviderKey = null;',
    '  const nexusBind = validateBindPolicy({',
    "    bind: process.env.MODELRELAY_BIND || '127.0.0.1',",
    "    bearerToken: process.env.MODELRELAY_BEARER_TOKEN || '',",
    '  });',
    '  const nexusGovernor = new ProviderGovernor();',
  ),
)
server = replaceExact(
  server,
  'manual refresh fanout',
  '    if (providerModels.length === 0) return;',
  lines(
    '    if (providerModels.length === 0 || NEXUS_SAFE_RUNTIME) return;',
    '    // Completion probes are intentionally excluded from NEXUS safe runtime.',
    '    // An explicit, provider-scoped canary is implemented outside this refresh path.',
  ),
)
server = replaceExact(
  server,
  'scheduled health switch',
  '      if (!isAutoPingEnabled(currentConfig)) {',
  '      if (!NEXUS_SAFE_RUNTIME && !isAutoPingEnabled(currentConfig)) {',
)
server = replaceExact(
  server,
  'scheduled inference fanout',
  lines(
    '      const now = Date.now();',
    '      for (const r of results) {',
    '        const pingIntervalMs = getProviderPingIntervalMs(currentConfig, r.providerKey);',
    '        const lastActivityAt = Math.max(r.lastModelResponseAt || 0, r.lastPingAt || 0);',
    '        if (now - lastActivityAt < pingIntervalMs) continue;',
    '        pingModel(r).catch(() => { });',
    '      }',
  ),
  lines(
    '      if (!NEXUS_SAFE_RUNTIME) {',
    '        const now = Date.now();',
    '        for (const r of results) {',
    '          const pingIntervalMs = getProviderPingIntervalMs(currentConfig, r.providerKey);',
    '          const lastActivityAt = Math.max(r.lastModelResponseAt || 0, r.lastPingAt || 0);',
    '          if (now - lastActivityAt < pingIntervalMs) continue;',
    '          pingModel(r).catch(() => { });',
    '        }',
    '      }',
  ),
)
server = replaceExact(
  server,
  'auto-update hard stop',
  lines(
    '    const currentConfig = loadConfig();',
    '    const state = normalizeAutoUpdateState(currentConfig);',
  ),
  lines(
    '    const currentConfig = loadConfig();',
    "    if (NEXUS_SAFE_RUNTIME || process.env.MODELRELAY_DISABLE_AUTO_UPDATE === '1') {",
    "      return { ok: true, message: 'Auto-update is disabled by NEXUS runtime policy.' };",
    '    }',
    '    const state = normalizeAutoUpdateState(currentConfig);',
  ),
)
server = replaceExact(
  server,
  'startup catalogue-only sequence',
  lines(
    "  process.stdout.write(chalk.dim('  ⏳ Initializing model health checks... '));",
    '  await safeRefreshProviderModels(() => refreshKiloCodeModels(true));',
    '  await safeRefreshProviderModels(() => refreshOpenRouterModels(true));',
    '  await safeRefreshProviderModels(() => refreshOpenAICompatibleModels(null, true));',
    '  await safeRefreshProviderModels(() => refreshOllamaModels(true));',
    '  await Promise.all(results.map(r => pingModel(r)));',
  ),
  lines(
    "  process.stdout.write(chalk.dim(NEXUS_SAFE_RUNTIME ? '  ⏳ Initializing provider catalogues... ' : '  ⏳ Initializing model health checks... '));",
    '  await safeRefreshProviderModels(() => refreshKiloCodeModels(true));',
    '  await safeRefreshProviderModels(() => refreshOpenCodeModels(true));',
    '  await safeRefreshProviderModels(() => refreshOpenRouterModels(true));',
    '  await safeRefreshProviderModels(() => refreshOpenAICompatibleModels(null, true));',
    '  await safeRefreshProviderModels(() => refreshOllamaModels(true));',
    '  if (!NEXUS_SAFE_RUNTIME) await Promise.all(results.map(r => pingModel(r)));',
  ),
)
server = replaceExact(
  server,
  'security and CORS middleware',
  lines(
    "  app.use(express.static(path.join(__dirname, '../public')));",
    '  app.use(express.json({ limit: jsonBodyLimit }));',
    '',
    '  // CORS',
    '  app.use((req, res, next) => {',
    "    res.header('Access-Control-Allow-Origin', '*');",
    "    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');",
    "    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');",
    "    if (req.method === 'OPTIONS') {",
    '      return res.sendStatus(204);',
    '    }',
    '    next();',
    '  });',
  ),
  lines(
    '  if (NEXUS_SAFE_RUNTIME) {',
    '    installNexusSecurityMiddleware(app, {',
    "      allowedOrigins: process.env.MODELRELAY_ALLOWED_ORIGINS || 'http://127.0.0.1:7356,http://localhost:7356,http://127.0.0.1:3001,http://localhost:3001',",
    "      bearerToken: process.env.MODELRELAY_BEARER_TOKEN || '',",
    '    });',
    '  }',
    '',
    '  // CORS',
    '  if (!NEXUS_SAFE_RUNTIME) {',
    '    app.use((req, res, next) => {',
    "      res.header('Access-Control-Allow-Origin', '*');",
    "      res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');",
    "      res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');",
    "      if (req.method === 'OPTIONS') return res.sendStatus(204);",
    '      next();',
    '    });',
    '  }',
    "  app.use(express.static(path.join(__dirname, '../public')));",
    '  app.use(express.json({ limit: jsonBodyLimit }));',
  ),
)
server = replaceExact(server, 'sanitized config response', '    res.json(providers);', '    res.json(NEXUS_SAFE_RUNTIME ? sanitizeConfigResponse(providers) : providers);')
server = replaceExact(
  server,
  'provider refresh fanout',
  '      void Promise.allSettled(providerModels.map(r => pingModel(r)));',
  '      if (!NEXUS_SAFE_RUNTIME) void Promise.allSettled(providerModels.map(r => pingModel(r)));',
)
server = replaceExact(
  server,
  'refresh-all fanout',
  lines(
    '    // Ping all models after refreshing',
    '    void Promise.allSettled(results.map(r => pingModel(r)));',
  ),
  lines(
    '    // Catalogue refresh is inference-free in the NEXUS safe runtime.',
    '    if (!NEXUS_SAFE_RUNTIME) void Promise.allSettled(results.map(r => pingModel(r)));',
  ),
)
server = replaceExact(
  server,
  'request deadline setup',
  lines(
    "  app.post('/v1/chat/completions', async (req, res) => {",
    '    let logEntry = null;',
    '    try {',
    '      const payload = req.body;',
    '      const attemptedModelKeys = new Set();',
  ),
  lines(
    "  app.post('/v1/chat/completions', async (req, res) => {",
    '    let logEntry = null;',
    '    const requestAbort = new AbortController();',
    '    const nexusAttemptBudget = new ProviderAttemptBudget(2);',
    "    const totalTimeoutMs = Math.max(1, Number(process.env.MODELRELAY_TOTAL_TIMEOUT_MS || 180_000));",
    "    const firstByteTimeoutMs = Math.max(1, Number(process.env.MODELRELAY_FIRST_BYTE_TIMEOUT_MS || 45_000));",
    '    const totalTimer = setTimeout(() => {',
    '      const error = new Error(`Provider request exceeded total deadline ${totalTimeoutMs}ms.`);',
    "      error.name = 'TimeoutError';",
    "      error.code = 'NEXUS_TOTAL_TIMEOUT';",
    '      requestAbort.abort(error);',
    '    }, totalTimeoutMs);',
    "    const abortForClient = () => requestAbort.abort(new DOMException('Client disconnected.', 'AbortError'));",
    "    req.once('aborted', abortForClient);",
    "    res.once('close', () => {",
    '      clearTimeout(totalTimer);',
    '      if (!res.writableEnded) abortForClient();',
    '    });',
    "    res.once('finish', () => clearTimeout(totalTimer));",
    '    try {',
    '      const payload = req.body;',
    '      const attemptedModelKeys = new Set();',
  ),
)
server = replaceExact(
  server,
  'provider-aware selection',
  lines(
    '      const pickNextModel = () => {',
    '        if (pinnedModelId) {',
    '          const pinningMode = getPinningMode(loadConfig());',
    '          const pinned = getPinnedModelCandidate(results, pinnedModelId, pinningMode, Array.from(attemptedModelKeys), pinnedProviderKey);',
  ),
  lines(
    '      const pickNextModel = () => {',
    '        const eligible = NEXUS_SAFE_RUNTIME',
    '          ? requestedModels.filter(r => nexusGovernor.isAvailable(r.providerKey) && nexusGovernor.isOfferAvailable({ providerKey: r.providerKey, modelId: r.modelId }))',
    '          : requestedModels;',
    '        if (pinnedModelId) {',
    '          const pinningMode = getPinningMode(loadConfig());',
    '          const pinned = getPinnedModelCandidate(eligible, pinnedModelId, pinningMode, Array.from(attemptedModelKeys), pinnedProviderKey);',
  ),
)
server = replaceExact(
  server,
  'provider-aware ranking',
  '        const ranked = rankModelsForRouting(requestedModels, Array.from(attemptedModelKeys));',
  '        const ranked = rankModelsForRouting(eligible, Array.from(attemptedModelKeys));',
)
server = replaceExact(
  server,
  'governed fetch helper',
  lines(
    '        const t0 = performance.now();',
    '        let response;',
    '        try {',
  ),
  lines(
    '        const t0 = performance.now();',
    '        let response;',
    '        const nexusOffer = () => ({',
    '          providerKey: best.providerKey,',
    '          modelId: best.modelId,',
    '          offerId: getRoutingModelKey(best),',
    "          accountKey: providerAuth.token ? createHash('sha256').update(String(providerAuth.token)).digest('hex').slice(0, 16) : null,",
    "          connectionKey: providerUrl ? createHash('sha256').update(String(providerUrl)).digest('hex').slice(0, 16) : null,",
    '        });',
    '        const fetchProvider = async (url, init) => {',
    '          const fetchOnce = async () => {',
    '            const firstByteTimer = setTimeout(() => {',
    '              const error = new Error(`Provider did not return response headers within ${firstByteTimeoutMs}ms.`);',
    "              error.name = 'TimeoutError';",
    "              error.code = 'NEXUS_FIRST_BYTE_TIMEOUT';",
    '              requestAbort.abort(error);',
    '            }, firstByteTimeoutMs);',
    '            try {',
    '              return await fetch(url, { ...init, signal: requestAbort.signal });',
    '            } finally {',
    '              clearTimeout(firstByteTimer);',
    '            }',
    '          };',
    '          if (!NEXUS_SAFE_RUNTIME) return fetchOnce();',
    '          return nexusGovernor.run(',
    '            best.providerKey,',
    '            () => nexusAttemptBudget.run(fetchOnce),',
    '            { signal: requestAbort.signal, offer: nexusOffer() },',
    '          );',
    '        };',
    '        try {',
  ),
)
server = replaceExact(server, 'provider fetch calls', 'response = await fetch(providerUrl, {', 'response = await fetchProvider(providerUrl, {', 2)
server = replaceExact(
  server,
  'two-call attempt budget loop',
  '      for (let retry = 0; retry <= MAX_PROACTIVE_RETRIES; retry++) {',
  lines(
    '      for (let retry = 0; retry <= MAX_PROACTIVE_RETRIES; retry++) {',
    '        if (NEXUS_SAFE_RUNTIME && nexusAttemptBudget.remaining === 0) break;',
  ),
)
server = replaceExact(
  server,
  'optional bearer fallback budget',
  '          if (shouldRetryOptionalProviderWithBearer(currentConfig, best.providerKey, providerAuth, String(response.status), null)) {',
  '          if ((!NEXUS_SAFE_RUNTIME || nexusAttemptBudget.remaining > 0) && shouldRetryOptionalProviderWithBearer(currentConfig, best.providerKey, providerAuth, String(response.status), null)) {',
)
server = replaceExact(
  server,
  'abort stops retries',
  lines(
    '          attempts.push(attemptMeta);',
    '          if (retry === MAX_PROACTIVE_RETRIES) {',
  ),
  lines(
    '          attempts.push(attemptMeta);',
    '          if (NEXUS_SAFE_RUNTIME && requestAbort.signal.aborted) throw requestAbort.signal.reason;',
    '          if (retry === MAX_PROACTIVE_RETRIES) {',
  ),
)
server = replaceExact(
  server,
  'scoped 429 and provider transient health',
  '        // On 429: mark this account as rate-limited so next retry picks a different key',
  lines(
    '        // 429 is scoped to the account/connection/model/offer, never the whole provider.',
    '        if (NEXUS_SAFE_RUNTIME) {',
    '          if (response.status === 429) {',
    '            const limitedOffer = nexusOffer();',
    '            nexusGovernor.openRateLimit(limitedOffer, {',
    '              scope: classifyRateLimitScope(response.headers, limitedOffer),',
    "              retryAfterMs: parseRetryAfterMs(response.headers.get('retry-after')),",
    '            });',
    '          } else {',
    "            const retryAfter = response.headers.get('retry-after');",
    '            nexusGovernor.recordStatus(best.providerKey, response.status, {',
    '              retryAfterMs: retryAfter ? parseRetryAfterMs(retryAfter) : undefined,',
    '            });',
    '          }',
    '        }',
    '        // Preserve upstream multi-account cooldown behavior.',
  ),
)
server = replaceExact(
  server,
  'stream error handling',
  '        Readable.fromWeb(selectedResponse.body).pipe(captureStream).pipe(res);',
  lines(
    '        const upstreamStream = Readable.fromWeb(selectedResponse.body);',
    "        upstreamStream.on('error', error => {",
    "          logEntry.status = 'err';",
    '          logEntry.error = error?.message || String(error);',
    '          saveLogs();',
    '          if (!res.destroyed) res.destroy(error);',
    '        });',
    '        upstreamStream.pipe(captureStream).pipe(res);',
  ),
)
server = replaceExact(
  server,
  'timeout response',
  lines(
    '    } catch (e) {',
    '      if (logEntry) {',
    "        logEntry.status = 'err';",
  ),
  lines(
    '    } catch (e) {',
    '      clearTimeout(totalTimer);',
    '      if (logEntry) {',
    "        logEntry.status = 'err';",
  ),
  1,
)
server = replaceExact(
  server,
  'fail-closed error response',
  "      res.status(400).json({ error: { message: e.message } });",
  lines(
    '      if (res.headersSent || res.destroyed) return;',
    "      const timeout = e?.name === 'TimeoutError' || String(e?.code || '').startsWith('NEXUS_');",
    '      res.status(timeout ? 504 : 400).json({ error: { message: e.message } });',
  ),
)
server = replaceExact(
  server,
  'provider-qualified v1 catalogue projection',
  lines(
    '    const groups = buildModelGroups(results, canonicalizeModelId)',
    '    const data = [',
    '      {',
  ),
  lines(
    '    const groups = buildModelGroups(results, canonicalizeModelId)',
    '    const routableModels = projectRoutableModelIds(groups)',
    '    const data = [',
    '      {',
  ),
)
server = replaceExact(
  server,
  'provider-qualified v1 catalogue rows',
  lines(
    '      ...groups.map(group => ({',
    '        id: group.id,',
    '        name: group.label,',
    '        object: "model",',
    '        created: Date.now(),',
    "        owned_by: 'relay'",
  ),
  lines(
    '      ...routableModels.map(model => ({',
    '        id: model.id,',
    '        name: model.name,',
    '        object: "model",',
    '        created: Date.now(),',
    "        owned_by: model.providerQualified ? 'relay-offer' : 'relay'",
  ),
)
server = replaceExact(server, 'bind listener', '  app.listen(port, () => {', '  app.listen(port, nexusBind, () => {')

await writeFile(serverPath, server, 'utf8')
process.stdout.write('Applied exact NEXUS ModelRelay 1.18.0 patch preimages.\n')
