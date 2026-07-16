# NEXUS SOL Ultimate + SAGE Whole-System Convergence Plan

**Date:** 2026-07-13
**Status:** Execution-grade convergence plan with dated proof-point evidence; not a completion claim
**Authority:** `NEXUS_MANIFEST.md`, `AGENTS.md`, `01_PROJECT_STATE.md`, vision manifest §11, port ownership rules, current source, and focused tests
**Scope:** SAGE, HERMES, NexusClaw, A2A/Agent Client Protocol boundaries, ModelRelay, model stack, CLI reach, trust, memory, benches, and operator evidence

## 1. Decision

SAGE is a first-class NEXUS reasoning organ, not an appendix and not a second executor.

The durable division of responsibility is:

| Organ | Lifecycle | Authority boundary |
|---|---|---|
| **SAGE** | **Sense → Propose → Witness** | May read bounded evidence, formulate governed proposals, and report receipts/results. It may not approve itself, claim work, execute arbitrary programs, or mutate NEXUS directly. |
| **HERMES** | **Claim → Execute → Retry → Close** | Claims approved work, selects an allowed execution lane, performs bounded retries, writes execution evidence, and closes or escalates the task. |
| **Governor / KAIJU / TrustKernel** | **Authenticate → Evaluate → Authorize/Deny → Audit** | Sits between every northbound request and any effectful action. No model is its own authority. |
| **NexusClaw** | **Envelope → Queue → Delegate → Reconcile** | Owns durable orchestration and proposal-to-task conversion after governance approval. |
| **ModelRelay** | **Discover → Normalize → Score evidence → Route → Recover** | Supplies models to execution clients. It does not turn catalogue presence into health or benchmark proof. |

The first production loop is therefore:

```text
operator in SAGE
  → public HTTPS allowlist
  → Brain API :7352 /api/sage/v1/*
  → SAGE auth + byte limit + strict schema
  → Trust/KAIJU + proposal envelope
  → durable pending_review receipt
  → operator/governor approval
  → HERMES claim
  → ModelRelay-selected worker and/or signed A2A execution :8000
  → execution evidence + VAP receipt
  → SAGE witness response
```

This plan rejects three tempting but unsafe shortcuts:

1. SAGE routes on the GROSS/MCP bridge at `7354`.
2. Raw code, shell, memory dumps, secrets, or unrestricted filesystem access in a Custom GPT Action.
3. Treating “GPT-5.6 Sol Ultra” as an invented relay model slug. **Sol is the model family; Ultra is an orchestration/product profile.** ModelRelay must use only IDs advertised by an authenticated provider catalogue. It must never invent `gpt-5.6-sol-ultra`.

## 2. Evidence rubric

Every status in this document uses one of five meanings:

| Label | Required evidence |
|---|---|
| **IMPLEMENTED** | Current source contains the behavior and imports/compiles. |
| **TESTED** | A named test exercises the behavior in this checkout and passes. |
| **LIVE-PROVEN** | The intended owner process is running on the reserved port and an authenticated runtime probe proves the behavior. |
| **PROVISIONAL** | A preview or operator-surface proof succeeded, but its endpoint, configuration, or lifecycle is not durable or production-approved. |
| **PLANNED** | Required work is sequenced here but not yet proven. |

Source presence or a unit test is not live proof. A port listener is not ownership proof. A provider catalogue entry is not health proof. A model name is not benchmark evidence.

## 3. Verified current state and remaining truth gaps

### 3.1 SAGE northbound boundary

| Capability | Current evidence | Status | Remaining gate |
|---|---|---|---|
| Dedicated Brain API router at `/api/sage/v1` | Current listener is `127.0.0.1:7352` under PID `24072`, owned by launcher supervisor PID `92684`; the hardened launcher and complete verifier passed after a clean restart | **LIVE-PROVEN** | Treat both PIDs as proof-point identities only; preserve the controlled launcher/restart path and re-probe after every deploy. |
| Six-operation allowlist | Live OpenAPI: four observation GETs, proposal POST, and job-status GET only | **LIVE-PROVEN** | Keep the generated contract drift gate mandatory. |
| Fail-closed bearer authentication | Rotated 96-character operator key in owner-only state; constant-time comparison; wrong bearer returned `401`; private Preview health and capabilities succeeded with the rotated credential | **LIVE-PROVEN** | Keep the rotation runbook mandatory; replace the shared service principal with per-user OAuth before any sharing. |
| Bounded request bodies | Prefix-specific ASGI byte-count middleware; default maximum 90,000 bytes | **IMPLEMENTED + TESTED** | Verify proxy and application limits agree; test chunked requests live. |
| Read-only default | Live `NEXUS_SAGE_GATEWAY_MODE=observe_only`; valid proposal POST returned `403` | **LIVE-PROVEN** | Do not promote during initial Custom GPT wiring. |
| Strict proposal schemas and persistence DLP | Discriminated allowlisted workflows, extra fields forbidden, and high-confidence checks reject raw and common encoded credentials, private keys, JWTs, paths, URLs, and executable markers without value reflection | **IMPLEMENTED + TESTED** | Homoglyph, nested, encrypted, compressed, and novel payloads remain; keep proposal writes disabled pending external adversarial review. |
| Durable proposal receipt | SQLite-backed `pending_review` receipt, atomic idempotency, normalized UTC expiry, and `expires_at`; retention defaults to 24 hours and is bounded to 1–168; scheduler-safe sweeping is dry-run by default and explicit-apply only. The 2026-07-13 live dry-run reached the canonical database and returned `state=complete`, `applied=false` | **IMPLEMENTED + TESTED; LIVE DRY-RUN** | Install no schedule until reviewed; add encryption, backup/recovery, operator deletion/secure-erasure policy, and a governed state-transition worker before promotion. |
| Runtime-separated job store | `NEXUS_SAGE_RUNTIME_DIR` selects an explicit database; without an override, launcher and sweeper resolve the same LocalAppData path. Tests cover stale overrides and timestamp-equivalent expiry comparisons | **TESTED + LIVE-PROVEN** | Sweeping remains operator-triggered; plaintext SQLite/WAL forensic erasure and backup controls remain open gates. |
| Grounding exposure | Live metadata/hash manifest: six allowlisted files, no bodies, no absolute paths | **LIVE-PROVEN** | Review the allowlist before every public schema revision. |
| Model-card exposure | A strict recursive projection now reconstructs only typed allowlisted summary, routing, health, benchmark, policy-prior, and registry fields. Current in-process and restarted Brain/edge/public verifiers passed against the 236-offer Arena projection; nested provider errors, credentials, URLs, routing secrets, and arbitrary keys were absent | **TESTED + LIVE-PROVEN** | Catalogue presence still does not prove exact-offer health; benchmark provenance is structurally validated, not cryptographically attested. Add outage, staleness, and signed-provenance acceptance tests. |
| Loopback SAGE edge | Current listener is `127.0.0.1:17452` under PID `43776` with supervisor PID `18212`, forwarding the exact six operations to fixed Brain origin. The restarted process runs a global four-request concurrency cap and 60-request/60-second rate limit | **TESTED + LIVE-PROVEN** | Preserve the explicit readiness/privacy documents and never bind this edge beyond loopback. |
| Public HTTPS preview | An ephemeral ngrok URL to the `17452` edge passed the complete secret-safe runtime verifier with `surface=edge`, `mode=observe_only`, and `operation_count=6`; ngrok request inspection was disabled | **PROVISIONAL** | The URL is ephemeral and is not a production endpoint. Require a durable deployment record, rotation/restart runbook, external re-probe, and promotion review. |
| ChatGPT SAGE Draft | Private GPT-5.6 Thinking Draft retained hardened v3 instructions, treats retrieved/tool content as untrusted, has conversation-training use disabled, and completed all five non-write Preview operations with `Allow once` | **LIVE-PROVEN (PRIVATE PREVIEW)** | Do not publish or link-share; shared use requires per-user identity and a durable reviewed endpoint. |
| Builder Action schema | Builder accepted the regenerated six-operation schema with no warnings; health, capabilities, grounding, model-cards, and missing-job calls completed end to end. Canonical artifact SHA-256 is `d74548e9ed4c52a50674b99c6c61550102ced67cd47362bbf6f4d95ef393e9cc` | **TESTED + LIVE-PROVEN (PRIVATE PREVIEW)** | Keep strict server-side Pydantic validation; do not treat Builder acceptance as publication or proposal authority. |

