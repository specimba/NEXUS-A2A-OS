# NEXUS governed ModelRelay runtime

This package pins `modelrelay` 1.18.0 and applies a reviewed NEXUS patch during
`npm ci`. It is the repo-owned replacement for an unpinned global installation.

Safety defaults:

- provider catalogue refreshes do not fan out chat/completion probes;
- a persisted provider-aware canary samples at most one offer every 150 seconds,
  at most 24 per hour, with 30-minute provider rotation and a 60-minute NVIDIA
  cooldown; it chooses one provider sentinel rather than fanning out over the
  catalogue;
- the health-sampler API exposes the non-secret sampler budget and last outcome;
- exact provider-model health observations from canaries and real client traffic
  survive process restarts, and live rows hydrate only when persisted evidence
  is newer;
- exact-offer 429 cooldown deadlines survive restarts without disabling sibling
  models at the same provider;
- manual health probes require an exact provider key when a model ID is
  ambiguous;
- the dashboard distinguishes fresh, stale, unverified, rate-limited, and
  unavailable offers and keys duplicate IDs by provider;
- unknown benchmark quality remains null instead of receiving a synthetic 45%;
- Mistral and NVIDIA work is serialized, and NVIDIA starts are paced to 8 RPM;
- a 429 cools the affected account, connection, model, or exact offer rather
  than disabling every model at that provider; NVIDIA cooldown is at least 75s
  and honors a longer `Retry-After`;
- a bare canonical model ID routes over its full logical offer group, while a
  provider-qualified ID remains exact;
- `nexus-resilient` is an explicit opt-in virtual alias, visible in `/v1/models`
  after a controlled relay restart. It prefers fresh (15-minute), exact
  observed-healthy offers, then uses bounded warm exact-success evidence (up
  to 48 hours) only when no fresher fitting route exists. It checks the live
  provider/offer governor, honours advertised context capacity for long agent
  sessions, excludes GLM-5.2 so the primary lock remains intact, and returns
  the standard typed 503 with zero upstream calls when no eligible route exists;
- first-byte deadlines abort and quarantine only the active offer; caller abort
  and the total request deadline still stop the whole request;
- exact health evidence selects a 6-30 second per-offer first-byte deadline;
  NVIDIA has a context-aware 12-25 second floor so a successful short probe
  cannot make a 100k-token Hermes session fail at six seconds. A 25-second
  request-level route budget still prevents sequential offers from multiplying
  CLI stalls;
- exhausted safe-runtime routes return a sanitized, two-call attempt receipt
  with `NEXUS_NO_HEALTHY_MODEL_OFFER`;
- transient provider 5xx/timeouts move through `DEGRADED` to `OPEN`;
- routing makes at most two upstream calls total, including auth fallback;
- Leanstral aliases and GLM-5.2 context metadata are canonicalized before UI/API projection;
- automatic package updates are disabled;
- the admin API is loopback-only;
- remote `/v1/*` access requires `MODELRELAY_BEARER_TOKEN`;
- CORS is an explicit allowlist.

Verification and shadow launch:

```powershell
npm ci
npm run patch:apply-reviewed
npm test
npm run verify
npm run verify:shadow-failover
npm run shadow
```


The checked `patches/modelrelay+1.18.0.patch` payload is the reproducible source
of truth. `patch:apply-reviewed` uses the same `patch-package` path as
`npm ci`, then verifies the pinned integrity and every governed marker.
`npm run shadow` uses port 17350 and the secret-free fixture config. It does not
modify or restart the production relay on port 7350.

`verify:shadow-failover` uses two loopback-only ephemeral upstreams to prove
that a first-byte timeout rotates to a distinct healthy offer within one relay
request. It writes only an ephemeral config with a runtime-generated token.
OmniRoute is not installed or placed in the serving path. Its provider source
may be inspected only through the opt-in, local-snapshot frontier-intelligence
adapter, which emits quarantined source-card candidates and never edits the
registry:

```powershell
py -3.13 -m tools.frontier_scanner.orchestrator omniroute-intel --source-root <pinned-clone> --expected-version <exact-version> --expected-commit <40-char-commit> --enable-omniroute-intel --emit-json <candidate-bundle.json>
```

## Opt-in resilient fallback alias

`nexus-resilient` is not an alias for `auto-fastest`, and no client is changed
to use it. A client may choose it explicitly only where a fallback model is
appropriate. The lane is deliberately conservative:

- it uses only the existing, fixed provider families `ollama-cloud`, Mistral,
  OpenCode, KiloCode, OpenRouter, and NVIDIA; it never discovers or registers a
  provider or model;
- an exact provider-model offer must be `up`, have a latest successful 2xx
  observation within the 15-minute fresh window or 48-hour warm window, fit a
  long request's advertised context capacity, and pass the current provider,
  rate-limit, offer-circuit, and access-hold governor checks;
- pending, unverified, 401/402/403-held, 429-cooled, deterministic canary
  incompatibilities, retired routes, failed, and malformed observations are
  excluded instead of being guessed from scores;
- fresh candidates rank above bounded warm candidates and are provider-
  diversified before the relay's two-call limit. Intelligence or benchmark
  scores are not used to manufacture capability claims; and
- all GLM-5.2 route spellings are excluded so a `glm-5.2` primary lock remains
  wholly separate. If no eligible fallback exists, the alias fails closed with
  `NEXUS_NO_HEALTHY_MODEL_OFFER` and no provider request.

The lane becomes usable only after a controlled restart of port 7350. Its
catalogue advertisement does not mean that a healthy fallback exists at that
moment; inspect the health sampler and Model Arena before electing it in a
client configuration.
