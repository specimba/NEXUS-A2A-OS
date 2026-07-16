'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const { buildModelCardProjection } = require('./model_card_projection');

const rootDir = path.resolve(__dirname, '..');
const dashboardRoot = path.join(rootDir, 'nexus_os', 'monitoring');
const wikiRoot = path.join(rootDir, 'nexus_os', 'archivist', 'wiki-ui');
const modelRegistryPath = path.join(rootDir, 'config', 'models.registry.json');
const arenaSnapshotPath = path.join(rootDir, 'config', 'arena_scores.snapshot.json');
// The runtime overlay is produced by `python -m nexus_os.relay.arena_ingest`.
// It is mutable operational state, whereas the checked-in snapshot is a
// bounded fallback fixture.  The ignored repo-local default is deliberate:
// managed Windows profiles may deny writes below the service user's home
// directory.  An operator can set NEXUS_RUNTIME_STATE_ROOT for an external
// state volume, and can still override either specific child path.
const runtimeStateRoot = process.env.NEXUS_RUNTIME_STATE_ROOT
  || path.join(rootDir, 'logs', 'runtime-state');
const runtimeArenaScoresPath = process.env.NEXUS_ARENA_SCORES_PATH
  || path.join(runtimeStateRoot, 'arena', 'scores.json');
// Frontier discovery is deliberately a quarantined, candidate-only plane.
// The daily job writes this small delta outside the repository.  The Arena
// may report that fresh discovery evidence exists, but never imports a
// candidate into the provider registry, client manifests, or router.
const frontierScannerStatePath = process.env.NEXUS_FRONTIER_SCANNER_STATE
  || path.join(runtimeStateRoot, 'frontier_scanner');
const frontierCandidatesPath = path.join(frontierScannerStatePath, 'latest_candidates.json');
const runtimeArenaStatusPath = path.join(path.dirname(runtimeArenaScoresPath), 'frontier_intelligence_status.json');
const MAX_RUNTIME_ARENA_BYTES = 4 * 1024 * 1024;
const MAX_RUNTIME_ARENA_STATUS_BYTES = 64 * 1024;
const MAX_FRONTIER_CANDIDATES_BYTES = 2 * 1024 * 1024;
const MAX_FRONTIER_CANDIDATES = 2_000;
const MAX_FRONTIER_REVIEW_QUEUE = 100;
const RUNTIME_ARENA_MAX_AGE_MS = 30 * 60 * 60 * 1000;
const FRONTIER_CANDIDATES_FRESH_MS = 30 * 60 * 60 * 1000;
const FUTURE_CLOCK_SKEW_MS = 5 * 60 * 1000;
const RUNTIME_SOURCE_MAX_AGE_MS = {
  aa_coding: 7 * 24 * 60 * 60 * 1000,
  aa_intelligence_index: 7 * 24 * 60 * 60 * 1000,
  aa_speed: 7 * 24 * 60 * 60 * 1000,
  aa_price: 7 * 24 * 60 * 60 * 1000,
  lmarena_elo: 7 * 24 * 60 * 60 * 1000,
  lmarena_code_elo: 7 * 24 * 60 * 60 * 1000,
  openrouter_usage: 3 * 24 * 60 * 60 * 1000,
};
const modelRelayBaseUrl = String(process.env.MODELRELAY_BASE_URL || 'http://127.0.0.1:7350').replace(/\/+$/, '');
const port = Number.parseInt(process.env.PORT || '7356', 10) || 7356;
const host = process.env.HOST || '127.0.0.1';

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.wasm': 'application/wasm',
};

function sendText(res, statusCode, message) {
  res.writeHead(statusCode, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(message);
}

function sendJson(res, statusCode, payload, extraHeaders = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    ...extraHeaders,
  });
  res.end(body);
}

function readJsonFile(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function finiteUnitInterval(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 && number <= 1 ? number : null;
}

function parseTimestampMs(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readBoundedRuntimeOverlay(filePath = runtimeArenaScoresPath, nowMs = Date.now()) {
  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile() || stat.size <= 0 || stat.size > MAX_RUNTIME_ARENA_BYTES) return null;
    const payload = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const generatedAtMs = parseTimestampMs(payload?.generated_at);
    if (
      payload?.version !== 1
      || !payload?.models
      || typeof payload.models !== 'object'
      || generatedAtMs === null
      || generatedAtMs > nowMs + FUTURE_CLOCK_SKEW_MS
      || nowMs - generatedAtMs > RUNTIME_ARENA_MAX_AGE_MS
    ) return null;
    return payload;
  } catch {
    // A sidecar is optional operational evidence.  A missing, oversized, or
    // malformed sidecar must never take the dashboard down or fabricate data.
    return null;
  }
}