Latest coordinator verification on 2026-07-13:

```text
py -3.13 -m pytest -q <ten focused SAGE API/bridge/contract/script files>
202 passed, 2 environment warnings

ruff check <scoped SAGE Python files>
All checks passed

py -3.13 scripts\export_sage_openapi.py --check
SAGE OpenAPI contract is current

PowerShell parser: scripts\start_sage_brain.ps1
OK
```

The earlier broader SAGE/Brain/edge/daemon/dashboard/exporter/verifier/legacy-facade gate passed `213` tests. After the independent P1 audit and edge abuse-control slice, the coordinator reran the current ten-file SAGE slice: `202 passed`. The focused retention, launcher, recursive model-card, and edge slices separately reported `18`, `11`, `122`, and `100` passing tests before the combined gate.

The required full suite was not green: `4,405 passed, 67 skipped, 69 failed, 96 errors`; permission failures in user-profile/vault temporary storage dominated the reported failures/errors. Runtime proof on 2026-07-13 established:

- `7352` and `17452` bound only to `127.0.0.1`; Brain listener PID `24072` was tied to supervisor PID `92684` by process identity/creation time, and the launcher now reports listener and supervisor separately;
- authenticated SAGE health reported `observe_only`, `execution_allowed=false`, and `port_owner=7352`;
- the local Brain, loopback edge, and host-pinned public edge verifiers each passed the exact six-operation contract;
- wrong bearer returned `401`, a valid proposal POST returned `403`, and program/memory/swarm/execute paths returned `404`;
- the private GPT Action completed health, capabilities, grounding, model-cards, and missing-job reads using `Allow once`; no job was submitted;
- Preview proved `proposal_writes_enabled=false`, `arbitrary_program_execution=false`, `raw_memory_export=false`, and `self_approval=false`;
- grounding returned metadata only, and model cards kept catalogue, health, and benchmark evidence distinct without secret-bearing runtime errors;
- the current `nexusctl` parser does not expose the older `dashboard --doctor` command, so that historical diagnostic is now **STALE** rather than reused as current proof.

This proves the **local observe-only milestone** and the **private read-only GPT Preview milestone**. The public transport remains **PROVISIONAL** because its tunnel is ephemeral and operator-scoped; no proposal write, sharing, public-production lifecycle, or execution authority is authorized.

### 3.2 Security review delta

| Finding | Current evidence | Status | Remaining gate |
|---|---|---|---|
| Runtime verifier redirect/host/surface pin | Redirect following is disabled, bearer forwarding across redirects is tested absent, non-loopback verification requires an expected-host pin, and a remote Brain surface is rejected unless it is the hardened edge | **TESTED + LIVE-PROVEN** | Re-run after every public URL rotation. |
| Edge pre-authentication | The loopback edge authenticates before body read/upstream I/O; repeated invalid-bearer tests prove zero upstream calls and the restarted edge passed local/public verifiers | **TESTED + LIVE-PROVEN** | Preserve no-store responses and fixed origin. |
| Edge abuse controls | Authenticated operations share a process-global cap of four in flight and 60 requests per 60 seconds; strict bounded env parsing, non-blocking `429`/`503`, `Retry-After`, no-store errors, recovery, and no `X-Forwarded-For` identity split are tested. The restarted edge and host-pinned public verifier pass | **TESTED + LIVE-PROVEN PROCESS** | This is single-operator containment, not per-user identity or distributed rate limiting; OAuth and durable edge-level controls remain required before sharing. |
| SAGE 422 redaction | Focused invalid-body tests prove SAGE responses expose only safe locations/types and never caller input | **TESTED** | Extend the external adversarial corpus before promotion. |
| Model-card origin and projection boundary | Source is fixed to `http://127.0.0.1:7356/api/model-cards`; redirects, ambient proxies, host confusion, and oversized responses are rejected. A second exact-key/type/range verifier independently validates every nested public field | **TESTED + LIVE-PROVEN** | Preserve the canonical origin and outage semantics; add signed/fresh provenance rather than trusting structurally valid source IDs as attestation. |
| Proposal content DLP | High-confidence secrets, paths, URLs, and code/command markers are rejected before persistence without reflection; bounded NFKC, invisible-character removal, percent-decoding, and Base64 semantic views close common encoding bypasses | **TESTED** | Homoglyph substitution, nested/encrypted/compressed payloads, and validation-field-name reflection remain; keep writes disabled pending external adversarial evaluation. |
| Job retention and recovery | Job/idempotency rows use normalized UTC timestamps; expiry comparisons use SQLite time semantics rather than lexical text ordering. The default sweeper resolves the launcher's canonical database and a live read-only run completed without deletion | **IMPLEMENTED + TESTED; LIVE DRY-RUN** | Operator scheduling is not installed; plaintext SQLite/WAL, backup/recovery, deletion, encryption, and forensic erasure remain hard gates. |
| Brain bind and WebSocket auth | Direct CLI and daemon launches default to loopback; non-loopback requires exact unsafe opt-in; `/ws` authenticates before accept using header credentials only | **TESTED + LIVE-PROVEN** | Keep query credentials forbidden and re-probe after every launcher change. |
| Legacy SAGE facade | MCP/GROSS never registers the old broad `/v1/*` SAGE routes, regardless of proposal-write configuration | **TESTED** | Do not revive the facade. |
| Private GPT prompt/privacy | The 7,763-character prompt saves below Builder's 8,000-character limit; retrieved/tool/knowledge content is untrusted; Web Search, Canvas, Image Generation, Code Interpreter, and conversation-training use are disabled; plain-language health selected the bounded Actions; external calls used `Allow once` | **LIVE-PROVEN (PRIVATE DRAFT)** | Preserve prompt length, natural-language routing, and least-privilege UI settings as regression gates; public/link sharing remains prohibited until OAuth/per-user identity, durable privacy terms, and reviewed hosting exist. |

