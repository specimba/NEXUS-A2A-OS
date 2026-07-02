# NEXUS OS Improvement Roadmap — 2026-07-02

**Status:** ACTIVE. Approved by operator 2026-07-02 (planning run: repo-wide scan + external July-2026 state-of-the-art sweep).
**Horizon:** ~7 weeks, 5 phases + 1 parallel fine-tune track. Executed slice-by-slice; every slice test-gated, evidence-grounded, hard-fail security defaults, no `git add .`.
**Supersedes/absorbs:** `NOVEL_CORE_REVIVAL_2026-07-02.md` remaining slices (slice 2 rotation-handoff DONE — commit 6eeb5164; slices 1/3/4 land in Phase 2 here). Selected items from `LONG_RUN_FUTURE_STEPS_2026-06-29.md` (eval packs → P4-6; temporal defenses → P4-8 decision; MCP gateway → P5). Fine-tune track continues `docs/roadmaps/FINETUNE_MERGE_ROADMAP.md` with the staged DPO→GRPO decision.
**Findings ledger:** `docs/reviews/FULL_AUDIT_2026-06-29_TRIAGE.md` — update with commit evidence as items close.

## Verified sequencing facts (spot-checked 2026-07-02, not assumed)
- Rotation handoff (revival slice 2) is DONE: `nexus_os/relay/model_relay.py` imports `persistent_memory` (6eeb5164).
- LG logprobs feed NOT done — no logprobs/landau path in the relay; daemon path runs `_dry_run_entropy` synthetic.
- Trust unification NOT done — `nexus_os/nexusclaw/agent_pool.py:356-408` still seeds static 95/90/85 floats.
- HERMES collision zone dirty in working tree: `tools/browser_ai_supervisor/*`, `tools/browser_ai_mcp/grok_mcp_server_v2.py`, `nexus_os/nexusclaw/grok_lane_env.py`, `browser_lane_registry.json`, `lane_conversation.py`, `scripts/start_grok_cdp_9224.ps1`, browser docs in `docs/operations/`. DO NOT TOUCH until HERMES lands.

## Operator-blocked items (flagged [OPERATOR] inline)
Git push / 149-commit history-rewrite decision; Lightning.ai T4 session (DPO/GRPO training); Intern Discovery workspace + `doppelground_sessions.jsonl` sanitization; key rotation explicitly declined → plumbing/redaction instead; browser-lane implementation gated on HERMES landing; LongCat beta re-request / novita funding / OpenModel key / siliconflow dashboard key.

## External inspiration → NEXUS mapping (July 2026 sweep)

| External signal | NEXUS application |
|---|---|
| TrustFlow (arXiv 2603.19452): topic-aware *vector* reputation | Validates the 11-element trust vector; consume trust-as-vector in GMR/Chimera routing (P2-2) |
| Semantic Entropy Probes (2406.15927), Semantic Energy (2508.14496), effective-rank uncertainty (2510.08389) | LG detector upgrade path: real logprobs first (P2-1), semantic-cluster entropy experiment after (P5-5) |
| GRPO standard where a verifier exists; DPO useful range 1k–5k pairs | Guard verdicts are programmatically verifiable → staged DPO v1 → GRPO v2 (Track F); extend pairs to 3–5k |
| Zep/Graphiti bi-temporal knowledge graph | Temporal validity on vault facts (P5-6 stretch; subsumes temporal-defenses build) |
| Portkey open-sourced gateway guardrails/PII/audit | Guard/PII/audit in the relay path (P1-10 redaction, P5 MCP audit logging) |
| Stagehand v3 CDP-native hybrid (deterministic fast-path + AI fallback) | Template for closing the browser_ai advisory ↔ CDP execution split-brain (P5-4) |
| MCP H1 2026 (~9,400 servers; Skills primitive incoming) | Expose relay/vault/archivist via existing `nexus_os/mcp/server.py` (P5-1/2/3) |
| June-2026 open-weight wave: GLM-6, DeepSeek V4.1 Flash, Qwen 3.7, MiMo V2 Pro | Registry refresh on free lanes, probe-verified (P4-7) |
| LiteLLM supply-chain attack (Mar 2026) | Pin/audit relay deps; self-built relay is an asset |

---

## Phase 1 — Stop the Bleeding: security criticals + repo foundations (Week 1)

Close every open CRITICAL and the fail-open HIGHs on the network/auth surface; make the repo installable and CI-able. Zero HERMES conflict.