function runtimeRefreshStatusPath(overlayPath = runtimeArenaScoresPath) {
  return path.join(path.dirname(overlayPath), 'frontier_intelligence_status.json');
}

function readRuntimeRefreshStatus(filePath = runtimeArenaStatusPath, nowMs = Date.now()) {
  const absent = {
    state: 'absent',
    fresh: false,
    generated_at: null,
    age_seconds: null,
    offline: false,
    stages: { catalog: 'unknown', evidence_ingest: 'unknown', client_manifest_sync: 'unknown' },
    evidence_sidecar_accepted: false,
    candidate_delta_available: false,
  };
  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile() || stat.size <= 0 || stat.size > MAX_RUNTIME_ARENA_STATUS_BYTES) {
      return { ...absent, state: 'invalid' };
    }
    const payload = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const generatedAtMs = parseTimestampMs(payload?.generated_at);
    const allowedStates = new Set(['succeeded', 'failed']);
    const allowedStages = new Set(['succeeded', 'failed', 'skipped']);
    if (payload?.version !== 1 || generatedAtMs === null || !allowedStates.has(payload?.state)) {
      return { ...absent, state: 'invalid' };
    }
    const ageMs = Math.max(0, nowMs - generatedAtMs);
    const stage = (name) => allowedStages.has(payload?.stages?.[name])
      ? payload.stages[name]
      : 'unknown';
    return {
      state: payload.state,
      fresh: generatedAtMs <= nowMs + FUTURE_CLOCK_SKEW_MS && ageMs <= RUNTIME_ARENA_MAX_AGE_MS,
      generated_at: new Date(generatedAtMs).toISOString(),
      age_seconds: Math.floor(ageMs / 1_000),
      offline: payload?.offline === true,
      stages: {
        catalog: stage('catalog'),
        evidence_ingest: stage('evidence_ingest'),
        client_manifest_sync: stage('client_manifest_sync'),
      },
      evidence_sidecar_accepted: payload?.evidence_sidecar_accepted === true,
      candidate_delta_available: payload?.candidate_delta_available === true,
    };
  } catch (error) {
    if (error?.code === 'ENOENT') return absent;
    return { ...absent, state: 'invalid' };
  }
}

function compactCandidateText(value, maxLength) {
  const text = String(value || '').trim();
  if (!text) return null;
  return text.slice(0, maxLength);
}

function frontierIntelligencePolicy() {
  return {
    candidate_only: true,
    automatic_registration: false,
    automatic_routing: false,
    automatic_probing: false,
  };
}

function frontierReviewContract() {
  return {
    mode: 'operator_review_only',
    admission_state: 'awaiting_operator_review',
    required_evidence: [
      'confirm provider entitlement and endpoint contract',
      'perform one explicit bounded health probe after review',
      'attach compatible benchmark evidence or retain UNSCORED',
    ],
    promotion: 'separate explicit operator change; this endpoint cannot register, route, or probe a candidate',
  };
}

function frontierCandidateId(provider, modelId) {
  return `frontier-discovery::${encodeURIComponent(provider)}::${encodeURIComponent(modelId)}`;
}

function frontierDiscoveryClass(reason) {
  return String(reason || '').startsWith('baseline_established:')
    ? 'baseline_established'
    : 'catalogue_delta';
}

function buildFrontierReviewQueue(candidates) {
  const unique = new Map();
  for (const candidate of candidates) {
    const candidateId = frontierCandidateId(candidate.provider, candidate.model_id);
    if (unique.has(candidateId)) continue;
    unique.set(candidateId, {
      candidate_id: candidateId,
      provider: candidate.provider,
      model_id: candidate.model_id,
      discovery_class: frontierDiscoveryClass(candidate.reason),
      review_state: 'awaiting_operator_review',
      registration_state: 'not_registered',
      routing_state: 'not_routable',
      evidence_state: 'catalogue_delta_only',
    });
  }
  const allItems = [...unique.values()].sort(
    (left, right) => `${left.provider}/${left.model_id}`.localeCompare(`${right.provider}/${right.model_id}`),
  );
  return {
    total_candidates: allItems.length,
    emitted_candidates: Math.min(allItems.length, MAX_FRONTIER_REVIEW_QUEUE),
    truncated: allItems.length > MAX_FRONTIER_REVIEW_QUEUE,
    items: allItems.slice(0, MAX_FRONTIER_REVIEW_QUEUE),
  };
}

