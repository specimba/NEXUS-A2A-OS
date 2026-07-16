# NEXUS SAGE P0 Local Runtime and P1 Preview Proof

**Date:** 2026-07-13
**Scope:** local observe-only SAGE ingress, canonical port ownership, deny-by-default loopback edge, ephemeral public HTTPS preview, private ChatGPT Draft state, HERMES relay reach, generated Action contract, and negative authority probes
**Claim:** local Brain/edge, the private read-only ChatGPT Action Preview, and narrow HERMES reach are live-proven at this proof point. The public URL remains an ephemeral operator preview, the Draft is unpublished/private, proposal writes remain disabled, and no execution authority is claimed.

Evidence labels follow the convergence plan: **TESTED** means a named test passed; **LIVE-PROVEN** means a runtime probe proved the intended surface; **PROVISIONAL** means a preview succeeded without a durable production lifecycle or promotion approval.

## Result

SAGE is live as a separately authenticated Sense/Propose/Witness client on the Brain governance plane. Its loopback edge, ephemeral HTTPS transport, and private GPT-5.6 Thinking Preview preserve the same observe-only authority fence. SAGE is not live on the MCP/GROSS plane and it has no proposal-write or execution authority.

| Surface | Evidence | Status |
|---|---|---|
| Brain / SAGE | `127.0.0.1:7352`, current listener PID `24072`, launcher supervisor PID `92684`, fast Brain identity plus authenticated six-operation verifier | **LIVE-PROVEN** |
| Loopback SAGE edge | `127.0.0.1:17452`, current listener PID `43776`, supervisor PID `18212`, fixed Brain origin, exact six-operation allowlist, bounded global concurrency/rate controls, negative contract tests | **TESTED + LIVE-PROVEN** |
| Public HTTPS preview | Ephemeral ngrok URL to `17452`; complete runtime verifier passed with request inspection disabled | **PROVISIONAL** |
| ChatGPT SAGE | Private GPT-5.6 Thinking Draft; 7,798 UTF-16-code-unit v3 instructions fit the 8,000-character builder limit; Web Search, Canvas, Image Generation, Code Interpreter, and conversation-training use are disabled; all five non-write Actions completed using `Allow once` | **LIVE-PROVEN (PRIVATE PREVIEW)** |
| Builder contract | Builder accepted all six operations without warnings; health, capabilities, grounding, model-cards, and missing-job reads completed; `POST /jobs` was not invoked and remains server-denied | **TESTED + LIVE-PROVEN (PRIVATE PREVIEW)** |
| MCP/GROSS | `127.0.0.1:7354`, `/health` HTTP 200, 25 tools, no SAGE surface | **LIVE-PROVEN** |
| Model Arena evidence | `127.0.0.1:7356/api/model-cards` | **LIVE-PROVEN** |
| HERMES / ModelRelay | Authenticated projection returned `134` models; Leanstral one-shot returned `HERMES_MODELRELAY_OK` with rc `0` | **LIVE-PROVEN** |
| SAGE mode | Authenticated health returned `observe_only` and `execution_allowed=false` | **LIVE-PROVEN** |
| Current port proof | `netstat`, local verifier, and host-pinned public verifier agree on loopback Brain/edge ownership; the historical `nexusctl dashboard --doctor` command is absent from the current parser | **LIVE-PROVEN; HISTORICAL COMMAND STALE** |

The PIDs are proof-point identifiers, not durable service identities. Re-probe after any restart.

## Loopback edge and ephemeral public preview

The restarted local edge bound to `127.0.0.1:17452` and used a fixed upstream of `127.0.0.1:7352`. Its API classifier accepted exactly the six reviewed method/path tuples. It rejected alternate methods, non-allowlisted and encoded/traversal paths, unsafe query shapes, non-JSON POSTs, GET bodies, oversized streamed bodies, ambient proxy/cookie headers, upstream redirects, oversized upstream responses, and non-loopback bind requests. The live process authenticates before admission/body/upstream I/O and returns no-store responses on authenticated/error paths. It runs a global cap of four in flight and 60 authenticated requests per 60 seconds; tested rejection returns bounded `429`/`503` with `Retry-After`, ignores forwarded identity, and recovers without upstream calls. Readiness and privacy are separate explicit documents; they do not create a generic proxy or an extra Brain operation.

The same edge was exposed temporarily through an ephemeral ngrok HTTPS preview with request inspection disabled. The secret-safe verifier completed with:

```text
ok=true
surface=edge
mode=observe_only
operation_count=6
secret_emitted=false
```