These findings prevent the preview result from being promoted by transport success alone.

### 3.3 Port ownership and effect boundary

| Port | Canonical owner | SAGE relationship | Non-negotiable acceptance |
|---:|---|---|---|
| `7350` | Node/npm ModelRelay primary | HERMES and CLIs discover/select models here | OpenAI-compatible catalogue and inference; provider/health evidence must be truthful. |
| `7352` | Brain API / NEXUS governance | **Only SAGE ingress owner** under `/api/sage/v1/*` | Correct process identity, separate SAGE bearer auth, Trust/KAIJU path, no relay/static/MCP content. |
| `7354` | GROSS/MCP read-only bridge | No SAGE facade, no SAGE key, no SAGE writes | Read-only MCP/GROSS surface; current 25-tool contract; SAGE paths absent or rejected. |
| `7355` | Python ModelRelay fallback/internal | Recovery lane selected by HERMES/relay policy, not called directly by SAGE | Internal fallback health and bounded parity with primary. |
| `7356` | Static Model Arena viewer | Canonical sanitized model-card projection consumed through Brain | Viewer/evidence API only; never an executor or provider authority. |
| `8000` | Governed A2A execution bridge | Downstream only after approval and HERMES claim | Signed task execution, replay protection, trust gate, evidence receipt. |

`7354` was restarted from hardened source on 2026-07-13. Live `/health` remained HTTP `200` with the 25-tool contract on `127.0.0.1`; `/v1/health`, `/v1/program`, `/v1/memory/task`, and `/privacy` all returned `404`. The inherited SAGE credential was stripped at startup, route registration was suppressed on `7354`, and the stale fallback credential file was removed without reading it.

### 3.4 HERMES → ModelRelay reach

The live 2026-07-13 HERMES proof point corrected the earlier zero-model picker failure:

| Probe | Evidence | Status | Remaining gate |
|---|---|---|---|
| ModelRelay discovery | Current `7350 /v1/models` returned `134` normalized IDs including `glm-5.2`, Leanstral, and MiniMax M3; HERMES can invoke the `modelrelay` provider | **LIVE-PROVEN** | Provider offers remain collapsed behind normalized IDs; reconcile selection with the 236-offer evidence projection. |
| Frontier/current identities | The authenticated HERMES projection included GLM-5.2 and Leanstral identities | **LIVE-PROVEN** | Preserve provider-offer identity and health separately; catalogue visibility is not benchmark or sustained-health proof. |
| Minimal inference | A fresh HERMES one-shot through `modelrelay` and Leanstral returned exact marker `HERMES_SAGE_RELAY_OK` with process return code `0` | **LIVE-PROVEN** | Tool-call compatibility, structured output, streaming, sustained reliability, and multi-CLI parity remain unproven. |
| GLM-5.2 route/error contract | A bounded HERMES request for normalized `glm-5.2` selected the Ollama-cloud offer and returned a subscription-required HTTP `403`, while the HERMES process still exited `0` | **LIVE-PROVEN DEFECT** | Add offer-aware routing/pinning so NVIDIA/Baseten/Ollama identities do not collapse into the wrong commercial route, and make HERMES return non-zero/typed failure for provider HTTP errors. Do not classify this as NIM health or retry it blindly. |

This satisfies the narrow non-zero-picker/minimal-request proof. It also disproves the stronger GLM-5.2 reach claim: catalogue visibility exists, but duplicate-offer selection and CLI exit semantics are not correct. The result does not complete the broader HERMES, NVIDIA NIM, provider-rotation, or four-client reach matrix.

### 3.5 Memory and audit mapping

SAGE does not receive an unrestricted memory API. It receives bounded projections and writes proposals/receipts through governed services.

Legacy S-P-E-W terms are conceptual routing aids, not a reason to replace the canonical eight-channel memory:

| Legacy concept | Canonical eight-channel destination | SAGE rule |
|---|---|---|
| Session | `WORKING`, `TASK` | Store request IDs, bounded task context, idempotency key hash, and expiry—not chat dumps. |
| Project | `SEMANTIC`, `PROCEDURAL` | Expose approved source cards, capability contracts, and runbooks by digest/reference. |
| Experience | `EPISODIC`, `TRUST` | Record proposal, decision, execution receipt, failure class, and trust delta. |
| Wisdom | `META`, `SEMANTIC` | Promote only reviewed lessons and benchmark conclusions with provenance. |
| Raw input | `SENSORY` | Quarantine, classify, and redact before any promotion. |

KAIJU must validate identity, capability, data scope, privilege monotonicity, and required approval at the SAGE → proposal and HERMES → execution boundaries. VAP/append-only audit records are the witness authority; SAGE summaries are not the source of truth.

### 3.6 Latest multi-agent log reconciliation

The full stored content of `NEXUSantiGRAVnexlog-12.txt`, `NEXUSgeneralFABLE5advisorylogs-04.txt`, and Kilo orchestration logs `06`/`07` was read under GND-001 and reconciled in `docs/reviews/NEXUS_SAGE_GND001_RECONCILIATION_2026-07-13.md`.

The logs establish priority and design lineage, not current SAGE proof. antiGRAV ends at the operator's SAGE request; later Kilo “live” summaries do not reproduce route evidence. FABLE's relay overlay was test-gated but explicitly not cut over at that checkpoint. Historical A2A closure summaries likewise do not replace one Brain-governed artifact cycle plus a proofless denial. Current source, focused tests, listener identity, and authenticated live probes are authoritative for the SAGE status in this plan.

### 3.7 Dated SAGE advisory and handoff delta - 2026-07-13

| Boundary | Status at this checkpoint | What this does **not** prove |
|---|---|---|
| Root-supplied FABLE advisory receipt | **IMPLEMENTED + TESTED (LOCAL ONLY):** `nexus_os/bridge/fable_advisor.py` accepts only the root actor, bounds and terminal-sanitizes input, redacts credentials/verdict markers, binds an input digest, and emits `proposal_only=true`, `execution_allowed=false`, `approval_state=pending`, and `governor_required=true`. `tests/bridge/test_fable_advisor.py` exercises the root-only, redaction, no-invocation, and input-boundary contracts. | It is not a FABLE provider integration, a SAGE Action, a tool call, an approval, a job creation, a NexusClaw dispatch, or a live/public claim. `EXTERNAL_FABLE_INVOCATION_ENABLED` remains false. |
| SAGE -> NexusClaw handoff | **IMPLEMENTED + TESTED (LOCAL CONTRACT ONLY):** `nexus_os/bridge/sage_governance.py` accepts only a canonical SAGE principal/job/workflow, binds the pending-review receipt to the canonical proposal and parameter digests, validates the dry-run `NexusClawTaskEnvelope`, and returns `proposal_only=true` plus `execution_allowed=false`. `tests/bridge/test_sage_governance.py` covers a valid receipt-bound handoff and tampered/non-pending rejection; the current focused FABLE/SAGE/API bundle is green. | It does not authorize `proposal_write`, queueing, HERMES claiming, A2A execution, sharing, publication, a service cutover, or a live task. The adapter is not wired to an Action route or live dispatcher; P1 still requires fresh claim-gate proof. |
| External/public SAGE surface | **PRIVATE/PROVISIONAL ONLY:** the local observe-only and private Preview evidence above remain the authoritative scope. | An ephemeral preview, builder acceptance, or an advisory receipt does not establish durable hosting, per-user identity, public sharing, or production readiness. |