function emptyFrontierIntelligenceStatus(state, policy, reviewContract) {
  return {
    schema_version: 1,
    state,
    candidate_count: 0,
    providers: [],
    preview: [],
    review_queue: {
      total_candidates: 0,
      emitted_candidates: 0,
      truncated: false,
      items: [],
    },
    policy,
    review_contract: reviewContract,
  };
}

function readFrontierIntelligenceStatus(filePath = frontierCandidatesPath, nowMs = Date.now()) {
  const policy = frontierIntelligencePolicy();
  const reviewContract = frontierReviewContract();
  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile() || stat.size <= 0 || stat.size > MAX_FRONTIER_CANDIDATES_BYTES) {
      return emptyFrontierIntelligenceStatus('invalid', policy, reviewContract);
    }
    const payload = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    if (!Array.isArray(payload) || payload.length > MAX_FRONTIER_CANDIDATES) {
      return emptyFrontierIntelligenceStatus('invalid', policy, reviewContract);
    }
    const candidates = payload.flatMap((entry) => {
      const provider = compactCandidateText(entry?.provider, 80);
      const modelId = compactCandidateText(entry?.model_id, 240);
      if (!provider || !modelId) return [];
      const reason = compactCandidateText(entry?.reason, 120);
      return [{ provider, model_id: modelId, reason }];
    });
    const reviewQueue = buildFrontierReviewQueue(candidates);
    const queueItems = reviewQueue.items;
    const ageMs = Math.max(0, nowMs - stat.mtimeMs);
    const counts = new Map();
    for (const candidate of queueItems) {
      counts.set(candidate.provider, (counts.get(candidate.provider) || 0) + 1);
    }
    const baselineEstablishedCount = queueItems.filter(
      (candidate) => candidate.discovery_class === 'baseline_established',
    ).length;
    return {
      schema_version: 1,
      state: ageMs <= FRONTIER_CANDIDATES_FRESH_MS ? 'fresh' : 'stale',
      generated_at: new Date(stat.mtimeMs).toISOString(),
      age_seconds: Math.floor(ageMs / 1000),
      candidate_count: reviewQueue.total_candidates,
      baseline_established_count: baselineEstablishedCount,
      providers: [...counts.entries()]
        .map(([provider, candidate_count]) => ({ provider, candidate_count }))
        .sort((left, right) => left.provider.localeCompare(right.provider)),
      // Deliberately exclude arbitrary source metadata and raw provider
      // errors; both are untrusted discovery input and never routing data.
      preview: queueItems
        .slice(0, 8)
        .map(({ provider, model_id }) => ({ provider, model_id })),
      policy,
      review_contract: reviewContract,
      review_queue: reviewQueue,
    };
  } catch (error) {
    const code = error && error.code;
    return emptyFrontierIntelligenceStatus(
      code === 'ENOENT' ? 'absent' : 'invalid',
      policy,
      reviewContract,
    );
  }
}

function modelIdentifiers(model) {
  const values = [model?.id];
  if (Array.isArray(model?.aliases)) values.push(...model.aliases);
  return new Set(values.map((value) => String(value || '').trim().toLowerCase()).filter(Boolean));
}

function evidenceReleaseIdentity(value) {
  // Provider offerings commonly append only a transport entitlement marker
  // (`:free` / `-free`) to the same released model.  It is safe to bridge
  // that exact marker for public benchmark evidence; do not strip quality or
  // release qualifiers such as thinking, flash, pro, preview, or VL.
  const bare = String(value || '').trim().toLowerCase().split('/').pop() || '';
  return bare.replace(/(?:[:_-]free)$/, '');
}

