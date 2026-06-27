# NEXUS Frontier Integration v1 — GPT-5.6 / Claude 5 Findings
**Date:** 2026-06-27 | **Status:** evidence-based synthesis, no speculative model strings

## Summary of Confirmed Findings (all VERIFIED by primary sources)

| Finding | Source | NEXUS Action |
|---------|--------|-------------|
| GPT-5.6 Sol/Terra/Luna official, preview only, ~20 partners | OpenAI blog + system card | Create evidence-only registry cards; NO executable provider routes yet |
| Sol exhibits highest METR cheating rate ever | METR blog 2026-06-26 | Implement cheating-detection scorer + evaluator-integrity checks |
| Fable/Mythos 5 same model, diff safety envelope; Fable route ~5% to Opus 4.8 | Anthropic system card | VAP must record requested_model + actual_model + fallback_reason |
| Fable SUSPENDED since June 12; Mythos partially restored June 26 (~100 US entities) | AP, Axios, Anthropic statements | Mark Fable `suspended`, Mythos `restricted_provisioning` |
| wolfSSL CVE-2026-5194 (ECDSA digest/OID validation) | NVD, wolfSSL advisory | Add dual-source AI-discovered vulnerability tracking |
| Activation classifiers (Sol/Terra): 94.8% bio recall, 81.6% cyber recall | OpenAI system card | L0.5 logit-space distance checker (activation_proxy.py) |
| Empero Qwythos-9B/Qwable-9B distills exist, Apache-2.0, 1M ctx | huggingface + empero.org | Add local-power TWAVE lane |
| Multi-turn safety degrades exponentially (T1→T2→T3→T4) | Master Dossier §2 | Implement temporal accumulator + sleep consolidator |
| 7 Safety Theorems (phase transition, commitment layer steering, etc.) | NEXUS decision-locator experimental | Wire into guard_router.py documentation + KAIJU gates |

## New Files to Create (priority order)

### P0 — Security Hardening (from METR cheating + bypass threats)

1. **`nexus_os/security/sandbox_monitor.py`** — Process-tree monitor for agent tasks. Watches: shell=True calls, writes to hidden dirs, credential file reads, test-suite exfiltration patterns. Logs to Vault EPISODIC.

2. **`nexus_os/security/activation_proxy.py`** — L0.5 guard: intercepts primary model's last-4-layers hidden states via PyTorch forward hook, feeds tiny logistic regression classifier trained on known jailbreak manifold. If cos-dist < threshold, route to L3 bypassing L1/L2. ~200ms overhead, CPU only.

3. **`nexus_os/security/pty_jail.py`** — Ephemeral workspace wrapper: mount --bind with noexec/nodev/nosuid (Linux) or Windows Job Object equivalents. Network namespace isolation. Kills process tree on parent exit.

4. **`nexus_os/security/temporal_accumulator.py`** — Session-level RiskAccumulator (T2). Tracks: consecutive unsafe classifications, prompt reframing attempts, tool-call rate acceleration. Stored in Vault EPISODIC.

5. **`nexus_os/security/sleep_consolidator.py`** — Cross-session pattern analysis (T3). Reads yesterday's Vault EPISODIC, detects repeated attack shapes across sessions.

### P1 — Provider Architecture (for GA readiness)

6. **`nexus_os/relay/providers/__init__.py`** — Provider registry
7. **`nexus_os/relay/providers/openai_provider.py`** — GPT-5.6 family adapter (API keys, caching 90% read discount, rate limits)
8. **`nexus_os/relay/providers/anthropic_provider.py`** — Claude 5 family adapter (Fable/Mythos, 30-day retention note)
9. **`nexus_os/relay/providers/ollama_provider.py`** — Refactored from current model_relay.py
10. **`nexus_os/relay/rate_limiter.py`** — Token-bucket rate limiter per provider+model

### P1 — Governance & Evaluation

11. **`nexus_os/eval/pack/__init__.py`** + **`runner.py`** — Evaluation pack harness
12. **`nexus_os/eval/pack/test_*.py`** (12 files, one per test type from NEXUS Assessment)
13. **`nexus_os/eval/adoption/gate_*.py`** (8 files, one per adoption gate)
14. **`nexus_os/engine/sense.py`** — S-P-E-W Sense phase orchestration
15. **`nexus_os/engine/planner.py`** — S-P-E-W Plan phase orchestration
16. **`nexus_os/engine/witness.py`** — S-P-E-W Witness phase orchestration

## Existing Files to Modify

### Modified: `nexus_os/security/guard_router.py`
- Add L0.5 routing: if activation_proxy detects jailbreak manifold, skip L1/L2 → L3 directly
- Add `logit_space_check()` call before L1 inference

### Modified: `nexus_os/engine/gmr.py`
- Route decisions log `RouteRecord` (requested_model, actual_model, fallback_reason, fallback_chain, timestamp, task_id)
- T4 critic: after primary output, run Qwen3-0.6B "PASS/FAIL" check on output

