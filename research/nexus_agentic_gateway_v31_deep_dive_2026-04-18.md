# Nexus Agentic Gateway v3.1 Deep Dive

Date: 2026-04-18
Scope: research-only audit of `C:\Users\speci.000\Downloads\nexus-os-agentic-gateway-v3.1 (1)` plus external and local reference systems

## Executive Verdict

The downloaded product is not yet a real Nexus gateway. It is a polished prototype with a genuine Google Vertex proxy backend and a largely simulated Nexus UI on top.

The correct upgrade path is not to keep extending the download as its own standalone backend. The correct path is:

1. Treat the downloaded app as a frontend shell and analyst console.
2. Re-anchor all backend behavior into the existing `NEXUS` Python system under `src/nexus_os/`.
3. Use LiteLLM for provider normalization, FastAPI for the API surface, Governor and TokenGuard for policy and budget enforcement, GMR for routing, and evaluation harnesses inspired by ISC-Bench, Secure-Hulk, AEGIS, ShieldGemma, RigorLLM, OR-Bench, and adaptive jailbreak work.

## Local Reality Audit

### What the downloaded product really is

- `README.md` says the app is a "Vertex AI Studio Frontend App with Node.js Backend" and is "intended for demonstration and prototyping purposes only", not production.
- `backend/server.js` is a Google-only Express proxy. It requires `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, Application Default Credentials, and a custom `PROXY_HEADER`.
- `frontend/vertex-ai-proxy-interceptor.js` intercepts only Google Vertex and Reasoning Engine URLs and forwards them to `/api-proxy` with a hardcoded `X-App-Proxy` header.

### What the UI claims it is

- `frontend/App.tsx` presents the product as `NEXUS OS Gateway` with tabs for `Threat Intel`, `GMR v4.0`, `AI Failures`, and `Telemetry`.
- `frontend/components/GMRDashboard.tsx` advertises `RelayFreeLLM`, `LiteLLM`, free-provider routing, key rotation, proxy wrappers, and fallback cascades.
- `frontend/geminiService.ts` asks Gemini to produce analyses framed in terms of `ISC-Bench`, `Magpie`, `Secure-Hulk`, `CARG-Eval`, and `LiteLLM/GMR`.

### What is simulated or missing

- `frontend/components/Telemetry.tsx` is driven by `MOCK_DATA`, so telemetry is not real.
- `frontend/components/GMRDashboard.tsx` uses a hardcoded `REAL_FREE_MODELS` array. Those routes are not backed by corresponding provider infrastructure in `backend/server.js`.
- There is no real multi-provider gateway, no true provider registry, no live LiteLLM router, no real RelayFreeLLM failover chain, and no governance-grade evaluation harness wired into the downloaded backend.

## Important Local Context Already Available in NEXUS

The current `NEXUS` repo already contains most of the real backend pieces the download is pretending to have:

- `src/nexus_os/bridge/server.py`: FastAPI-oriented A2A bridge with HMAC auth, KAIJU authorization, executor dispatch, and token headers.
- `src/nexus_os/monitoring/token_guard.py`: budget tracking, hard-stop thresholds, and VAP-style audit entries.
- `src/nexus_os/governor/trust_scoring.py`: lane-scoped trust scoring with non-compensatory harm logic.
- `src/nexus_os/gmr/context_packet.py`: zero-context-loss handoff packet.
- `src/nexus_os/gmr/rotator.py`: dual-pool routing, intent classification, failure accounting, and circuit-breaking.

This means the best path is convergence, not reinvention.

## Source-Ranked Matrix

| Rank | Source | Evidence Strength | What to Borrow | What Not to Borrow |
|---|---|---:|---|---|
| 1 | Local downloaded gateway files | High | Honest reality of current prototype, UI/backend mismatch | Do not mistake branded UI claims for implemented capabilities |
| 2 | Current `NEXUS/src/nexus_os` code | High | Canonical backend structure: Bridge, Governor, GMR, TokenGuard, Trust | Do not fork a second backend around the download |
| 3 | `Downloads/Team Update – NexusAlpha x ISC-Benc.txt` | Medium | StressLab framing, FREE_RESEARCH pool idea, central relay model, inspiration-registry concept | Treat status claims as proposals unless confirmed in repo |
| 4 | `Downloads/System Status ARCHITECTURAL SYNCHRO.txt` | Medium | Validator-first "weight room", surgical patch loop, metrics/evidence split, proposed unification map | Do not treat the proposed `nexus_aegis` tree as current canon |
| 5 | User-provided `Nexus-Aegis Sovereign OS` architecture report | Medium | Glass Box metrics, calm-mode release gates, temporal-causal patch lineage, explicit constitutional bans, gateway/vault/session-bus decomposition | Do not create a second sovereign tree before proving modules inside current canon |
| 6 | [LiteLLM docs](https://docs.litellm.ai/) and [repo](https://github.com/BerriAI/litellm) | High | Unified multi-provider gateway, auth, budgets, guardrails, fallback, spend tracking | Do not let LiteLLM become policy authority; keep Governor above it |
| 7 | [FastAPI](https://github.com/fastapi/fastapi) and [dependency system docs](https://fastapi.tiangolo.com/tutorial/dependencies/) | High | Production API surface, dependency injection, security middleware composition | Do not keep the Node prototype as the long-term control plane |
| 8 | [OpenAI Agents SDK repo](https://github.com/openai/openai-agents-python), [handoffs](https://openai.github.io/openai-agents-python/handoffs/), [tracing](https://openai.github.io/openai-agents-python/tracing/) | High | Handoffs, tools, guardrails, tracing model for multi-agent workflows | Do not replace Nexus orchestration with SDK defaults wholesale |
| 9 | [RelayFreeLLM](https://github.com/msmarkgu/RelayFreeLLM) | Medium | Session affinity, failover, context management, strict boot validation | Treat as design inspiration, not canonical governance layer |
| 10 | [ISC-Bench repo](https://github.com/wuyoscar/ISC-Bench), [paper](https://arxiv.org/abs/2603.23509), local `Downloads\\ISCbench` copy | High | TVD workflow testing, domain templates, layered verification for specialist harms | Do not collapse all safety evaluation into single-turn jailbreak metrics |
| 11 | [Secure-Hulk](https://github.com/AppiumTestDistribution/secure-hulk) | High | MCP/tool security scanning: prompt injection, tool poisoning, toxic flows, exfiltration | Do not assume scanner coverage replaces runtime policy enforcement |
| 12 | [AEGIS paper](https://arxiv.org/pdf/2404.05993v2) | High | Risk taxonomy, expert-ensemble moderation, broader safety benchmark coverage | Do not rely on moderation only at model output time |
| 13 | [ShieldGemma paper](https://arxiv.org/abs/2407.21772) | High | Strong lightweight moderation model option for input/output safety | Do not use one moderator as sole oracle |
| 14 | [RigorLLM paper](https://arxiv.org/abs/2403.13031) | High | Resilient guardrail pattern against adversarial inputs and jailbreaks | Avoid heavy guardrail placement on every hot-path call without latency budgeting |
| 15 | [OR-Bench paper](https://arxiv.org/pdf/2405.20947v1), [identity suppression paper](https://arxiv.org/abs/2409.13725), [GAI moderation UX paper](https://arxiv.org/pdf/2506.14018v1) | High | Over-refusal, fairness, appeals, explainability, user trust | Do not optimize safety by indiscriminate refusal |
| 16 | [Magpie repo](https://github.com/magpie-align/magpie) | Medium | Synthetic task and alignment data generation for evals and regression suites | Do not use synthetic data without provenance labels and human review gates |
| 17 | [ZenGuard repo](https://github.com/ZenGuard-AI/fast-llm-security-guardrails) | Medium | Runtime trust-layer pattern, prompt injection and PII detectors | The repo is archived; use pattern ideas, not as a long-term foundational dependency |
| 18 | [amardeeplakshkar/awesome-free-llm-apis](https://github.com/amardeeplakshkar/awesome-free-llm-apis) and [cheahjs/free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) | Medium | Provider discovery, rate-limit metadata, OpenAI-compat flags | Do not treat these lists as stable or governance-grade truth |

## Strongest Research Claims

1. [ISC-Bench paper](https://arxiv.org/pdf/2603.23509) identifies a structural failure mode where legitimate workflows can cause frontier models to generate harmful content; it reports `53 TVD scenarios across 8 professional disciplines` and worst-case safety failure rates averaging `95.3%` in representative settings.
2. [LiteLLM docs](https://docs.litellm.ai/) and [repo](https://github.com/BerriAI/litellm) show the right abstraction for provider normalization: one interface across `100+` providers, with retry and fallback logic, budgets, virtual keys, logging, and a centralized proxy model.
3. [OpenAI Agents tracing docs](https://openai.github.io/openai-agents-python/tracing/) and [handoff docs](https://openai.github.io/openai-agents-python/handoffs/) show a clean model for agent delegation and observability: handoffs are explicit, and traces should capture model calls, tools, handoffs, and guardrails.
4. [Secure-Hulk](https://github.com/AppiumTestDistribution/secure-hulk) explicitly targets MCP-native risks that matter here: prompt injection, tool poisoning, cross-origin escalation, exfiltration, and toxic agent flows.
5. [AEGIS](https://arxiv.org/pdf/2404.05993v2), [ShieldGemma](https://arxiv.org/abs/2407.21772), and [RigorLLM](https://arxiv.org/abs/2403.13031) together argue for layered moderation and resilient guardrails rather than a single classifier or naive refusal layer.
6. [OR-Bench](https://arxiv.org/pdf/2405.20947v1), [Identity-related Speech Suppression](https://arxiv.org/abs/2409.13725), and the [GAI moderation UX paper](https://arxiv.org/pdf/2506.14018v1) show the other half of the problem: safety systems can also over-refuse, suppress identity-related expression, and frustrate legitimate users if governance is not calibrated.

## Working Target Structure

Do not evolve the downloaded folder into a separate production backend. Turn it into a frontend package that talks to the real Nexus runtime.

```text
NEXUS/
  src/nexus_os/
    bridge/
      server.py            <- public API ingress
      provider_gateway.py  <- LiteLLM adapter layer
      provider_registry.py <- free/pro/trial provider metadata
    governor/
      compliance.py
      kaiju_auth.py
      trust_scoring.py
      moderation.py        <- AEGIS / ShieldGemma / RigorLLM / ZenGuard adapters
    gmr/
      rotator.py
      context_packet.py
      telemetry.py
    monitoring/
      token_guard.py
      tracing_export.py
    evals/
      isc/
      moderation/
      overrefusal/
      mcp_security/
  apps/
    nexus_gateway_ui/      <- migrated frontend shell from downloaded product