function expandRegistryFamilyIdentifiers(registry, modelId) {
  // A runtime score is keyed by the registry's canonical ID.  Relay routes
  // often use a provider-specific alias (for example z-ai/glm-5.2).  Expand
  // through explicit registry aliases and an exact `free` offering identity
  // so a live score reaches that same released route without cross-family
  // name guessing.
  const identifiers = new Set([String(modelId || '').trim().toLowerCase()].filter(Boolean));
  const releaseIdentities = new Set([...identifiers].map(evidenceReleaseIdentity).filter(Boolean));
  const models = Array.isArray(registry?.models) ? registry.models : [];
  let changed = true;
  while (changed) {
    changed = false;
    for (const model of models) {
      const family = modelIdentifiers(model);
      const isExplicitAlias = [...family].some((identifier) => identifiers.has(identifier));
      const isExactFreeOffering = [...family].some(
        (identifier) => releaseIdentities.has(evidenceReleaseIdentity(identifier)),
      );
      if (!isExplicitAlias && !isExactFreeOffering) continue;
      for (const identifier of family) {
        if (!identifiers.has(identifier)) {
          identifiers.add(identifier);
          const releaseIdentity = evidenceReleaseIdentity(identifier);
          if (releaseIdentity) releaseIdentities.add(releaseIdentity);
          changed = true;
        }
      }
    }
  }
  return identifiers;
}

function freshRuntimeSources(entry, nowMs = Date.now()) {
  const sourceEntries = entry?.sources && typeof entry.sources === 'object' ? entry.sources : {};
  return Object.entries(sourceEntries).flatMap(([name, source]) => {
    const maxAgeMs = RUNTIME_SOURCE_MAX_AGE_MS[name];
    const fetchedAtMs = parseTimestampMs(source?.fetched_at);
    const normalized = finiteUnitInterval(source?.normalized);
    const trustTier = String(source?.trust_tier || '').toLowerCase();
    if (
      fetchedAtMs === null
      || maxAgeMs === undefined
      || fetchedAtMs > nowMs + FUTURE_CLOCK_SKEW_MS
      || nowMs - fetchedAtMs > maxAgeMs
      || source?.stale === true
      || normalized === null
    ) return [];
    return [{ name, normalized, trustTier, fetchedAt: source.fetched_at, fetchedAtMs }];
  });
}

function runtimeEntryToSnapshotEntry(entry, nowMs = Date.now()) {
  if (!entry || typeof entry !== 'object' || entry.no_data === true) return null;
  const arenaScore = finiteUnitInterval(entry.arena_score);
  const sources = freshRuntimeSources(entry, nowMs);
  const capabilitySources = sources.filter((source) => source.trustTier === 'tier1' || source.trustTier === 'tier2');
  if (arenaScore === null || capabilitySources.length === 0) return null;

  const sourceValue = (names) => {
    const matching = sources.find((source) => names.includes(source.name));
    return matching ? matching.normalized : null;
  };
  const asOf = capabilitySources
    .slice()
    .sort((left, right) => right.fetchedAtMs - left.fetchedAtMs)[0]
    .fetchedAt;
  return {
    arena_score: arenaScore,
    code_score: sourceValue(['lmarena_code_elo', 'aa_coding']),
    // The ingest sidecar contains no task-specific reasoning or SWE result;
    // keep those dimensions null rather than synthesizing a proxy score.
    reasoning_score: null,
    swe_score: null,
    speed_score: sourceValue(['aa_speed']),
    cost_efficiency_score: null,
    confidence: String(entry.confidence || 'unknown'),
    sources: sources.map((source) => source.name),
    as_of: asOf,
    evidence_origin: 'runtime_overlay',
  };
}

function buildArenaSnapshot(registry, nowMs = Date.now(), overlayPath = runtimeArenaScoresPath) {
  const runtimeRefresh = readRuntimeRefreshStatus(runtimeRefreshStatusPath(overlayPath), nowMs);
  const staticSnapshot = fs.existsSync(arenaSnapshotPath)
    ? readJsonFile(arenaSnapshotPath)
    : { version: 1, models: {} };
  const snapshotFallback = {
    ...staticSnapshot,
    evidence_mode: 'snapshot_fallback',
    runtime_refresh: runtimeRefresh,
  };
  const runtimeOverlay = readBoundedRuntimeOverlay(overlayPath, nowMs);
  if (!runtimeOverlay) return snapshotFallback;

  const runtimeModels = {};
  for (const [modelId, entry] of Object.entries(runtimeOverlay.models)) {
    const normalized = runtimeEntryToSnapshotEntry(entry, nowMs);
    if (!normalized) continue;
    for (const identifier of expandRegistryFamilyIdentifiers(registry, modelId)) {
      runtimeModels[identifier] = normalized;
    }
  }
  if (Object.keys(runtimeModels).length === 0) return snapshotFallback;
  return {
    version: 1,
    generated_at: runtimeOverlay.generated_at,
    evidence_mode: 'runtime_overlay_with_snapshot_fallback',
    runtime_refresh: runtimeRefresh,
    models: {
      ...(snapshotFallback?.models && typeof snapshotFallback.models === 'object' ? snapshotFallback.models : {}),
      ...runtimeModels,
    },
  };
}