| # | Item | Files | Effort | Test gate |
|---|---|---|---|---|
| 1 | mimo JSONC corruption: `//`-stripper eats `http://` URLs, wipes config every 5-min cycle | `nexus_cli_ctl/integrations/mimo/mimo_integration.py:43` | S | config with `http://` URLs round-trips unchanged |
| 2 | Unauth 0.0.0.0 WS/HTTP 8765/8766 → 127.0.0.1 default + shared token; hard-fail non-loopback w/o token | `nexus_cli_ctl/control/unified_state/state_manager.py:122` | M | non-loopback-without-token raises; unauth → 401 |
| 3 | Brain API weak auth (0.0.0.0:7352, any `nexus-` key mutates) → loopback + constant-time token | `nexus_cli_ctl/daemon/master_daemon.py:195` | S | auth-required test |
| 4 | Relay hardening: guard fail-open :471 → hard-fail; errors-as-200 :396 → real codes; health-cached-forever :272 → TTL; unauth 0.0.0.0 :991 → loopback+token | `nexus_os/relay/model_relay.py` | M | guard-failure rejects; upstream error → 5xx; stale health expires |
| 5 | KAIJU clearance verification — verify vs TrustKernel/governance DB, not caller claims | `nexus_os/governor/base.py:95` | M | spoofed clearance denied |
| 6 | Governor pair: allow-regex path traversal (anchor/normalize); fail-open compliance → default-deny | `governor/privilege_control.py:121`, `governor/base.py:273` | S | traversal + error-path tests |
| 7 | nexusclaw auth pair: spoofable SYSTEM origin → signed/allowlisted; HITL fail-open → hold, don't execute | `nexusclaw/message_bus.py:405`, `nexusclaw/task_router.py:223` | M | spoofed-SYSTEM rejected; HITL-unavailable → task held |
| 8 | Repo P0 hygiene: untrack 5 runtime SQLite DBs; `model_relay/__init__.py`; `pyproject.toml` editable install | `.gitignore`, `pyproject.toml` | M | `python -c "import nexus_os"` clean; no DB churn in `git status` |
| 9 | Minimal CI: `.github/workflows/ci.yml` (ruff + core pytest) + local pre-push runner. [OPERATOR] GitHub activation waits on push decision | `.github/workflows/ci.yml`, `scripts/ci_local.ps1` | S | local runner green |
| 10 | Key-redaction plumbing (rotation declined): central redaction filter for logs/dossiers/relay_info | new `nexus_os/security/redaction.py` | S/M | log-scrub test with canary key pattern |

**Done when:** all 4 CRITICALs closed with tests; committed probe test asserts no unauthenticated non-loopback listener; repo imports cleanly; local CI green; triage updated with evidence.

## Phase 2 — Core Intelligence: wire the built-but-unplugged (Weeks 2–3)

Wire-don't-build: real AES-GCM crypto, real entropy math, and the trust kernel already exist — connect them. Completes revival slices 1/3/4.