```

## 2026-04-19 Team Report Delta Integration

The two latest team reports add several useful ideas that were not explicit enough in the first version of this research note. The important correction is to integrate them as layered proposals, not as already-landed system state.

### What the latest team reports add

1. They sharpen the role of ISC-Bench from "benchmark inspiration" into a dedicated internal failure-simulation lab.
2. They make the free-provider layer operationally clearer: one central research pool behind Hermes/GMR, not key handling spread across sub-agents.
3. They introduce a validator-first self-improvement loop: stress case fails, evidence is logged, patch is synthesized, patch is verified, then promoted.
4. They add a useful distinction between production pillars and experimental adaptation layers.
5. They suggest an "Inspiration Registry" model for tracking which starred repositories matter to which Nexus subsystem.

### What is locally confirmed versus team-proposed

Locally confirmed in the current repo:

- `src/nexus_os/engine/hermes.py` exists, but it is a router and scorer, not yet the dual-judge AEGIS-style governor described in the team report.
- `src/nexus_os/swarm/` exists, so swarm execution is a valid integration point.
- `src/nexus_os/monitoring/token_guard.py` exists and is already meaningful infrastructure.
- `stresslab/` does not exist in the current repo.
- `src/nexus_os/weight_room/` does not exist in the current repo.

Therefore the right integration stance is:

- treat `StressLab`, `weight_room`, `FREE_RESEARCH`, `Inspiration Registry`, and `validator-first patch loop` as next-structure proposals
- do not represent them as already implemented

## Newly Integrated Structural Recommendations

### 1. Add a dedicated StressLab package

This was under-specified in the prior draft and should now be explicit.

Recommended shape:

```text
NEXUS/
  src/nexus_os/
    evals/
      isc/
      moderation/
      overrefusal/
      mcp_security/
    stresslab/
      __init__.py
      run_isc.py
      batch_isc.py
      templates/
      adapters/
      validators/
      reports/