That verifier proved Brain-plane health, the Sense/Propose/Witness authority fence, metadata-only grounding, sanitized model cards, the six-operation edge contract, absence of public OpenAPI, invalid-bearer rejection, forbidden-route rejection, and proposal-write denial.

This is **PROVISIONAL**, not production:

- the public URL is ephemeral and may rotate or disappear;
- request inspection was disabled, but a durable deployment, restart/revocation record, and external operational monitor do not yet exist;
- the preview did not authorize proposal writes or execution;
- private ChatGPT Action Preview succeeded, but it does not make the transport durable or suitable for sharing/publication.

## Private ChatGPT Draft and Builder proof

The authenticated Builder surface retains a private `NEXUS SAGE` Draft using GPT-5.6 Thinking. The canonical instructions were compacted from a rejected 8,135-character draft to 7,798 UTF-16 code units and fit the builder limit. Retrieved/tool/knowledge content is explicitly treated as untrusted data; Web Search, Canvas, Image Generation, Code Interpreter, and conversation-training use are disabled; the GPT remains unpublished.

Builder rejected the earlier v1.1 `POST /jobs` request body because it used a discriminated `oneOf`. The regenerated contract replaces only the Action-facing request with an explicit object, documents bounded expiry, retains strict server-side Pydantic models, and now loads with all six operations and no Builder warnings.

Using `Allow once` for every call, private Preview proved:

- health: `service=nexus-sage-ingress`, `mode=observe_only`, `execution_allowed=false`;
- capabilities: proposal writes, arbitrary program execution, raw memory export, and self-approval all `false`;
- grounding: six metadata entries, `content_included=false`, no absolute paths or file bodies;
- model cards: three sanitized cards, no credentials/runtime errors/routing secrets, and catalogue/health/benchmark evidence kept distinct;
- missing job: `not found` with no other job data exposed.

No job was submitted. A generic first health request initially did not select the Action and truthfully returned `not observed`. The persisted instructions were then hardened so current NEXUS state requests cannot substitute Web Search, browsing, uploaded knowledge, or an "import API" analysis. After disabling every optional built-in capability, a fresh plain-language `Check the current NEXUS SAGE health` request selected the registered health Action and capabilities Action without operation IDs, returned `observe_only` and `execution_allowed=false`, and submitted no job. This behavior remains a regression gate rather than a hidden endpoint failure.

## Security review delta

| Finding | Evidence | Status | Remaining gate |
|---|---|---|---|
| Verifier redirects, host, and surface pinning | Redirects are disabled; bearer forwarding across redirects is tested absent; non-loopback HTTPS requires an expected-host pin and must identify as the hardened edge | **TESTED + LIVE-PROVEN** | Re-run after every URL rotation. |
| Edge pre-authentication | The restarted edge authenticates before body read/upstream I/O; invalid-bearer tests prove zero upstream calls | **TESTED + LIVE-PROVEN** | Preserve fixed origin and no-store behavior. |
| Edge abuse controls | Global four-in-flight and 60-per-60-second defaults; bounded strict env parsing; no forwarded-address identity split; `429`/`503` recovery and zero-upstream rejection tests | **TESTED + LIVE-PROVEN PROCESS** | These are private single-operator controls, not OAuth, per-user policy, or distributed production limiting. |
| SAGE 422 redaction | Focused invalid-body tests prove responses expose safe locations/types without caller values | **TESTED** | Extend the public adversarial corpus. |
| Model-card URL origin | Fixed to `127.0.0.1:7356/api/model-cards`; redirects, ambient proxy use, host confusion, and oversized responses are rejected | **TESTED + LIVE-PROVEN** | Preserve outage/staleness semantics. |
| Proposal content DLP | High-confidence credentials, private keys, JWTs, absolute paths, URLs, and code/command markers are rejected before persistence without reflection; bounded NFKC, invisible-character, percent-decoding, and Base64 views close common encoding bypasses | **TESTED** | Homoglyph substitution, nested/encrypted/compressed payloads, and attacker-controlled validation field names remain residual risks. |
| Job retention/recovery | Default 24-hour retention bounded to 1–168 hours; launcher and sweeper share the canonical LocalAppData database; timestamps normalize to UTC and expiry uses SQLite time semantics; the live one-shot returned `state=complete`, `mode=dry_run`, and `applied=false` | **IMPLEMENTED + TESTED; LIVE DRY-RUN** | No schedule is installed; plaintext SQLite/WAL, backup/recovery, operator deletion, encryption, and secure erasure remain gates. |
| Brain bind/WebSocket | CLI and daemon launch loopback by default; non-loopback requires explicit unsafe opt-in; WebSocket auth is header-only and pre-accept | **TESTED + LIVE-PROVEN** | Keep query credentials and anonymous fallback forbidden. |
| Legacy MCP facade | Old broad SAGE `/v1/*` routes are permanently unregistered on MCP/GROSS | **TESTED** | Do not revive. |
| GPT identity/privacy | Static bearer remains one operator service principal; prompt treats retrieved data as untrusted and conversation-training use is off | **PRIVATE-ONLY** | OAuth/per-user identity and durable privacy/hosting controls are required before sharing. |
| Builder least privilege | Prompt length is under the enforced Builder limit; all optional built-in capabilities are off; external calls remain `Allow once` | **LIVE-PROVEN (PRIVATE DRAFT)** | Preserve these UI settings as a manual promotion gate until a supported configuration export/API can attest them. |