async function fetchRelayJson(pathname) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);
  try {
    const response = await fetch(`${modelRelayBaseUrl}${pathname}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`ModelRelay ${pathname} returned HTTP ${response.status}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function buildLiveModelCards() {
  const [arenaPayload, v1Payload, providerConfigs] = await Promise.all([
    fetchRelayJson('/api/models'),
    fetchRelayJson('/v1/models'),
    fetchRelayJson('/api/config'),
  ]);
  return buildModelCardProjection({
    arenaModels: Array.isArray(arenaPayload?.models) ? arenaPayload.models : [],
    v1Models: Array.isArray(v1Payload?.data) ? v1Payload.data : [],
    providerConfigs: Array.isArray(providerConfigs) ? providerConfigs : [],
    registry: readJsonFile(modelRegistryPath),
    arenaSnapshot: buildArenaSnapshot(readJsonFile(modelRegistryPath)),
  });
}

// A client must not infer a usable model list from the raw relay catalogue:
// it contains aliases, internal offers, and non-chat records.  This manifest
// is the narrow, versioned contract consumed by CLI synchronizers.  It is
// generated from the same live projection as the Arena UI, so the UI and
// clients cannot silently disagree about health or benchmark provenance.
const CLIENT_HEALTH_RANK = {
  healthy: 5,
  stale: 4,
  unverified: 3,
  rate_limited: 2,
  auth_required: 1,
  unavailable: 0,
  excluded: -1,
  unknown: -2,
};

function clientCardRank(card) {
  const health = CLIENT_HEALTH_RANK[card?.health?.state] ?? -2;
  const evidence = card?.benchmarks?.status === 'evidence_backed' ? 1 : 0;
  const quality = evidence && Number.isFinite(card?.benchmarks?.dimensions?.quality)
    ? card.benchmarks.dimensions.quality
    : -1;
  const context = Number.isFinite(card?.registry?.context_tokens)
    ? card.registry.context_tokens
    : 0;
  return [health, evidence, quality, context];
}

function isBetterClientCard(candidate, existing) {
  const left = clientCardRank(candidate);
  const right = clientCardRank(existing);
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] > right[index];
  }
  return String(candidate?.provider_key || '').localeCompare(String(existing?.provider_key || '')) < 0;
}

function projectClientManifestModel(card) {
  const routeId = String(card?.routing?.cli_route_id || '').trim();
  const capabilities = card?.registry?.capabilities && typeof card.registry.capabilities === 'object'
    ? card.registry.capabilities
    : {};
  const dimensions = card?.benchmarks?.dimensions && typeof card.benchmarks.dimensions === 'object'
    ? card.benchmarks.dimensions
    : {};
  return {
    id: routeId,
    label: String(card?.label || routeId),
    provider: String(card?.provider_key || 'relay'),
    health: {
      state: String(card?.health?.state || 'unverified'),
      observed: card?.health?.observed === true,
      fresh: card?.health?.fresh === true,
      last_checked_at: card?.health?.last_checked_at || null,
      age_seconds: Number.isFinite(card?.health?.age_seconds) ? card.health.age_seconds : null,
      latency_ms: Number.isFinite(card?.health?.latency_ms) ? card.health.latency_ms : null,
    },
    benchmarks: {
      status: String(card?.benchmarks?.status || 'no_data'),
      dimensions: {
        quality: Number.isFinite(dimensions.quality) ? dimensions.quality : null,
        code: Number.isFinite(dimensions.code) ? dimensions.code : null,
        reasoning: Number.isFinite(dimensions.reasoning) ? dimensions.reasoning : null,
        swe: Number.isFinite(dimensions.swe) ? dimensions.swe : null,
      },
      sources: Array.isArray(card?.benchmarks?.sources) ? card.benchmarks.sources : [],
      as_of: card?.benchmarks?.as_of || null,
    },
    context_tokens: Number.isFinite(card?.registry?.context_tokens) ? card.registry.context_tokens : null,
    max_output_tokens: Number.isFinite(card?.registry?.max_output_tokens) ? card.registry.max_output_tokens : null,
    capabilities,
    free: typeof card?.registry?.free === 'boolean' ? card.registry.free : null,
  };
}