```

Purpose:

- run ISC-Bench-derived TVD scenarios under Nexus controls
- inject TokenGuard, Governor, Trust, and VAP assertions into execution loops
- archive results as governance evidence rather than one-off red-team notes

### 2. Add a central `FREE_RESEARCH` pool behind GMR

The prior report discussed provider discovery but not the operational boundary strongly enough.

New recommendation:

- add a research-only provider pool to GMR, named `FREE_RESEARCH` or `FREE_POOL`
- only the gateway/provider mesh may hold relay credentials or free-tier provider config
- Hermes, swarm workers, and experimental runners request capability through the gateway, never directly through scattered provider keys

This is the right way to absorb the free-API repo ecosystem without turning the system into unmanaged key sprawl.

### 3. Add validator-first patching as an experimental loop

The team report is directionally correct here, and it fills a genuine gap in the original blueprint.

Recommended loop:

1. StressLab runs a scenario and captures structured failure.
2. Evidence and trace data are written to the audit/evidence layer.
3. Hermes or a dedicated analysis component classifies the failure.
4. SkillSmith proposes a patch, rule update, or deterministic skill.
5. The patch is tested against the originating validator.
6. Only validated outputs are promoted into the canonical runtime.

This should live in experimental space first, not directly inside the hot production path.

### 4. Add an Inspiration Registry

The original report referenced external repos, but it did not recommend a durable local index for them.

This is worth adding:

```text
research/
  inspiration_registry.md
  sources/
    routing.md
    governance.md
    evals.md
    swarm.md
    free_providers.md