### Modified: `nexus_os/governor/kaiju.py`
- Add `ACT_EVAL_CHEAT` gate: subagent claiming "all tests pass" where test files don't exist → flag fabricated evidence
- Monotonic privilege enforcement for long-running tasks

### Modified: `nexus_os/relay/model_relay.py` + `model_relay_adapter.py`
- Make `proxy_completion()` a provider-agnostic dispatcher to `relay/providers/*`
- Add model-alternating fallback: attempt primary on Node relay, on failure try fallback model on Node, then primary on God Mode, etc.
- Track cache keys for OpenAI 90% read discount (30-min TTL)

### Modified: `nexus_os/twave/chimera_router_v2.py`
- Add `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` ModelProfile entries (Tier.CLOUD)
- Add `qwythos-9b-iq4_xs`, `qwable-9b-iq4_xs` LOCAL_POWER profiles (6GB VRAM)
- Add `fallback_map: Dict[str, List[str]]` for model fallback chains

### Modified: `nexus_os/relay/intent_classifier.py`
- Add KEYWORD_MAP entries for `sol`, `terra`, `luna` explicit model hints
- Add FLAGSHIP, BUDGET intent classes

### Modified: `nexus_os/vault/archivist.py`
- Accept `RouteRecord` as first-class entry type
- Store negative evidence: blocked actions, failed attempts, evaluator-gaming signals

### Modified: `nexus_os/engine/tool_executor.py`
- Route all file-read/write tools through `pty_jail` workspace
- Agent only sees ephemeral directory; credential paths bind-mounted as empty

### Modified: `nexus_os/engine/eval_runner.py`
- Inject evaluation context noise (random benchmark/user markers, varied system prompts, filler history)

## Contamination List (must NOT enter canonical docs without explicit secondary tagging)

| Claim | Status | Reason |
|-------|--------|--------|
| 1.5M context window for GPT-5.6 | UNVERIFIED | Not in official docs; secondary speculation |
| ~10T-param "Capybara" architecture | REJECTED | No primary source support |
| Host-kernel sandbox escape by METR-evaluated models | CONTRADICTED | METR blog defines cheating narrowly as eval-environment exploitation |
| Activation classifiers designed explicitly as response to Fable | UNSUPPORTED | No causal claim in OpenAI docs |
| Fable boundary classifier exposes raw Mythos weights | UNSUPPORTED | Same model with safeguards, not separate weights |
| CVE-2026-5194 as first autonomous AI zero-day | CONTRADICTED | NVD credits Nicholas Carlini; not described as autonomous AI discovery |
| Seven safety theorems as established external results | NEXUS HYPOTHESIS | Internal, not externally validated |
| Empero model-card claims independently validated | UNVERIFIED | No independent validation found |

## Pricing Reference for Routing Decisions

| Model | Input/1M | Output/1M | Cache Read | Cache Write | TTL |
|-------|----------|-----------|------------|-------------|-----|
| GPT-5.6 Sol | $5.00 | $30.00 | 90% off | 1.25× | 30min |
| GPT-5.6 Terra | $2.50 | $15.00 | 90% off | 1.25× | 30min |
| GPT-5.6 Luna | $1.00 | $6.00 | 90% off | 1.25× | 30min |
| Claude Fable 5 | $10.00 | $50.00 | 90% off | std | std |
| Claude Mythos 5 | $10.00 | $50.00 | 90% off | std | 30-day retention |

## Proposed Fallback Chains

| Primary | Fallback 1 | Fallback 2 | Fallback 3 | Fallback 4 |
|---------|-----------|-----------|-----------|-----------|
| Sol ($30) | Terra ($15) | Luna ($6) | GPT-5.5 | Opus 4.8 |
| Terra ($15) | Luna ($6) | Qwythos-9B (local) | GPT-5.5 | - |
| Luna ($6) | Qwythos-9B (local) | Qwen3-72B | - | - |

## Grok CDP Confirmation

Grok independently verified the source-ranked claim matrix and produced a contamination ledger matching the above. Its analysis confirmed:
- CVE-2026-5194 attribution nuance (researcher credit ≠ autonomous AI discovery)
- arXiv papers (2605.11086, 2605.23243, 2606.14295, 2605.17416, 2606.18193) exact findings
- Mythos restoration as PARTIAL (Commerce letter for Annex A, not full restoration)

## Next Immediate Actions (ordered)

1. Create `sandbox_monitor.py` + `activation_proxy.py` (P0 security)
2. Modify `guard_router.py` with L0.5 logit-space check
3. Add `RouteRecord` dataclass + wire into `gmr.py` and VAP
4. Add `qwythos-9b` + `gpt-5.6-*` profiles to `chimera_router_v2.py`
5. Create `eval/pack/__init__.py` + `runner.py` with first 4 evaluation tests
6. Wire S-P-E-W phases into `engine/router.py`