Ordered next sequence - no publication, share-link enablement, live dispatch, or port cutover is authorized by this delta:

1. Keep the FABLE boundary root-supplied and disabled for external invocation; re-run `tests/bridge/test_fable_advisor.py` whenever the receipt schema, sanitizer, or SAGE instructions change.
2. Re-run and independently review the SAGE -> NexusClaw fixture/dry-run handoff contract: canonical envelope, receipt/proposal digest binding, `pending_review`, tamper rejection, and zero execution/queue side effect.
3. Reconcile the resulting receipt fields with Governor/KAIJU, VAP, and the existing SAGE job projection; retain `observe_only` and make any missing evidence a denial rather than a retry loop.
4. Only after the P0/P1 gates below are fresh and green may the separate P2 proposal-write review be considered. P2 authorization, HERMES claiming, A2A execution, durable external hosting, and public release each retain their own explicit approval gates.

## 4. Target architecture

### 4.1 SAGE as the northbound reasoning client

SAGE is the operator-facing GPT project with NEXUS instructions and bounded Actions. The current private Draft uses GPT-5.6 Thinking. The separately advertised Sol API family remains provider-catalogue data, while “Ultra” describes the high-orchestration operating profile—multi-pass decomposition, critic/reviewer roles, and tool coordination—not a new provider model identifier.

SAGE may:

- sense health, capability, grounding-manifest, model-card, and its own job-status projections;
- propose an allowlisted workflow with bounded parameters and an idempotency key;
- witness receipts, denials, pending-review state, execution evidence, and final closure;
- ask the operator for an approval that NEXUS says is required.

SAGE may not:

- call shell, Python, raw program, generic HTTP fetch, arbitrary URL, filesystem, Git mutation, or provider-secret operations;
- read raw 8-channel memory, private ARCHIVIST dumps, prompts, environment variables, provider errors, or absolute paths;
- approve, claim, retry, close, promote, fine-tune, delete, or publish;
- bypass HERMES, Governor, KAIJU, NexusClaw, or the signed execution bridge;
- choose a model solely from a self-reported model name or unverified score.

### 4.2 HERMES as the effectful lifecycle owner

HERMES consumes an approved NexusClaw task envelope, not free-form SAGE prose. It must:

1. claim with an atomic lease;
2. resolve the required capability profile;
3. query ModelRelay for eligible, healthy, policy-allowed candidates;
4. execute through the correct local, cloud, MCP, CLI, or signed-A2A adapter;
5. retry only retriable classes with a bounded budget and jitter;
6. checkpoint evidence after every attempt;
7. close with a verifiable artifact or escalate with a precise blocker.

HERMES model-picker reach is accepted only when its `modelrelay` provider returns the canonical `7350 /v1/models` catalogue and can complete a minimal request. A menu row showing `0 models` is a failed integration even if the relay is healthy elsewhere.

### 4.3 Protocol edges

| Edge | Protocol | Purpose | Explicit exclusion |
|---|---|---|---|
| Agent ↔ agent / organization boundary | **A2A v1** | Agent Card discovery, task lifecycle, artifacts, status, signed delegation | Not an IDE transport and not a substitute for KAIJU authorization. |
| IDE/editor ↔ coding agent | **Agent Client Protocol** | Session, prompt, tool, plan, and editor interaction for OpenCode/HERMES-style clients | Not the IBM Agent Communication Protocol; do not conflate it with the A2A agent edge. |
| Model client ↔ provider | OpenAI-compatible ModelRelay API | `/v1/models` and inference normalization | Not an A2A task bus. |
| Tool client ↔ governed tool | MCP/GROSS | Bounded tool discovery and invocation | `7354` remains read-only; effectful tasks go through governance. |
| Browser lane ↔ local controller | CDP/MCP adapter | Observable, bounded browser collaboration | No hidden navigation, credential extraction, or ungoverned keepalive. |

A2A v1 becomes the external agent interoperability contract. Agent Client Protocol becomes an optional IDE adapter feeding the same governed proposal/task core. Neither protocol owns execution policy; both terminate at the Bridge and pass through Governor/KAIJU.

### 4.4 Model stack

NEXUS is a governed multi-model OS, not a frontier-base-model training project. The model stack is capability-tiered:

| Tier | Examples / source | Intended role | Gate |
|---|---|---|---|
| Operator reasoning surface | Private SAGE Draft on GPT-5.6 Thinking; Sol API family only where provider-advertised; Ultra orchestration profile | Sense, propose, synthesize, witness | External request-response only; no self-approval or direct execution. |
| Frontier coordinators and reviewers | Fable5, Grok/xAI, provider-advertised GPT/Claude-class lanes | Architecture, critique, difficult synthesis, red/blue review | Provenance, operator-paid trace policy, cost/egress gate, no invented availability. |
| Cloud execution candidates | NVIDIA NIM, InternAI, LongCat, Mistral/Leanstral, OpenCode/KiloCode partner lanes, other verified providers | Coding, tool use, science, long context, fallback diversity | Live catalogue + authenticated health + capability evidence + license/ToS record. |
| Local 8 GB organs | Guard/router/classifier/detector SLMs and bounded local workers | Safety fast path, privacy, classification, verifier and low-cost work | Hard 8 GB ceiling; no architecture rewrite or oversized local crown. |
| Training benches | Intern A800 and approved durable benches | TokenHD and other governed organs; evaluation and distillation | A800 quota hard rule, one live kernel, durable artifact proof, F-2 promotion gate. |
| Image lane | Modal and approved image services | Image-only generation/processing | Never silently used as a general text/model relay. |

The relay stores provider offers and model identities separately. One normalized model may have multiple offers with different limits, cost, health, tool support, and rate windows.

### 4.5 ModelRelay truth model

The Model Arena and router must maintain separate fields for:

1. **Catalogue presence** — the provider or CLI advertised the model.
2. **CLI visibility** — HERMES/OpenCode/KiloCode can see the normalized model ID.
3. **Authentication state** — credentials are configured, missing, expired, or quarantined; never returned to clients.
4. **Health** — `healthy`, `degraded`, `cooldown`, `unverified`, or `offline`, with probe time and latency.
5. **Capability** — chat, reasoning, code, tools, structured output, vision, context, streaming, and provider quirks.
6. **Benchmark evidence** — benchmark name/version, score, evaluator, date, source, comparability class, and confidence.
7. **Policy prior** — cost, license/ToS, privacy, rate tier, region, and operator preference; never mislabelled as intelligence evidence.

There is no universal default `45%`. Models without compatible evidence remain **UNSCORED** while staying discoverable. Rankings expose per-domain evidence (for example SWE-bench family, terminal/coding, tool-use, scientific reasoning, long-context, safety, and human-preference evidence) instead of manufacturing one precise number from architecture reputation.