function buildClientManifest(projection) {
  const candidates = new Map();
  const cards = Array.isArray(projection?.models) ? projection.models : [];
  for (const card of cards) {
    if (!card?.routing?.cli_visible || card?.routing?.eligible === false) continue;
    const routeId = String(card?.routing?.cli_route_id || '').trim();
    if (!routeId) continue;
    const existing = candidates.get(routeId);
    if (!existing || isBetterClientCard(card, existing)) candidates.set(routeId, card);
  }
  const canonicalCards = [...candidates.values()].sort((left, right) => {
    const leftRank = clientCardRank(left);
    const rightRank = clientCardRank(right);
    for (let index = 0; index < leftRank.length; index += 1) {
      if (leftRank[index] !== rightRank[index]) return rightRank[index] - leftRank[index];
    }
    return String(left?.label || '').localeCompare(String(right?.label || ''));
  });
  const models = canonicalCards.map(projectClientManifestModel);
  const primary = models.find((model) => model.health.state === 'healthy')
    || models.find((model) => model.health.state === 'stale')
    || null;
  const providerCount = new Set(models.map((model) => model.provider)).size;
  return {
    schema_version: 1,
    generated_at: projection?.generated_at || new Date().toISOString(),
    contract: {
      source: 'nexus-model-arena-live-projection',
      relay_base_url: `${modelRelayBaseUrl}/v1`,
      transport: 'openai_chat_completions',
      refresh: 'live_on_request_no_store',
      selection_order: ['observed_health', 'benchmark_evidence', 'quality', 'context'],
      score_policy: 'catalogue_priors_are_not_benchmark_scores',
    },
    summary: {
      ...(projection?.summary || {}),
      canonical_cli_routes: models.length,
      canonical_providers: providerCount,
      observed_healthy_routes: models.filter((model) => model.health.state === 'healthy').length,
    },
    automatic_route: {
      id: 'auto-fastest',
      label: 'NEXUS Auto Fastest',
      contract: 'governed relay selects an eligible live route; it is not a benchmark winner claim',
    },
    recommendation: primary ? {
      id: primary.id,
      label: primary.label,
      provider: primary.provider,
      health: primary.health.state,
      basis: 'best currently observed canonical route under manifest selection_order',
    } : null,
    models,
  };
}

async function buildLiveClientManifest() {
  return buildClientManifest(await buildLiveModelCards());
}

// ── Wiki content API (same-origin; the Next.js /api/wiki sets no CORS) ──
// GET /wiki/api/index          -> file index with frontmatter metadata
// GET /wiki/api/page/<slug>    -> raw markdown

const archivistWikiRoot = path.join(rootDir, 'nexus_os', 'archivist', 'wiki');
const docsRoot = path.join(rootDir, 'docs');
const DOCS_CATEGORIES = [
  'wiki', 'research', 'coordination', 'planning', 'operations',
  'handbook', 'governance', 'hermes', 'grounding',
];
const MAX_INDEX_FILES = 2000;

function parseFrontmatter(content) {
  const meta = { tags: [], confidence: null, priority: null, title: null };
  if (!content.startsWith('---')) return { meta, body: content };
  const end = content.indexOf('\n---', 3);
  if (end === -1) return { meta, body: content };
  const block = content.slice(3, end);
  const body = content.slice(end + 4);
  for (const rawLine of block.split('\n')) {
    const m = rawLine.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!m) continue;
    const [, key, valueRaw] = m;
    const value = valueRaw.trim();
    if (key === 'title') meta.title = value.replace(/^["']|["']$/g, '');
    else if (key === 'confidence') meta.confidence = Number.parseFloat(value) || null;
    else if (key === 'priority') meta.priority = Number.parseFloat(value) || null;
    else if (key === 'tags') {
      const inline = value.match(/^\[(.*)\]$/);
      if (inline) {
        meta.tags = inline[1].split(',').map((t) => t.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      }
    }
  }
  return { meta, body };
}

function describeMarkdown(filePath, slug, category) {
  const stat = fs.statSync(filePath);
  const content = fs.readFileSync(filePath, 'utf-8');
  const { meta, body } = parseFrontmatter(content);
  const headings = [];
  let title = meta.title;
  for (const line of body.split('\n')) {
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      if (!title && h[1] === '#') title = h[2].trim();
      if (h[1] !== '#') headings.push(h[2].trim());
      if (headings.length >= 12) break;
    }
  }
  const excerpt = body
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#') && !l.startsWith('|'))
    .slice(0, 3)
    .join(' ')
    .slice(0, 220);
  return {
    slug,
    title: title || path.basename(filePath, '.md'),
    category,
    updatedAt: stat.mtime.toISOString(),
    size: stat.size,
    headings,
    excerpt,
    frontmatter: { tags: meta.tags, confidence: meta.confidence, priority: meta.priority },
  };
}

function walkMarkdown(dir, onFile) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue; // skip .obsidian and friends
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkMarkdown(full, onFile);
    else if (entry.isFile() && entry.name.endsWith('.md')) onFile(full);
  }
}