The current private Preview used the hardened process image. Transport and Builder success still do not authorize sharing, proposal writes, or execution.

## Live SAGE route contract

The live Brain OpenAPI exposed exactly:

1. `GET /api/sage/v1/health`
2. `GET /api/sage/v1/capabilities`
3. `GET /api/sage/v1/grounding`
4. `GET /api/sage/v1/model-cards`
5. `POST /api/sage/v1/jobs`
6. `GET /api/sage/v1/jobs/{job_id}`

Negative runtime probes:

| Probe | Expected | Observed |
|---|---:|---:|
| Wrong bearer on health | 401 | 401 |
| Valid job proposal while `observe_only` | 403 | 403 |
| `/api/sage/v1/program` | 404 | 404 |
| `/api/sage/v1/memory/task` | 404 | 404 |
| `/api/sage/v1/swarm/dispatch` | 404 | 404 |
| `/api/sage/v1/execute` | 404 | 404 |

The capability projection assigned SAGE `sense`, `propose`, and `witness`; HERMES retained `claim`, `execute`, `retry`, and `close`. It explicitly reported no arbitrary-program execution, raw-memory export, or self-approval.

## Data-minimization proof

- Grounding returned metadata for six allowlisted files with `content_included=false`.
- No absolute user path appeared in the grounding response.
- The restarted verifier accepted a strict typed model-card projection sourced from 236 catalogue offers; the Action may request only its bounded result window.
- The projection reported one observed-healthy offer at the proof point.
- Nested provider/runtime errors, URLs, credentials, routing secrets, and arbitrary fields were absent from the sanitized SAGE response.
- The Model Arena keeps catalogue, CLI visibility, health, benchmark evidence, and policy priors separate.

## Job-store runtime separation

The job store keys its cached handle by the resolved `sage_jobs.sqlite3` path. An explicit `NEXUS_SAGE_RUNTIME_DIR` remains supported; without it, both launcher and sweeper resolve the same LocalAppData runtime path. A stale override falls back only to an existing canonical live database, and a runtime-directory change selects a different store instead of reusing a process-global test or prior-runtime handle.

This is **TESTED** isolation behavior plus a **LIVE DRY-RUN** against the canonical database. Production permissions, backup, recovery, scheduled retention, and governed state-transition evidence remain gates before `proposal_write`.

## Credential containment

- A fresh 96-character service credential was generated without printing its value.
- It is stored outside the repository in an ACL-protected operator state file.
- The stale 7354-era fallback key file was removed without reading it.
- The 7354 starter explicitly sets SAGE mode to disabled and removes inherited SAGE bearer state.
- The 7354 process neither loads the SAGE credential nor registers SAGE routes.

## HERMES → ModelRelay proof

The current `7350 /v1/models` projection returned `134` normalized IDs and contained GLM-5.2, Leanstral, and MiniMax M3. A fresh HERMES request through the `modelrelay` provider reached the relay.

The bounded successful inference proof remains Leanstral:

- model: `labs-leanstral-1-5-1`;
- exact current response marker: `HERMES_SAGE_RELAY_OK`;
- process return code: `0`.

The current bounded `glm-5.2` request did invoke the normalized ID, but ModelRelay selected the Ollama-cloud offer and returned a subscription-required HTTP `403`; HERMES still exited `0`. This is a **LIVE-PROVEN ROUTING/ERROR-CONTRACT DEFECT**, not NVIDIA NIM health evidence. It proves that normalized catalogue visibility is insufficient until provider-offer pinning/selection and typed non-zero CLI failures are fixed. Tool-call parity, streaming, sustained health, NIM 429 recovery, and the OpenCode/KiloCode/Grok four-client matrix remain unproven.

## Generated ChatGPT Actions contract

Artifact: `config/sage/nexus_sage_v1_1_openapi.json`
Exporter: `scripts/export_sage_openapi.py`
Schema SHA-256: `d74548e9ed4c52a50674b99c6c61550102ced67cd47362bbf6f4d95ef393e9cc`