NVIDIA NIM and other rate-limited providers require a shared state machine:

```text
healthy → soft_limit → cooldown → half_open → healthy
                           ↘ auth_or_quota_exhausted → disabled_until_operator_action
```

Requirements: honor `Retry-After`, cap concurrency per provider/key/model, add jitter, distinguish 429 quota from 429 burst limits, prevent recursive retry/subagent spawning, persist cooldown, route only to capability-compatible fallbacks, and return a typed terminal error when no eligible offer remains.

OmniRoute or any other aggregator may be evaluated as a **catalogue/provider adapter candidate**, never installed as a second source of truth by hype or star count. Adoption requires license review, provider identity mapping, secret-handling review, request/response compatibility tests, rate-limit semantics, and rollback. Its free-provider claims must be probed and timestamped like every other offer.

### 4.6 Root-only Fable advisor boundary

`Cjbuilds/Codex-Orchestration` PR #1 is closed and superseded by merged PR #2 (`a1d9c546`). NEXUS adopts only its useful protocol pattern: one active root may request one bounded, read-only Fable review, then the root adjudicates. NEXUS does not install its plugin/configurator, edit global Codex configuration, import a second scheduler, or register Fable as a SAGE Action.

The NEXUS adapter is disabled by default and must use a minimal environment allowlist, fixed argv, no tools or session persistence, bounded input/output/time, `TerminalSanitizer`, typed non-reflective failures, and exact runtime `modelUsage` evidence. Upstream `PLAN_APPROVED` maps only to `advisor_no_material_gap`; it never becomes NEXUS approval. Any mixed/unconfirmed route fails closed. Rollback is removal of the explicit feature flag, leaving NexusClaw and SAGE unchanged.

### 4.7 Public `NEXUS_SAGE` release stream

The public `specimba/NEXUS_SAGE` repository currently contains only its initial README. It is a documentation-first release surface, not a mirror of the private runtime. The first public slice may contain a polished product statement, architecture/status/threat-boundary documents, public placeholder contracts, and mocks. It must not contain private endpoints, credentials, raw logs/evidence, model traces, provider errors, weights, internal topology, or production-ready claims.

Promotion requires a leak scan, frontmatter/public-share sanitation, link/license checks, an explicit status matrix, and operator review. If no upstream source is copied, Codex-Orchestration is cited as design inspiration; copied source would require its MIT notice. Public SAGE remains separate from proposal-write and public-hosting promotion.

## 5. Delivery waves and dependency order

### P0 — Contain, prove, and establish the SAGE boundary

**Objective:** A fail-closed SAGE observation surface exists on the correct Brain owner; the old `7354` execution-shaped facade is absent; ModelRelay identity is stable enough to expose sanitized evidence.

Work:

1. Review and retain the six-operation Brain slice and the focused tests.
2. Remove unused duplicate SAGE persistence code so there is one atomic job store.
3. Restart `7354` from hardened source with SAGE gateway disabled; prove MCP/GROSS remains read-only and reports the expected 25-tool contract.
4. Rotate the previously exposed SAGE credential. Store the new value only in the service secret boundary; never source, log, test fixture, shell history, or plan.
5. Restart the correct Brain API owner on `7352` with `NEXUS_SAGE_GATEWAY_MODE=observe_only`.
6. Run ownership preflight with `PortRegistry`, current listener/process identity, and the commands exposed by the current `nexusctl` parser; do not depend on the removed dashboard-doctor command.
7. Prove the live SAGE OpenAPI contains exactly the six allowed operations and no program, shell, memory, swarm, execute, URL-fetch, filesystem, or generic proxy route.
8. Prove `7356/api/model-cards` is the canonical projection and that SAGE strips runtime/provider errors.
9. Repair HERMES `modelrelay` configuration so its picker discovers `7350 /v1/models`; preserve provider credentials in the relay rather than copying them into HERMES.
10. Build the first CLI reach matrix for HERMES, OpenCode, KiloCode, and the Grok build CLI: catalogue count, minimal completion, tool-call compatibility, error class, and timestamp.

P0 claim gates:

- focused SAGE/A2A tests green;
- MCP hardening/tool-contract tests green;
- current `PortRegistry`, listener, and process-identity probes report canonical ownership; `grounding doctor` status is recorded separately;
- `7352` identifies as Brain and passes SAGE `401/503/200` auth/mode probes;
- `7354` has no SAGE routes/key and passes read-only negative probes;
- HERMES `modelrelay` lists more than zero canonical models and completes one minimal request; provider HTTP errors produce typed non-zero failure rather than successful process exit;
- root-supplied FABLE advice has a fresh bounded/redacted/digest-bound receipt proof with `proposal_only=true`, `execution_allowed=false`, `approval_state=pending`, `governor_required=true`, and zero external invocation, job, queue, or Governor side effect (`nexus_os/bridge/fable_advisor.py`; `tests/bridge/test_fable_advisor.py`);
- no credential value appears in diff, process command line, logs, OpenAPI, or responses.

Rollback:

- set SAGE mode to `disabled`, stop the public tunnel, and revoke the SAGE credential;
- leave Brain, relay, and MCP owners on their canonical ports;
- retain proposal DB/audit evidence read-only for forensics;
- revert the service deployment artifact only—do not delete evidence or repurpose a port.

### P1 — Observe-only Custom GPT integration and relay truth

**Depends on:** P0 runtime and secret gates.

**Objective:** The operator can use SAGE to sense NEXUS safely, while every model/CLI view derives from one truthful catalogue and projection.

Work:

1. Export a versioned SAGE OpenAPI document from the tested Brain router; include only the six operations.
2. Publish only `/api/sage/v1/*` through TLS with an explicit reverse-proxy allowlist. The loopback edge already applies body, global concurrency, and rate limits; durable hosting must add redacted access logs and distributed/per-user controls.
3. Configure the SAGE project instructions around Sense/Propose/Witness and the Ultra orchestration profile. Do not encode model slugs or provider secrets in instructions.
4. Enable only the five read operations in the first Action acceptance cycle; keep `POST /jobs` server-side forbidden by `observe_only`.
5. Run prompt-injection, schema-confusion, overlong/chunked-body, IDOR, replay, and error-redaction tests through the public edge.
6. Make provider discovery periodic and diff-based. Each adapter records source, retrieval time, schema version, model additions/removals, endpoint changes, and probe eligibility.
7. Normalize NVIDIA NIM, InternAI, LongCat, Mistral/Leanstral, OpenCode, KiloCode, and other verified lanes into provider offers without collapsing duplicate model IDs.
8. Replace synthetic score fallbacks with per-benchmark evidence cards and confidence. Keep unscored models visible.
9. Add provider cooldown/budget state to the Arena and CLI diagnostics without exposing secret-bearing errors.

Current execution checkpoint:

- **TESTED + LIVE-PROVEN:** the deny-by-default loopback edge on `127.0.0.1:17452` forwards the exact six API operations to fixed Brain origin `127.0.0.1:7352`; local negative-path and body/header/traversal tests pass. The restarted process enforces four concurrent authenticated requests and 60 requests per 60 seconds, returning bounded no-store `429`/`503` responses with `Retry-After`.
- **PROVISIONAL:** an ephemeral ngrok HTTPS preview, with request inspection disabled, passed the complete runtime verifier in `observe_only` mode. It is neither a stable production endpoint nor a promotion record.
- **LIVE-PROVEN (PRIVATE PREVIEW):** the private GPT-5.6 Thinking Draft persisted hardened v3 instructions and completed health, capabilities, grounding, model-card, and missing-job Actions; each external call used `Allow once`, conversation-training use is off, and no job was submitted.
- **TESTED + BUILDER-ACCEPTED:** the regenerated Action-only contract exposes all six operations without warnings or `oneOf`; the canonical artifact documents bounded proposal expiry and remains strict on the server.
- **TESTED + LIVE DRY-RUN:** the job store and sweeper resolve the same canonical runtime database, apply pre-persistence DLP, normalize UTC expiry, and enforce bounded retention; plaintext storage, secure erasure, backup, and recovery remain unresolved.
- **TESTED + LIVE-PROVEN:** the recursive typed model-card projection and independent verifier strip nested provider/runtime errors, credentials, URLs, routing secrets, and arbitrary keys while preserving distinct catalogue, route, health, benchmark, and policy-prior evidence.
- **LIVE-PROVEN DEFECT:** HERMES reaches Leanstral, but normalized `glm-5.2` currently selects an Ollama subscription-only offer and HERMES exits `0` after HTTP `403`; offer-aware routing and typed CLI failure are still P0 dependencies.

Therefore the private P1 read-only Custom GPT observation gate is satisfied. Public/link sharing and production transport remain open and explicitly prohibited.

P1 claim gates:

- Custom GPT public-edge observation smoke passes without any write;
- public schema diff equals the reviewed six-operation contract;
- rate/concurrency limit tests prove bounded `429`/`503`, recovery, authentication-before-admission, and zero upstream calls on rejection;
- no response contains absolute paths, raw memory, source bodies, secrets, provider stack traces, or unredacted runtime errors;
- provider discovery fixture tests cover add, remove, rename, endpoint change, duplicate identity, and stale-catalogue cases;
- Arena totals reconcile across catalogue, CLI visibility, health, evidence, and provider-offer counts;
- a model with no benchmark evidence is rendered UNSCORED, not 45%.
- a fixture/dry-run SAGE -> NexusClaw handoff emits exactly one canonical `NexusClawTaskEnvelope` linked to the pending-review receipt and proposal/parameter digests; forged source, changed digest, non-pending state, or `execution_allowed=true` hard-fail; the test proves zero queue, HERMES, A2A, or external FABLE invocation side effect.

Rollback: disable the public route and SAGE mode; retain local observation routes for tests; restore the last signed provider-catalogue snapshot and mark all unprobed offers `unverified`.

### P2 — Proposal-write, operator approval, and HERMES handoff

**Depends on:** P1 public-edge adversarial acceptance and stable ModelRelay identity.

**Objective:** SAGE can create bounded, idempotent proposals that HERMES executes only after independent authorization.

Work:

1. Promote to `proposal_write` only after an explicit reviewed configuration change.
2. Keep the initial workflow allowlist narrow: grounding audit, evidence search, model-health snapshot, and parallel-audit proposal.
3. Add the proposal-review transition service: `pending_review → accepted|rejected|expired`; only Governor/operator principals may transition.
4. Convert an accepted proposal into one canonical NexusClaw task envelope with provenance, required capabilities, budget, deadline, and approval reference.
5. Make HERMES atomically claim the task; SAGE never claims it.
6. Route effectful work through the signed `8000` A2A execution bridge or an equally governed internal adapter.
7. Persist attempt receipts, retry classification, relay offer selected, cost/token telemetry, tool evidence, and final artifact digest.
8. Project only redacted status/evidence back to `GET /jobs/{job_id}` so SAGE can witness closure.

P2 claim gates:

- duplicate idempotency key + same payload returns the same receipt; changed payload conflicts;
- unauthorized transition, direct execute, raw code, secret, path, URL, and arbitrary tool fields hard-fail;
- accepted task has one approval reference, one atomic HERMES claim, bounded retries, and a VAP/evidence record;
- no SAGE response can cause a privilege expansion;
- end-to-end smoke proves proposal → approval → HERMES claim → signed execution → evidence → witness.

Rollback: return mode to `observe_only`; stop the transition worker; allow already claimed tasks to reach a governed terminal state or quarantine them—never silently requeue effectful work.

### P3 — A2A v1 organization edge, Agent Client Protocol IDE edge, and multi-CLI parity

**Depends on:** P2 lifecycle proof.

**Objective:** SAGE, HERMES, browser agents, and coding CLIs interoperate through protocol adapters without creating parallel governance planes.

Work:

1. Publish a minimal A2A v1 Agent Card for the governed NEXUS boundary: capabilities, authentication method, task states, artifact types, and trust requirements.
2. Map A2A task IDs to canonical NexusClaw tasks and VAP receipts; add replay and sender-signature validation.
3. Add an Agent Client Protocol adapter for approved IDE clients. Map editor sessions/tools to the same proposal and task envelopes.
4. Do not revive the older IBM ACP as a competing bus; its relevant agent-communication concepts converge on the A2A edge.
5. Give HERMES, OpenCode, KiloCode, Grok build CLI, and approved IDE clients a generated ModelRelay profile pointing to `7350`, with fallback policy internal to NEXUS.
6. Add capability negotiation so tool-required work never routes to a chat-only model and structured-output work never routes to an incompatible offer.
7. Add A2A/MCP/ACP conformance smokes and a cross-client model-card consistency test.
8. Add continuity fences: task lease expiry, heartbeat, maximum retry tree depth, duplicate-subagent suppression, and dead-loop detection.

P3 claim gates:

- A2A v1 conformance and signed task lifecycle tests pass;
- Agent Client Protocol adapter cannot bypass auth, approval, or monotonic privilege controls;
- all supported CLIs resolve the same normalized model identity and provider-offer metadata;
- forced NIM 429, timeout, invalid tool schema, and provider removal cases terminate or fall back within budget—no unresponsive recursion;
- A2A smoke crosses Brain authorization and `8000` signed execution with an auditable receipt.

Rollback: disable individual protocol adapters and revoke their client identity; keep the canonical NexusClaw task and ModelRelay APIs intact.

### P4 — Bench-driven routing, adaptive trust, and governed evolution

**Depends on:** P3 protocol parity and durable evidence.

**Objective:** Route and improve models from reproducible evidence, not catalogue hype or self-reported intelligence.

Work:

1. Build benchmark families with explicit comparability groups: coding/terminal, tool use, reasoning/knowledge, science, long-context, safety, latency, cost, and reliability.
2. Store raw run manifests, harness/version, prompts/holdout hashes, evaluator, model/provider offer, decoding settings, date, and confidence.
3. Produce domain scores plus Pareto views; any composite score must publish its formula and evidence coverage.
4. Feed observed task success, policy compliance, retry burden, and evidence quality into Trust—not raw model brand.
5. Use SAGE/frontier lanes as proposal authors, teachers, critics, or judges only with provenance and anti-evaluator-gaming checks.
6. Preserve frozen eval holdouts. Operator-paid traces may enter training only after redaction, provenance tagging, and explicit operator promotion.
7. Train bounded organs such as TokenHD on the A800 bench under the quota hard rule and F-2 gates; keep model weight zero until acceptance evidence exists.
8. Automate provider opportunity discovery as an advisory diff. New free/partner offers remain `unverified` until ToS/license, auth, capability, health, and bench gates pass.
9. Publish a periodic, redacted SAGE witness digest: proposals, decisions, executions, failures, trust changes, relay drift, and unresolved evidence gaps.