function buildWikiIndex() {
  const files = [];
  const push = (filePath, slug, category) => {
    if (files.length >= MAX_INDEX_FILES) return;
    try {
      files.push(describeMarkdown(filePath, slug, category));
    } catch {
      /* unreadable file: skip */
    }
  };

  walkMarkdown(archivistWikiRoot, (filePath) => {
    const rel = path.relative(archivistWikiRoot, filePath).split(path.sep).join('/');
    const sub = rel.includes('/') ? rel.split('/')[0] : 'root';
    push(filePath, `archivist/${rel}`, `archivist/${sub}`);
  });
  for (const cat of DOCS_CATEGORIES) {
    walkMarkdown(path.join(docsRoot, cat), (filePath) => {
      const rel = path.relative(docsRoot, filePath).split(path.sep).join('/');
      push(filePath, `docs/${rel}`, `docs/${cat}`);
    });
  }

  const categories = [...new Set(files.map((f) => f.category))].sort();
  return { files, categories, count: files.length, generatedAt: new Date().toISOString() };
}

function resolveWikiPage(slug) {
  if (slug.includes('..') || slug.includes('\\') || slug.includes('\0') || slug.includes(':')) {
    return null;
  }
  let root;
  let rel;
  if (slug.startsWith('archivist/')) {
    root = archivistWikiRoot;
    rel = slug.slice('archivist/'.length);
  } else if (slug.startsWith('docs/')) {
    root = docsRoot;
    rel = slug.slice('docs/'.length);
    if (!DOCS_CATEGORIES.includes(rel.split('/')[0])) return null;
  } else {
    return null;
  }
  const filePath = path.resolve(root, rel);
  const realRoot = fs.realpathSync.native(root);
  if (!fs.existsSync(filePath)) return null;
  const realFile = fs.realpathSync.native(filePath);
  if (realFile !== realRoot && !realFile.startsWith(`${realRoot}${path.sep}`)) return null;
  if (!realFile.endsWith('.md')) return null;
  return realFile;
}

function handleWikiApi(pathname, res) {
  if (pathname === '/wiki/api/index') {
    sendJson(res, 200, buildWikiIndex());
    return true;
  }
  if (pathname.startsWith('/wiki/api/page/')) {
    const slug = decodeURIComponent(pathname.slice('/wiki/api/page/'.length));
    const filePath = resolveWikiPage(slug);
    if (!filePath) {
      sendJson(res, 404, { error: 'not found' });
      return true;
    }
    const content = fs.readFileSync(filePath, 'utf-8');
    res.writeHead(200, { 'Content-Type': 'text/markdown; charset=utf-8' });
    res.end(content);
    return true;
  }
  return false;
}

function resolveStaticPath(requestUrl) {
  let pathname;

  try {
    pathname = decodeURIComponent(new URL(requestUrl, `http://${host}:${port}`).pathname);
  } catch {
    return null;
  }

  if (pathname.includes('\\') || pathname.includes(':') || pathname.includes('\0')) {
    return null;
  }

  const segments = pathname.split('/').filter(Boolean);
  if (segments.some((segment) => segment === '..')) {
    return null;
  }

  let root = dashboardRoot;
  let relativePath = pathname;

  if (pathname === '/' || pathname === '/dashboard.html') {
    relativePath = '/dashboard.html';
  } else if (pathname === '/wiki' || pathname === '/wiki/') {
    root = wikiRoot;
    relativePath = '/nexus-dashboard.html';
  } else if (pathname.startsWith('/wiki/')) {
    root = wikiRoot;
    relativePath = pathname.slice('/wiki'.length);
  }

  const filePath = path.resolve(root, `.${relativePath}`);
  const realRoot = fs.realpathSync.native(root);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  const realFile = fs.realpathSync.native(filePath);
  if (realFile !== realRoot && !realFile.startsWith(`${realRoot}${path.sep}`)) {
    return null;
  }

  return realFile;
}