```

Each entry should record:

- source
- subsystem relevance
- adaptation target
- confidence
- implementation status

This turns the starred-repo and team-scan work into reusable system memory instead of conversational drift.

### 5. Split production pillars from experimental adaptation layers

The `nexus_aegis` tree proposed in the architectural synchronization report is useful as a thought model, but it should not replace the current canonical tree yet.

A safer integration is:

- keep `src/nexus_os/` as canon
- add experimental layers under names like `stresslab/`, `skills/`, or `experimental/`
- only promote individual modules into canon once verified

That preserves branch sanity and avoids a disruptive rename before the new concepts are proven.

## Additional OSMAN Report Integration

The later `Nexus-Aegis Sovereign OS` report adds a stronger scientific-operations layer than the earlier team notes. The useful parts are real improvements to this blueprint, but the proposed `src/nexus_aegis/` parallel tree should still be treated as a design sketch, not an immediate filesystem target.

### Highest-value additions from this report

1. **Glass Box observability**
   The report correctly pushes beyond generic telemetry into explicit scientific metrics: convergence rate, regression rate, value density, and stability index. Those metrics should become first-class outputs of StressLab and future dashboards.

2. **Calm-mode release gates**
   The suggested acceptance bar is strong and concrete: repeated randomized cycles, zero-regression thresholds, budget stability, and no silent infrastructure failures. This is a better deployment gate than feature-complete checklists.

3. **Temporal-causal patch lineage**
   The report usefully extends memory design by insisting that every promoted patch remain linked to the exact validator failure that triggered it. That should become part of evidence logging and future memory-channel design.

4. **Explicit constitutional bans**
   The report is right to make some synthesis bans crisp rather than heuristic, especially for synthesized deterministic skills. That belongs in governance policy even if the exact rule set is refined later.

5. **Gateway decomposition**
   The decomposition into ingress, vault/provider gateway, router, and session bus is useful. The names may change, but the separation of concerns is sound.

### What to adopt from this report

- Add a `Glass Box` concept to the control-plane roadmap.
- Track `convergence_rate`, `regression_rate`, `value_density`, and `stability_index`.
- Require promotion gates based on repeated validator success, not single-pass correctness.
- Add evidence lineage so each patch, rule change, or promoted skill can be traced back to its originating failure.
- Treat local, free-tier, and frontier inference as explicit tiers inside the provider architecture.

### What not to adopt literally

- Do not create a second parallel root package like `src/nexus_aegis/` while `src/nexus_os/` is already the canonical runtime.
- Do not describe `Weight Room` as the universal primary execution boundary for all production traffic. It is better modeled as the primary experimental validation boundary.
- Do not declare Secure-Hulk-style bans sufficient by themselves; keep them as one layer under Governor and verification gates.

### Revised interpretation

The strongest reading of the OSMAN report is not "rename Nexus into Aegis." The strongest reading is:

- keep Nexus as the sovereign production substrate
- add Aegis-style scientific method around it
- make StressLab the experimental proving ground
- make Glass Box the scientific observability layer
- only promote experimentally proven modules into the canonical Nexus tree

## Recommended Service Boundaries

### 1. UI Shell

Keep the downloaded frontend, but remove dashboard theater.

- `ThreatIntel` becomes a real analysis client for the backend.
- `GMRDashboard` becomes a live view over `gmr/telemetry.py`, provider registry health, and rotator decisions.
- `Telemetry` becomes real traces, token budgets, moderation events, and trust transitions.
- `AI Failures` becomes eval results and incident snapshots, not static content.

### 2. Gateway API

Replace the prototype Node backend with FastAPI as the canonical ingress.

- Use FastAPI dependencies for auth, budget checks, policy checks, tracing context, and provider access.
- Keep the existing `BridgeServer` concepts, but expose clear REST and JSON-RPC entrypoints.
- Use WebSockets only for live events and streaming responses, not as a provider-specific Google shim.

### 3. Provider Mesh

Use LiteLLM as the provider normalization layer.

- Centralize provider auth, retries, fallback, and cost tracking there.
- Keep provider metadata in a Nexus-owned registry.
- Use the free-API repos only as seed data for discovery and experimentation.
- Use explicit provider tiers:
  - `LOCAL` for zero-cost discovery and cheap deterministic loops
  - `FREE_RESEARCH` for rate-limited cloud experimentation
  - `FRONTIER` for validation-critical or escalation-only paths
- Import RelayFreeLLM ideas selectively:
  - session affinity
  - context pruning modes
  - strict boot validation
  - automatic failover

### 4. Governance Layer

Put Governor above provider routing.

- TokenGuard runs before expensive inference.
- KAIJU auth and scope checks run before task execution.
- Moderation adapters run on ingress, egress, and tool handoff boundaries.
- Trust scoring remains lane-scoped and non-compensatory.
- MCP/tool security scanning runs continuously on tool manifests and selected flows.

### 5. Agent Runtime

Adopt OpenAI Agents SDK patterns, not necessarily the SDK as the only runtime.

- Explicit handoffs between specialist agents.
- Tracing spans for model calls, tools, handoffs, guardrails, and human intervention.
- Zero-context-loss handoffs via `ContextPacket`.
- Handoff decisions should be visible in the UI and auditable in Vault.

## Governance Test Framework

The product needs a wide governance suite, not one benchmark.

### A. Structural Harm and Workflow-Induced Failure

Use ISC-Bench as the main research harness.

- Run TVD-style scenarios across text, code, cyber, chemistry, biology, and clinical workflows.
- Use the local `Downloads\\ISCbench\\ISC-Bench` copy for templates and verification rules.
- Add domain-tagged result classes: `triggered`, `held`, `specialist-review`, `false-positive`, `over-refusal`.

### B. Moderation Breadth

Use AEGIS and ShieldGemma patterns.

- Multi-category risk taxonomy.
- Ensemble or multi-model scoring for uncertain cases.
- Separate input moderation, output moderation, and tool-response moderation.

### C. Jailbreak Robustness

Use adaptive attack literature and RigorLLM.

- Test suffix attacks, logprob-adaptive attacks where applicable, and transfer attacks.
- Measure whether the gateway catches unsafe intent before and after provider fallback.

### D. Over-Refusal and Fairness

Use OR-Bench, speech suppression, and user-moderation UX research.

- Track safe refusal errors.
- Track identity-related suppression.
- Track appealability and explanation quality for blocked requests.

### E. MCP and Tool Security

Use Secure-Hulk style coverage.

- prompt injection
- indirect prompt injection
- tool poisoning
- cross-origin escalation
- privilege escalation
- cross-resource attacks
- toxic agent flows
- exfiltration attempts

### F. Synthetic Regression Generation

Use Magpie carefully.

- Generate structured benign and harmful edge cases for regression testing.
- Label all synthetic examples with provenance and review state.
- Keep synthetic eval corpora separate from production memory and user traffic.

### G. Evolutionary Repair and Skill Promotion

This section is newly explicit based on the latest team reports.

- Track failure recurrence, convergence rate, regression rate, and value density for candidate fixes.
- Let validator-backed repair loops propose deterministic skills, patches, or policy deltas.
- Require proof-chain and verification records before promotion.
- Keep draft skills and promoted skills separate until they survive repeated zero-regression cycles.

## Concrete Upgrade Phases

### Phase 0: Truth Alignment

- Remove fake telemetry and static routing metrics from the UI.
- Mark every placeholder metric as simulated until live.
- Freeze the Google-only proxy as legacy prototype code.

### Phase 1: Backend Convergence

- Mount the frontend against `NEXUS` FastAPI endpoints.
- Add provider gateway and provider registry modules under `src/nexus_os/bridge/`.
- Keep Vertex as one provider, not the architecture.

### Phase 2: GMR Becomes Real

- Connect `GMRDashboard` to live provider telemetry and routing decisions.
- Implement FAST and PREMIUM pools against actual providers.
- Add fallbacks, circuit breaking, and session affinity.

### Phase 3: Governance Hardening

- Wire ingress and egress moderation adapters.
- Expose Governor decisions and TokenGuard budget events to telemetry.
- Add explainable deny and held states.

### Phase 4: Evaluation and Red-Team

- Build an `evals/` package and run scheduled governance suites.
- Add ISC-Bench-derived structural harm tests.
- Add OR-Bench and suppression tests so safety does not become blunt refusal.
- Add a first experimental `stresslab/` runner, not just loose benchmark scripts.
- Add a validator-backed patch loop for recurrent failure classes.

### Phase 5: Analyst-Facing Control Plane

- Threat Intel becomes a real analyst workspace.
- AI Failures becomes a searchable failure registry with trace links.
- Telemetry becomes the operator view for budgets, moderation, provider health, and trust.
- Add an internal "StressLab Arena" view for template coverage, trigger rate, hold rate, and mitigation success over time.
- Add a `Glass Box` scientific view for convergence, regression, value density, and patch lineage.

### Phase 6: Calm-Mode Release Gates

- Require repeated randomized StressLab runs before any release candidate is treated as stable.
- Track `convergence_rate`, `regression_rate`, `value_density`, and `stability_index` as release metrics.
- Require zero silent promotion: every promoted patch, rule change, or skill must have validator evidence and proof-chain lineage.
- Treat local/free/frontier tier stability as part of release readiness, not just model quality.

## Practical Design Decisions

### Keep

- The frontend layout and analyst-console framing.
- The idea of a GMR dashboard.
- The threat-analysis schema ambition.
- The broader Nexus branding and control-plane concept.

### Replace

- The Node/Vertex backend as the core gateway.
- The hardcoded interceptor-first architecture.
- Static provider tables.
- Mock telemetry.
- implied capabilities that are not backed by code.

### Add

- FastAPI ingress
- LiteLLM provider mesh
- central `FREE_RESEARCH` pool
- real provider registry
- moderation adapters
- evaluation harnesses
- StressLab and validator-backed repair loop
- inspiration registry
- Glass Box scientific telemetry
- temporal-causal patch lineage
- calm-mode release thresholds
- trace-backed observability
- incident and appeals model

## Critical Risks If You Do Nothing

1. The UI will keep overstating system capability and create false operator confidence.
2. The backend will remain locked to Google-specific flows while the UI implies a multi-provider runtime.
3. Governance claims will remain aspirational instead of test-backed.
4. Safety will be biased toward refusal theater unless structural-harm, fairness, and over-refusal testing are all present.
5. Self-improvement loops will become anecdotal rather than scientific if convergence, regression, and lineage are not measured explicitly.

## Research Gaps and Confidence Limits

- I could not directly verify `https://github.com/specimba/awesome-free-llm-apiss`; it appears unavailable or non-public from current sources.
- I could not retrieve a usable primary source for `https://github.com/0xrdan/carg-eval`; I therefore did not treat it as a verified architectural dependency.
- ZenGuard is useful as a pattern source, but the repository is archived, so it should not be treated as a stable foundation.
- Free-provider lists are valuable discovery inputs but are operationally volatile.

## Bottom Line

The downloaded product is worth keeping, but only as a control-plane shell.

If you want a real Nexus Agentic Gateway, the canonical backend should be the existing `NEXUS/src/nexus_os` system, upgraded with:

- FastAPI ingress
- LiteLLM provider normalization
- a central `FREE_RESEARCH` provider pool for research traffic
- RelayFreeLLM-inspired failover and context management
- OpenAI Agents-style handoffs and tracing
- Governor, TokenGuard, and trust scoring as first-class enforcement
- StressLab for validator-backed failure simulation and repair
- ISC-Bench, Secure-Hulk, AEGIS, ShieldGemma, RigorLLM, OR-Bench, and moderation-UX research as the governance test stack

That yields a real structure instead of a dashboard that only narrates one.