P4 claim gates:

- every displayed score traces to a versioned benchmark record or is visibly UNSCORED;
- promotion/demotion decisions are reproducible from evidence and cannot be issued by the candidate model alone;
- full regression, stress, security, leak, and cycle-check gates pass;
- A800 artifacts are durable outside notebook-local state and comply with project-capacity rules;
- rollback can restore the prior routing policy/catalogue snapshot without deleting new evidence.

Rollback: pin the last signed routing policy and evidence snapshot; set newly promoted offers/organs to shadow weight zero; preserve all new runs for review.

## 6. Dependency map

```text
P0 correct ports + fail-closed SAGE + relay reach
 ├─→ P1 observe-only public SAGE
 │    └─→ P2 proposal approval + HERMES lifecycle
 │          └─→ P3 A2A v1 + Agent Client Protocol + CLI parity
 │                 └─→ P4 evidence-driven trust/routing/evolution
 └─→ P1 relay discovery + benchmark evidence
      └───────────────────────────────→ P4
```

No later wave may be used to excuse a failed earlier gate. In particular, A2A/ACP expansion cannot begin with an unowned `7352`, a write-capable `7354`, an exposed SAGE credential, or a HERMES picker showing zero ModelRelay models.

## 7. Claim-gate matrix

| Claim | Minimum authoritative proof |
|---|---|
| “SAGE is implemented” | Current router/security/job/governance source imports and focused tests pass. |
| “SAGE is live” | Correct `7352` owner + authenticated live route matrix + exact live OpenAPI + negative probes. |
| “SAGE is public” | TLS/allowlist probe from outside localhost + redacted access log + public-edge adversarial suite. |
| “SAGE can propose” | Explicit `proposal_write`, durable pending-review receipt, idempotency proof, independent transition authority. |
| “SAGE task executed” | Approval reference + HERMES claim + signed `8000` receipt + artifact digest + VAP record. |
| “7354 is safe” | Owner identity + 25-tool read-only contract + no SAGE key/routes + write-negative tests. |
| “HERMES reaches ModelRelay” | Non-zero canonical `/v1/models` picker result and one minimal completion through HERMES. |
| “Model is online” | Timestamped authenticated health probe for the exact provider offer. |
| “Model is frontier/strong” | Compatible benchmark evidence with source/version/date/confidence—not a default prior. |
| “Provider opportunity is usable” | ToS/license record + credential path + catalogue + capability + health + cost/rate probe. |
| “A2A integrated” | Agent Card + conformance + signed lifecycle smoke + receipt through governance. |
| “Agent Client Protocol integrated” | IDE session/tool smoke mapped to canonical envelopes with no authorization bypass. |
| “Complete” | Full requirement-by-requirement audit, focused and full tests, cycle-check, live proof, and no unresolved P0/P1 blocker. |

## 8. Immediate ordered execution backlog

1. Keep the ChatGPT GPT private and unpublished; preserve `observe_only`, `Allow once`, disabled built-ins/conversation training, and the exact six-operation Action contract.
2. Preserve the current 203-test SAGE gate, listener/supervisor identity proof, real-database retention dry-run, recursive model-card verifier, and restarted local/public edge probes after every change.
3. Fix ModelRelay duplicate-offer identity: HERMES `glm-5.2` must select an explicitly eligible NVIDIA/Baseten/Ollama offer rather than the wrong exact-ID route; provider HTTP failure must return a typed non-zero CLI status.
4. Keep the planned root-only Fable advisor adapter disabled by default; prove environment allowlisting, route confirmation, output sanitization, advisory-only receipts, and zero SAGE Action/OpenAPI change before any opt-in.
5. Finish and leak-scan the documentation-first public `NEXUS_SAGE` foundation; do not push private runtime details, live endpoints, logs, traces, secrets, weights, or production claims.
6. Preserve the natural-language Action-selection rule as a regression gate: a plain-language health request must select the registered Action without an operation ID or Web Search substitution.
7. Run the external adversarial edge suite: prompt/schema confusion, overlong/chunked bodies, IDOR, replay, traversal, error/authorization redaction, obfuscated-secret DLP, and live limit recovery.
8. Replace the ephemeral preview with a governed, restartable HTTPS deployment or retain it explicitly as development-only; document endpoint rotation, revocation, monitoring, privacy ownership, and distributed rate controls.
9. Design per-user OAuth/identity and remove blanket operator semantics before any link or public sharing.
10. Review an operator schedule around the dry-run-first retention utility; add encrypted storage or an approved alternative, operator deletion, backup/recovery, and secure-erasure evidence.
11. Keep `POST /jobs` denied; any independently reviewed negative Builder POST test must prove `403` with zero row creation.
12. Run the four-client reach matrix (HERMES, OpenCode, KiloCode, Grok build CLI) with normalized identity, selected provider offer, result, tool/stream/structured-output support, and typed failure.
13. Reconcile `7350`'s 134 normalized model IDs with `7356`'s 236 provider offers without conflating catalogue, CLI visibility, health, benchmark evidence, or policy priors.
14. Complete the bounded NVIDIA governor and test `Retry-After`, concurrency one, 8-RPM pacing/cooldown, terminal budget, and compatible fallback without recursive retries.
15. Repair or quarantine the single corrupt grounding-ledger line and diagnose the fresh changed-only scan hang through the governed recovery workflow.
16. Prove one positive Brain-governed A2A artifact cycle and one proofless denial before claiming A2A integration.
17. Run the full regression in a permission-correct environment and close the current user-profile/vault temp failures before a whole-system completion claim.
18. Only then design the P2 review-transition worker and request explicit promotion to `proposal_write`.

## 9. Definition of the first useful SAGE milestone

The first milestone is not “SAGE can execute code.” It is:

> From the private NEXUS SAGE Draft on GPT-5.6 Thinking, using the v3 Sense/Propose/Witness instructions and Ultra orchestration profile, the operator can request a bounded NEXUS health/grounding/model assessment, receive only sanitized evidence through the governed Brain API, submit nothing effectful in observe-only mode, and verify that every returned statement traces to a live projection or durable receipt.

The second milestone is one approved proposal completing the full SAGE → Governor → NexusClaw → HERMES → ModelRelay/A2A → evidence → SAGE witness loop without privilege expansion, duplicate execution, hidden retries, or untraceable model selection.

## 10. Required evidence artifacts

Each execution wave must append or update durable artifacts rather than relying on chat claims:

- focused and full test logs with command, timestamp, and exit code;
- port-owner/runtime probe matrix;
- redacted SAGE OpenAPI digest and route allowlist;
- public-edge security/adversarial report;
- CLI/ModelRelay reach matrix;
- provider catalogue-diff and health snapshots;
- proposal/approval/claim/execution/witness receipt chain;
- A2A and Agent Client Protocol conformance reports;
- benchmark run manifests and routing-policy snapshots;
- `nexusctl cycle-check` and cold-handoff package at transfer boundaries;
- append-only NEXUS continuity milestone records.

Until these artifacts prove the corresponding gate, the status remains implemented, tested, or planned—not live, promoted, or complete.

## 11. Dated addendum — 2026-07-14 relay, client, and protocol convergence

This addendum is evidence/status only. It changes no port owner, default model, client profile, SAGE mode, or protocol authority. “Source-tested” and “live-process-proven” remain distinct labels; catalogue presence, a dashboard row, or a fallback sentence is not a health or completion claim.

### 11.1 Reconciled operating truth

| Surface | Reconciled position | Consequence |
|---|---|---|
| `7350` ModelRelay and `7356` Model Arena | The checked-in relay source contains bounded provider-aware canaries, offer-specific 429/access handling, fresh-only route selection, and a terminal-`410` canary exclusion. The dashboard source contains the newer fresh-only card projection and client/frontier-intelligence projections. The running processes may predate those source changes; source or focused-test success is not evidence that either process has reloaded. | Keep the source/process split visible until each port has its own controlled reload receipt. Do not use an old-process `up` flag, stale latency, or a missing new endpoint to infer deployment of the newer policy. |
| GLM-5.2 and Leanstral | In the recorded 2026-07-14 evidence, an exact NVIDIA GLM-5.2 offer had a prior successful observation and later returned HTTP `429`; its honest state is `rate_limited` with cooldown evidence, not healthy. A Leanstral fallback, timeout, or auxiliary-title `503` is degradation/fallback evidence only. | Neither event proves a reliable frontier lane, a correct HERMES primary route, or an acceptable “best available” result. A failed fresh observation must outrank a stale `up` row, and no eligible offer must produce a typed terminal result rather than recursive retries or a false-success exit. |
| Fresh-only resilient routing | The automatic lane is **opt-in**, not a global default. An offer is eligible only when the exact provider offer has a fresh observed success inside its declared TTL, compatible chat/tool/structured-output capabilities, policy approval, and no active cooldown/access block. Selection is provider-diverse and bounded by one retry tree; it never promotes an unverified catalogue entry or silently changes a manually chosen model. | If no exact eligible offer exists, preserve the requested model identity, return a typed degraded/no-eligible-offer result, and expose redacted diagnostics. This is safer than treating Leanstral as a universal substitute. |
| Candidate discovery and benchmark evidence | Daily discovery remains a diff of candidate offers, not a registration, probe, route, or client-default mutation. Fresh public capability evidence may update an evidence sidecar only when its source/version/date/comparability requirements are met; missing evidence remains `UNSCORED`. The local OmniRoute adapter is an explicit opt-in source-card reader pinned to `https://github.com/diegosouzapw/OmniRoute`, version `3.8.46`, commit `9cd18bf9a11b7d2e8c037c374631b492adabf469`, and a detached snapshot hash manifest. It emits quarantined `source_card_candidate` records with no network, provider traffic, or registry auto-promotion; upstream “free”/“no auth” assertions remain unverified claims. | OmniRoute is not installed as a relay, source of truth, or provider credential path. Any candidate still needs independent identity, license/ToS, auth, capability, health, rate/cost, and rollback proof before activation. |
| All-client and WSL boundary | A repository-local manifest is declarative intent, not proof that a client-owned profile is configured. HERMES, OpenCode, KiloCode, Mimo, Pi, Cline, and browser/IDE clients require per-client discovery of binary, configuration owner, schema, effective endpoint, model ID, selected offer, and capability result. WSL access to a Windows-bound relay may require the Windows host gateway rather than `127.0.0.1`; that is a runtime fact to prove per client, never a guessed profile write. `7354` remains the governed MCP boundary and does not replace a CLI’s inference/OAuth configuration. | Do not modify user-home/WSL configurations or claim parity until the exact client configuration is readable, schema-valid, and independently smoke-tested. The reach matrix must record typed failure, including no-eligible-offer, instead of treating a CLI fallback as success. |
| SAGE public/private split | `specimba/NEXUS_SAGE` remains a documentation/mock release surface. Private Brain/SAGE routes, runtime receipts, endpoints, topology, provider errors, logs, secrets, and production assertions stay in the governed private system. Local SAGE contract tests do not make the public repository a live service. | Public documentation may describe boundaries and reviewed mock contracts only. Any public/HTTPS promotion remains separately gated by identity, transport, leak-scan, and adversarial-edge evidence. |
| A2A and ACP authority | The signed A2A smoke validates an inbound signature/replay path only as a `proposal_only=true`, `execution_allowed=false` governed envelope; it is not a live A2A listener, Agent Card, task execution route, or approval. The Agent Client Protocol profile is an IDE-client descriptor/contract; it is not a second governor, an IBM ACP revival, or an authorization bypass. | A2A and ACP both terminate at Bridge → Governor/KAIJU → canonical NexusClaw lifecycle. They cannot select an ungoverned relay offer, execute a SAGE proposal, or use `7354` as an effectful backchannel. |

### 11.2 Concrete P0 closure receipts

1. **`7350` controlled reload receipt:** prove the listener/process identity and source artifact digest before and after restart; then record canonical `/v1/models`, `/api/meta`, and sampler-policy outputs, with the retired `410` alias excluded and exact-offer `429` converted to bounded cooldown/typed failure. No broad provider sweep or synthetic health promotion is acceptable.
2. **`7356` controlled reload receipt:** prove its dashboard process identity and the refreshed projection endpoints; verify that a fresh failed offer is not rendered healthy/top route, stale or unverified offers do not enter “best available,” and benchmark/policy-prior labels remain distinct.
3. **Fresh resilient-lane receipt:** use a fixture or governed non-effectful smoke to prove capability matching, opt-in activation, provider diversity, terminal no-eligible behavior, bounded retry depth, and redacted cooldown diagnostics. A successful fallback alone does not satisfy this gate.
4. **Client/WSL reach receipt:** for every supported client, capture effective endpoint and normalized ID, exact selected offer, tool/stream/structured-output suitability, timestamp, and typed outcome. Preserve a separate `not inspected` state where client-owned configuration cannot safely be verified.
5. **SAGE/A2A/ACP receipt:** retain the private/public separation; prove SAGE’s current authenticated mode separately from source tests, a valid signed A2A proposal plus invalid-signature/replay denial, and ACP's inability to bypass Governor/KAIJU. Do not claim a live Agent Card or execution transport before its P3 gates.
6. **Discovery/provenance receipt:** retain the candidate diff, benchmark sidecar source metadata, and the exact OmniRoute pin/manifest. Promotion requires an independent reviewed proposal; it is never a side effect of an unattended discovery run.

No service restart, provider request, credential read, or user-profile/WSL mutation is authorized by this document update. Until the above receipts exist, the correct whole-system state is **partially implemented and degraded**, not stable or complete.