const server = http.createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendText(res, 405, 'Method Not Allowed');
    return;
  }

  let apiPathname = null;
  try {
    apiPathname = decodeURIComponent(new URL(req.url || '/', `http://${host}:${port}`).pathname);
  } catch {
    apiPathname = null;
  }
  // Port-plane health shim — probes historically 404'd on /health for 7356.
  if (apiPathname === '/health' || apiPathname === '/api/health') {
    sendJson(res, 200, {
      status: 'ok',
      service: 'static_dashboard',
      port,
      host,
      plane_owner: 'static_dashboard',
      surfaces: [
        '/', '/dashboard.html', '/api/model-cards', '/api/client-manifest',
        '/api/frontier-intelligence', '/wiki/',
      ],
      modelrelay_expected: {
        node: 'http://127.0.0.1:7350/v1',
        python: 'http://127.0.0.1:7355',
      },
      brain_api: 'http://127.0.0.1:7352',
    });
    return;
  }
  if (apiPathname === '/api/model-cards') {
    try {
      sendJson(res, 200, await buildLiveModelCards(), { 'Cache-Control': 'no-store' });
    } catch (err) {
      sendJson(res, 502, {
        error: 'model_card_projection_unavailable',
        detail: String(err && err.message ? err.message : err),
      }, { 'Cache-Control': 'no-store' });
    }
    return;
  }
  if (apiPathname === '/api/client-manifest') {
    try {
      sendJson(res, 200, await buildLiveClientManifest(), { 'Cache-Control': 'no-store' });
    } catch (err) {
      sendJson(res, 502, {
        error: 'client_manifest_unavailable',
        detail: String(err && err.message ? err.message : err),
      }, { 'Cache-Control': 'no-store' });
    }
    return;
  }
  if (apiPathname === '/api/frontier-intelligence') {
    sendJson(res, 200, readFrontierIntelligenceStatus(), { 'Cache-Control': 'no-store' });
    return;
  }

  if (apiPathname && apiPathname.startsWith('/wiki/api/')) {
    try {
      if (handleWikiApi(apiPathname, res)) return;
    } catch (err) {
      sendJson(res, 500, { error: String(err && err.message ? err.message : err) });
      return;
    }
  }

  const filePath = resolveStaticPath(req.url || '/');
  if (!filePath) {
    sendText(res, 404, 'Not Found');
    return;
  }

  fs.stat(filePath, (statError, stat) => {
    if (statError || !stat.isFile()) {
      sendText(res, 404, 'Not Found');
      return;
    }

    const headers = {
      'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream',
      'Content-Length': stat.size,
      'Cache-Control': path.extname(filePath) === '.html' ? 'no-store, max-age=0, must-revalidate' : 'no-cache',
    };

    res.writeHead(200, headers);

    if (req.method === 'HEAD') {
      res.end();
      return;
    }

    fs.createReadStream(filePath).pipe(res);
  });
});

if (require.main === module) {
  server.listen(port, host, () => {
    const baseUrl = `http://${host === '127.0.0.1' ? 'localhost' : host}:${port}`;

    console.log(`NEXUS HTML dashboard active at ${baseUrl}/`);
    console.log(`Quality × Health Matrix: ${baseUrl}/dashboard.html`);
    console.log(`Wiki dashboard: ${baseUrl}/wiki/`);
    console.log('ModelRelay API expected at http://localhost:7350/v1 (Node) | fallback http://localhost:7355 (Python)');
  });
}

module.exports = {
  buildArenaSnapshot,
  buildClientManifest,
  buildLiveClientManifest,
  buildLiveModelCards,
  freshRuntimeSources,
  readFrontierIntelligenceStatus,
  readBoundedRuntimeOverlay,
  readRuntimeRefreshStatus,
  runtimeStateRoot,
  runtimeEntryToSnapshotEntry,
};