The checked-in server is deliberately `https://sage-gateway.invalid`. Every operation carries Bearer security and `x-nexus-execution-allowed=false`.

The SHA above identifies the current Builder-compatible v1.1 artifact. Exporter checks prove an explicit request object with no `oneOf`, explicit success properties including `expires_at`, and the exact six-operation/auth/observe-only fences. A live-derived copy with only the operator-preview server replaced was Builder-accepted and Preview-tested; the canonical placeholder remains unchanged in source.

## Claim gates run

```text
202 passed in the current coordinator SAGE gate
  ten API, bridge, contract, exporter, launcher, retention, and verifier files

213 passed
  tests/api/test_sage_routes.py
  tests/api/test_sage_jobs.py
  tests/api/test_sage_edge.py
  tests/api/test_sage_brain_mount.py
  tests/nexus_cli_ctl/test_master_daemon.py
  tests/nexus_cli_ctl/test_dashboard_sync.py
  tests/nexus_cli_ctl/test_brain_api_auth.py
  tests/nexus_cli_ctl/test_brain_api_extensions.py
  tests/scripts/test_verify_sage_runtime.py
  tests/scripts/test_start_sage_brain_launcher.py
  tests/scripts/test_export_sage_openapi.py
  tests/tools/test_grok_mcp_server_v2_static.py
  tests/bridge/test_sage_governance.py

11 passed after listener/supervisor identity and orphan-cleanup hardening
5 exporter tests plus exporter --check
```

After the independent P1 audit, Brain and then the abuse-controlled edge were restarted from hardened code. The local Brain, loopback edge, and host-pinned public HTTPS verifiers each returned `ok=true`, `mode=observe_only`, `operation_count=6`, and `secret_emitted=false`; remote verification reported `surface=edge`. Brain listener/supervisor are `24072`/`92684`; edge listener/supervisor are `43776`/`18212`, each tied by process creation identity. The earlier five private GPT read Actions completed end to end with no job submission. These are private-preview claim gates, not durability or publication gates.

The required full suite also ran earlier: `4,405 passed, 67 skipped, 69 failed, 96 errors, 25 warnings` in `307.87s`. It is **not green**. Permission failures in user-profile/vault temporary storage dominated the failure/error list. No whole-system completion claim is made from focused SAGE results.

The current `grounding doctor --json` remains `degraded` because the ledger reports one corrupt line. A fresh changed-only scan produced no result within the bounded observation window and was terminated; the earlier successful `22,794` discovered / `57` ingested / `0` scan-error result is retained as historical evidence, not recast as current. The current CLI parser does not expose the older `nexusctl dashboard --doctor` command, so that historical diagnostic is not cited as fresh evidence.

## Remaining gates

1. Keep the Draft private/unpublished with `observe_only`, `Allow once`, and conversation-training use disabled while the endpoint is ephemeral.
2. Preserve and automate the now-live-proven natural-language Action-selection behavior so future schema/prompt changes cannot regress to Web Search substitution.
3. Run the external prompt/schema-confusion, chunked-body, replay, IDOR, traversal, error-redaction, authorization-redaction, and obfuscated-secret DLP suite.
4. Replace the ephemeral tunnel with a governed, restartable HTTPS deployment or retain it explicitly as development-only with endpoint rotation, revocation, and monitoring.
5. Implement per-user OAuth/identity and remove blanket operator semantics before link/public sharing.
6. Add encryption or an approved storage alternative, scheduled sweeping, operator deletion, backup/recovery, and secure-erasure evidence for proposal data.
7. Keep `POST /jobs` denied; any negative Builder POST test must be independently reviewed and prove `403` plus zero row creation.
8. Extend HERMES beyond the Leanstral one-shot: GLM-5.2 invocation, tool calls, structured output, streaming, typed NIM 429 cooldown/fallback, and four-client parity.
9. Run the full suite in a permission-correct user-profile/vault temp environment before a whole-system completion claim.
10. Repair or quarantine the single corrupt grounding-ledger line through the governed grounding recovery workflow.
11. Re-run port/listener, local verifier, public verifier, Builder schema, and five-read Preview gates after every restart or URL rotation.
12. Use `docs/operations/NEXUS_SAGE_PRIVATE_PREVIEW_RUNBOOK_2026-07-13.md` for rotation, startup, verification, rollback, and secret-safe evidence logging.

This report claims a private P1 read-only GPT Preview plus provisional public-edge transport. It does not claim durable public deployment, sharing/publication, proposal-write authority, P2 execution, or completion of the wider ModelRelay/HERMES/A2A program.