| # | Item | Files | Effort | Test gate |
|---|---|---|---|---|
| 1 | LG relay logprobs feed: `logprobs:true/top_logprobs:K` in proxy_completion (Ollama proven via live_demo.py), per-token `assess()`, verdicts → relay_info + A2A. Fix en route: spectral recursion `:195`, logits×0 cooling `:516` (penalize, don't zero) | `relay/model_relay.py`, `twave/landau_ginzburg_tracker_v2.py:314-350` | L | integration test vs local Ollama: real (non-dry-run) assessment in relay_info; unit tests for both twave bugs |
| 2 | Trust unification: TrustKernel singleton; agent_pool read-through (95/90/85 → bootstrap priors only); TrustEngineV2 unify-or-quarantine; 11-element vector where consumers allow | `governor/trust_kernel.py`, `nexusclaw/agent_pool.py:356-408` | L | 14 existing kernel tests + round-trip `agent_pool.update_trust` → kernel persistence; no second store writes |
| 3 | COGER trust budget + fail-closed: kernel budget not default-100; L4 fail-open `:297` → closed; no fabricated L3 answers `:155`; judge attribution `peer_review.py:249` | `gmr/coger.py`, `gmr/peer_review.py` | M | unknown agent → conservative budget; relay failure → error not fabrication; attribution test |
| 4 | GMR breaker `sync_from_relay` | `gmr/circuit_breaker.py` | S | breaker-state propagation test |
| 5 | Vault encryption wiring: orphaned `vault_encrypt.py` (AES-256-GCM+HKDF) into channel persistence; persist channels beyond TRUST encrypted at rest | `security/vault_encrypt.py`, `vault/memory_channels.py` | M | round-trip test; on-disk artifact has no plaintext (grep-canary) |
| 6 | Vault correctness trio: adaptive-persistence trust-gate bypass `:692`; set()→json TypeError `persistent_trust_memory.py:142`; score inversion `semantic_backend.py:358` | vault files | M | unit test per bug |
| 7 | monitor_daemon consumes real LG verdicts + alerts (today: stats reader only) | `twave/monitor_daemon.py` | S | injected high-entropy verdict → alert emitted |

**Done when:** one e2e test shows an `auto-gmr` request against a local model producing a real entropy verdict in relay_info, budgeted by TrustKernel trust, breaker-synced; agent_pool has no independent trust state; vault persists encrypted.

## Phase 3 — CLI/CTL Ecosystem: nexusctl / nexusclaw / nexuscli first-class (Weeks 3–4)

Operator-flagged priority: one coherent installable CLI surface + consolidation of duplicate engines it fronts.

| # | Item | Files | Effort | Test gate |
|---|---|---|---|---|
| 1 | Single nexusctl entrypoint: console-script in pyproject; other form becomes deprecation shim | `nexusctl.py`, `nexusctl/cli.py`, `pyproject.toml` | M | parity test: both forms dispatch identical command table |
| 2 | Dedupe `nexus_os/model_relay/` vs `nexus_os/relay/` (relay/ is the engine; persistent_memory now production-imported — move or shim; delete dead remainder) | both dirs | M | relay + handoff suites green; no orphan imports |
| 3 | Quota unification: 3 impls (`model_relay/quota_tracker.py`, `relay/quota.py`, generated) → 1 canonical | quota modules | M | quota tests ported; consumer integration green |
| 4 | rotate_keys full propagation (today: opencode only) + shared redaction helper; browser lanes read-only w.r.t. HERMES | `nexusctl/rotate_keys.py:240` | M | dry-run lists every target; sync test vs fixture configs |
| 5 | sync_hermes YAML nesting fix (providers at column 0; `!r` quoting) | `nexusctl/model_sync.py:506` | S | YAML structure assertion |
| 6 | Schedule `nexusctl models verify` in monitor_daemon; last-verify age in `nexusctl status` | `models_cli.py`, monitor_daemon | S | schedule + status-output tests |
| 7 | New CLI surface: `nexusctl trust` / `vault status` / `relay verdicts` (trails P2) | `nexusctl/` | M | golden-output CLI tests |
| 8 | nexusclaw/nexusctl harmonization + split-of-responsibilities doc | `docs/` | S/M | help-text conformance + doc committed |

**Done when:** fresh clone → `pip install -e .` → `nexusctl status`/`models verify`/`quota`/`trust` all work from one entrypoint; exactly one quota impl and one relay package; rotate_keys dry-run enumerates all consumers.

## Phase 4 — Reliability & Ops: daemons, swarm, wiki, registry (Weeks 4–5)

| # | Item | Files | Effort | Test gate |
|---|---|---|---|---|
| 1 | Swarm: foreman self-deadlock `:325`; worker claim-before-run idempotency `:128` | `swarm/foreman.py`, `swarm/worker.py` | M | two workers/one task → single execution; foreman self-assignment test |
| 2 | doppelground_bridge trust from TrustKernel (not self-asserted 90) | `archivist/doppelground_bridge.py:102` | S | kernel-sourced score assertion |
| 3 | Chimera resilience-tier predicate (`:370` excludes every recent model) | `twave/chimera_router_v2.py` | S | ≥1 current registry model qualifies per tier |
| 4 | Wiki pipeline unification: `archivist/fit.py` canonical; `nexusclaw/wiki_intel_pipeline.py` becomes caller | both pipelines | M | both entry paths → identical dossier output on fixture corpus |
| 5 | Govern the :7356 dashboard: loopback+token per P1 pattern; monitor_daemon health registration; audit-log telemetry reads | `scripts/serve_dashboard_7356.js` | M | unauth → 401; health-registration test |
| 6 | Eval-pack harness: prompt packs → relay → scored JSON report (doubles as Track F eval infra) | new `nexus_os/eval/` | M | self-test on 10-prompt smoke pack vs local model |
| 7 | June-2026 model-wave registry refresh: GLM-6, DeepSeek V4.1 Flash, Qwen 3.7, MiMo V2 Pro on free lanes; probe-verify; regen tables | `config/models.registry.json`, gen pipeline | S/M | `models verify` green; generated-table diff reviewed |
| 8 | Temporal-defenses decision doc (recommend: defer to P5 Graphiti evaluation — avoid double-building temporal machinery) | `docs/plans/` | S | decision doc committed |

**Done when:** 24h unattended daemon soak clean (zero duplicate executions, zero deadlocks, log-audited); one wiki pipeline; authenticated dashboard; June-wave models probe-verified; eval harness e2e.

## Phase 5 — New Capabilities: MCP, browser hybrid, semantic detection (Weeks 5–7)

| # | Item | Files | Effort | Test gate |
|---|---|---|---|---|
| 1 | MCP server: relay completion + registry tools, TrustKernel-gated, audit-logged; align with `nexus_mcp_profile_*.yaml` (working-tree — confirm ownership first) | `nexus_os/mcp/server.py` | M | MCP client test: list_tools + gated call + denied call |
| 2 | MCP server: vault + archivist read-mostly tools (dossier search, trust-gated memory query); P1 redaction mandatory | `nexus_os/mcp/` | M | redaction canary through MCP path; trust-denial test |
| 3 | MCP Skills-primitive readiness (watch item — thin wrappers when it ships) | — | S | — |
| 4 | [HERMES-gated] Browser hybrid closed loop (Stagehand-v3 pattern). Until HERMES lands: interface contract doc ONLY (`docs/plans/BROWSER_HYBRID_CONTRACT.md`) defining verdict/action schema over A2A. NO collision-zone edits | contract doc now; impl later | S now / L post-HERMES | contract reviewed; post-HERMES: advisory decision → CDP execution → result fed back |
| 5 | Semantic-entropy detector upgrade (SEP/Semantic Energy layered on P2 feed, flag-gated) | `twave/`, `monitoring/` | L | P4 eval-pack comparison: semantic must beat token entropy on labeled pack before default-on |
| 6 | Graphiti-style bi-temporal vault facts (stretch; supersede-don't-overwrite; subsumes P4-8 if adopted) | `vault/` | L | temporal query test (true at T1, superseded at T2) |

**Done when:** external MCP client calls relay + archivist tools with trust gating and clean redaction; browser contract agreed (impl only if HERMES lands in window); semantic detector has a written adopt/reject verdict.

## Track F (parallel from week 1) — Fine-tune: DPO v1 → GRPO v2 → compare

Staged per operator decision. Local work proceeds now; training runs wait on operator sessions.

| # | Item | Effort | Gate |
|---|---|---|---|
| 1 | Extend DPO pairs 1k → 3–5k (pipeline live, resumable) + dedup/quality pass | S ongoing | pair-schema validation + dedup-rate report |
| 2 | Frozen held-out eval set FIRST: ~10–15% stratified + adversarial guard prompts; hashes committed; never trained on | M | eval-pack hashes committed; untrained-guard baseline row scored |
| 3 | DPO v1 LoRA training runner (peft/trl, T4-sized, local RTX 4070 smoke) — none exists in repo | M | 10-step local smoke: loss decreases, checkpoint round-trips |
| 4 | [OPERATOR] DPO v1 train on Lightning T4 → baseline eval row | — | eval ≥ untrained baseline; artifacts archived |
| 5 | GRPO v2 runner: reward = programmatic guard-verdict correctness, group sampling | L | 10-step smoke; advantage variance > 0 |
| 6 | [OPERATOR] GRPO v2 train + comparison report (untrained vs DPO vs GRPO, same frozen pack) → promote winner only if it beats DPO | — | per-category score report committed |
| 7 | doppelground_sessions.jsonl sanitization script (reuses P1 redaction) — phase-3 Nexus-OS-7B prereq | M | sanitization test on fixture with canary secrets |

**Done when:** comparison report exists with both checkpoints on the same frozen held-out pack and a recorded promotion decision.

## Dependency graph

```
P1 security+packaging --> P2 core wiring --> P3 CLI (trust/vault cmds trail)
        |                      |                    |
        v                      v                    v
        +----------------> P4 reliability <--------+
                               | (eval harness)
                               v
                          P5 capabilities   (browser item gated on HERMES)
Track F: parallel from week 1; training runs gated on operator T4 / Intern sessions
```

## Standing rules for every slice
- Test gate before commit; no `git add .`; fail-closed everywhere a finding says fail-open.
- Never edit HERMES collision-zone files; check their `git status` dirtiness before any nexusclaw/browser-adjacent change.
- Free-tier providers only; no key rotation — redaction/plumbing instead.
- [OPERATOR] Push blocked until history-rewrite decision; keep commits atomic so either rewrite path stays cheap.
