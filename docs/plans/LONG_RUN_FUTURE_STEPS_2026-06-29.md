# NEXUS OS — Long-Run Future Steps (2026-06-29)

Grounded from: 01_PROJECT_STATE.md, knowledge.md, ARCHIVIST reports (GPT56_FABLE_MYTHOS_NEXUS_ASSESSMENT, NEXUS_FRONTIER_INTEGRATION_v1), NEXUSlogs (log-26, HERMES-05, antigrav-10), siliconflowMODELguideSHORT.txt, .modelrelay.json, and live provider verification.

---

## PHASE 7: ModelRelay Resilience (Week 1-2)

### 7.1 Provider Health Circuit Breaker [P0]
**Problem:** Router retries 412/429/timeout providers 6 times before failover. No cooldown, no degraded-state partitioning. 15+ second latency spikes on dead providers.
**Evidence:** `NEXUS_model_RELAY_router_logs-01.txt` — Fireworks=412, DeepInfra=timeout, Ollama=ECONNREFUSED. Router just loops.
**Actions:**
1. Create `nexus_os/relay/circuit_breaker.py` — per-provider state machine: CLOSED→OPEN→HALF_OPEN
   - OPEN after 3 consecutive failures (412/429/timeout)
   - HALF_OPEN after configurable cooldown (default 60s)
   - ONE probe request in HALF_OPEN; success→CLOSED, fail→OPEN
   - Integrate into `model_relay_adapter.py` and `god_mode_proxy.py`
2. Create `nexus_os/relay/rate_limiter.py` — token-bucket per provider+model
   - NVIDIA NIM: 40 RPM free tier
   - SiliconFlow: per-model TPM tracking
   - OpenRouter: :free suffix quota tracking
3. Wire into ModelRelay Node (7350) — add `/health/providers` endpoint returning breaker state
4. Tests: 15+ circuit breaker state machine tests

### 7.2 SiliconFlow Full Integration [P0, DONE partially]
**Status:** Key rotated, LIVE, opencode.json + .modelrelay.json updated, model_sync.py updated.
**Remaining:**
1. Wire SiliconFlow into Node ModelRelay (7350) as first-class provider
   - Add to `modelrelay` npm config with new key
   - Add model list: GLM-5, GLM-5.1, DeepSeek V4 Flash/Pro, MiniMax M2.5/M2.1, Qwen3 235B, Kimi K2.6
   - Set `enable_thinking` per-model for SiliconFlow reasoning models
2. Add SiliconFlow as ChimeraRouterV2 lane (profile: `god-code-sf`, `god-reason-sf`)
3. Verify thinking config format: SiliconFlow uses `enable_thinking: true` + `thinking_budget: N`; NVIDIA NIM uses Anthropic-style `thinking: {type: "enabled", budget_tokens: N}`; NIM also works WITHOUT thinking params (auto-enables for thinking models)
4. Stress test: run 10 completion calls across 5 SiliconFlow models, measure latency + quota

### 7.3 NVIDIA NIM Quota Awareness [P1]
**Problem:** Free tier is 40 RPM. No tracking → 429 errors that cascade. Two distinct failure modes discovered live (2026-06-29):
1. **429 Rate-limit throttling** — bursty multi-agent dispatches saturate 40 RPM window during peak hours. Router retries 6× before failover → 27s latency spikes.
2. **202,752 token context limit (GLM 5.1)** — `ValueError: Requested token count exceeds the model's maximum context length of 202752 tokens.` Happens when compaction already ran (reducing input to ~173K) but completion budget (32K) pushes total over. The model rejects the entire request with zero retry intelligence.
**Actions:**
1. Create `nexus_os/relay/quota_tracker.py` — per-provider quota state
   - NVIDIA NIM window: sliding 60s, max 40 requests
   - Proactive backoff at 80% utilization (32/40)
   - Log to Vault EPISODIC + monitoring TokenGuard
2. Add `X-RateLimit-Remaining` header parsing from NIM responses
3. Integrate with circuit breaker: 429 → increment counter, 3×429 in 5min → OPEN circuit
4. **Context limit guard** — token-count check BEFORE dispatch:
   - Track max_context per NIM model: GLM-5.1=202,752, MiniMax-M3=524,288 (512K), Kimi-K2=262,144, Devstral-2=131,072
   - If total_tokens (input + completion_budget) > max_context: auto-reduce completion budget to fit, OR fail over to a higher-context model (e.g. MiniMax M3 with 512K)
   - Never retry same model after context-limit rejection — immediate failover
5. **Multi-agent dispatch discipline** — when running parallel agents on NIM:
   - Cap concurrent NIM requests at 2 (never 3+ parallel subagent calls)
   - Stagger dispatch by 3s between NIM-bound calls to avoid burst 429
   - Prefer SiliconFlow/OpenRouter for parallel reads; reserve NIM for single critical synthesis calls

### 7.4 Model Name Normalization [P2]
**Problem:** Same model has 5+ names: `minimax-m3` / `minimaxai/minimax-m3` / `nvidia/minimax-m3` / `MiniMaxAI/MiniMax-M3` etc.
**Actions:**
1. Create `nexus_os/relay/model_aliases.py` — canonical name registry
2. Normalize all names to `provider/canonical-name` (e.g. `siliconflow/glm-5`, `nim/minimax-m3`)
3. Add alias resolution in God Mode Proxy and ChimeraRouterV2
4. Ensure model_sync.py output uses canonical names

---

## PHASE 8: Guard Pipeline Enhancement (Week 2-3)

### 8.1 MCP Gateway Pipeline [P0, from knowledge.md gap #1]
**Problem:** BrowserHTTPDiagnosticRelay and MetaAttackDetector exist independently but are NOT wired together. MCP attacks undetected until after execution.
**Actions:**
1. Create `nexus_os/security/mcp_gateway.py` — pre-deploy MCP server scanning
   - Tool description hash + schema validation
   - Wire `execute_governed()` output to MetaAttackDetector
   - Import attack patterns from `mcp_attack_master_v5.csv`
2. Add runtime monitoring hook: feed CDP/bridge decisions to detector
3. Add `nexusctl doctor --mcp-gateway` status report
4. Tests: 20+ gateway + pattern ingestion tests

### 8.2 Temporal Defenses Completion [P1]
**Already partially done:** ALSB (T4) and CSI (T2) implemented per AGENTS.md.
**Remaining:**
1. `nexus_os/security/temporal_accumulator.py` — T2 session-level risk accumulation
   - Track consecutive unsafe classifications, prompt reframing attempts
   - Stored in Vault EPISODIC
2. `nexus_os/security/sleep_consolidator.py` — T3 cross-session pattern analysis
   - Read previous Vault EPISODIC, detect repeated attack shapes
3. Wire both into guard_router.py after L0/L1/L2/L3 cascade
4. Full test coverage

### 8.3 Evaluator Integrity [P1, from METR Sol findings]
**Problem:** GPT-5.6 Sol shows highest-ever METR cheating rate. Subagents claim "all tests pass" where test files don't exist.
**Actions:**
1. Add `ACT_EVAL_CHEAT` gate to KAIJU — flag fabricated evidence claims
2. Require file-existence proof for "tests pass" claims in agent handoff
3. Independent result verification: T4 critic run cheap model "PASS/FAIL" on primary output
4. Monotonic privilege enforcement for long-running tasks (Progent)

---

## PHASE 9: Provider Architecture GA (Week 3-4)

### 9.1 Provider Registry Refactor [P1]
**Current:** All provider config in single `.modelrelay.json` flat structure.
**Target:** `nexus_os/relay/providers/` with per-provider modules.
**Actions:**
1. `nexus_os/relay/providers/__init__.py` — provider registry base
2. `nexus_os/relay/providers/nvidia_provider.py` — NIM-specific: 40 RPM quota, thinking auto-enable
3. `nexus_os/relay/providers/siliconflow_provider.py` — SF-specific: enable_thinking support
4. `nexus_os/relay/providers/openrouter_provider.py` — :free suffix handling, fusion routing
5. `nexus_os/relay/providers/anthropic_provider.py` — Fable/Mythos identity recording
6. `nexus_os/relay/providers/ollama_provider.py` — refactor from current model_relay.py

### 9.2 VAP Route Provenance [P1, from Claude 5 identity concerns]
**Problem:** Safety routing can silently change executing model. Requested model ≠ actual executor.
**Actions:**
1. Every route decision logs `RouteRecord` (requested_model, actual_model, fallback_reason, fallback_chain, timestamp, task_id)
2. Store as first-class Vault EPISODIC entry
3. Negative evidence: blocked actions, failed attempts, evaluator-gaming signals
4. Wire into Brain API `/api/route-history` endpoint

### 9.3 Cache Economics [P2]
**Evidence:** OpenAI 90% read discount on cached prompts, 30-min minimum TTL.
**Actions:**
1. Track cache keys in ModelRelay for cost optimization
2. Prefer cached routes when available (cache-aware routing in GMR)
3. Not priority until we have pay-per-use providers

---

## PHASE 10: Evaluation Infrastructure (Week 4-5)

### 10.1 Evaluation Pack Harness [P1]
**Actions:**
1. `nexus_os/eval/pack/runner.py` — standardized test harness
2. 12 test type modules (one per benchmark category from NEXUS Assessment)
3. 8 adoption gate modules (per NEXUS frontier integration doc)
4. Version all: prompts, tools, budgets, hints, targets, harnesses with every score

### 10.2 STRES7: Frontier Model Stress Suite [P2]
**Scope:** Add GPT-5.6 Sol/Terra/Luna and Claude Fable/Mythos attack templates
**Actions:**
1. Evidence-only registry cards (no executable provider routes)
2. New attack templates for: activation classifier evasion, evaluator gaming, safety routing manipulation
3. Integrate into benchmarks/regenerate_frontier_v5.py

---

## PHASE 11: Engine S-P-E-W Orchestration (Week 5-6)

### 11.1 Four-Phase Engine [P2]
**Current:** Engine runs single dispatch. No structured phases.
**Target:** SENSE → PLAN → EXECUTE → WITNESS cycle.
**Actions:**
1. `nexus_os/engine/sense.py` — context gathering, grounding scan
2. `nexus_os/engine/planner.py` — task decomposition, model selection
3. `nexus_os/engine/executor.py` — bounded execution with monotonic privilege
4. `nexus_os/engine/witness.py` — result verification, VAP proof, cross-check

### 11.2 FlowSearch DAG [P2, from Core Gaps v4.2]
**Problem:** No directed-graph task execution. Sakana/Fugu demonstrates this pattern.
**Actions:**
1. `nexus_os/engine/dag.py` — DAG task graph with dependency tracking
2. `nexus_os/engine/scheduler.py` — topological sort + parallel execution
3. Integrate with NEXUSCLAW Orchestrator's existing task dispatch

---

## PHASE 12: Memory Consolidation (Week 6-7)

### 12.1 Dream Consolidation [P0, from knowledge.md gap #3]
**Problem:** 8-channel Vault has sleep/dream cycle stub. CODEX-15 proved fragmentation.
**Actions:**
1. Implement `vault/dream_cycle.py` — overnight consolidation pass
   - Read EPISODIC + SENSORY + WORKING from past 24h
   - Extract patterns → SEMANTIC (long-term knowledge)
   - Decay low-value entries (trust decay, relevance decay)
   - Compress duplicate memories (same event across channels)
2. Trigger on `nexusctl dream` or scheduled task (3 AM daily)
3. Write consolidation report to TASK + META channels

### 12.2 Trust Unification [P1, from knowledge.md gap #6]
**Problem:** `trust_formulas.py` uses [-1,1] scale, `vault/trust.py` uses [0,1]. Inconsistent routing.
**Actions:**
1. Normalize to [0,1] scale internally (display as 0-100)
2. `trust_formulas.py` — convert all outputs to [0,1] before storage
3. Add trust score audit: record every trust change with delta + reason
4. 30+ trust unification tests

---

## IMMEDIATE NEXT SESSION PRIORITIES

1. **SiliconFlow into Node ModelRelay (7350)** — Add provider config with new key + model list
2. **Circuit breaker skeleton** — `nexus_os/relay/circuit_breaker.py` with CLOSED/OPEN/HALF_OPEN states
3. **NVIDIA NIM quota tracker** — `nexus_os/relay/quota_tracker.py` with 40 RPM window
4. **Verify CDP silent mode persists** — Run supervisor, confirm window stays off-screen after director
5. **Run full test suite** — Confirm 833+ tests still pass after model_sync changes

---

## RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| NVIDIA NIM free tier ends | Medium | High — lose GLM-5.1 + M3 | SiliconFlow as backup; Ollama Cloud for M3 |
| SiliconFlow key expires (like old one) | Medium | Medium — lose 12 free models | Track key age; rotate before expiry |
| 429 cascade on NIM during peak hours | High | Medium — 15s+ latencies | Circuit breaker + quota tracker + proactive backoff |
| GPT-5.6 evaluator gaming in NEXUS agents | Low | High — false "done" claims | ACT_EVAL_CHEAT gate, file-existence proof, T4 critic |
| Fable 5 remains suspended | High | Low — no direct Anthropic route | Use OpenRouter/Fireworks proxies if restored |
| Chrome CDP window steals focus (regression) | Medium | Low — annoying | Post-director re-hide + hide_chrome_window.mjs |

---

## PROVIDER STATUS SNAPSHOT (2026-06-29)

| Provider | Status | Key Freshness | Rate Limit | Notes |
|----------|--------|--------------|-----------|-------|
| NVIDIA NIM | LIVE | Rotated 2026-06-22 | 40 RPM free | 429 during peak; thinking auto-enabled for M3 |
| SiliconFlow | LIVE | Rotated 2026-06-28 | TPM per model | Was DEAD (403); new key from archivist works |
| OpenRouter | LIVE | Stable | :free models unlimited | 341+ models; fusion for high-stakes |
| Groq | LIVE | Stable | 30 RPM free | Ultra-fast (236ms) |
| Cloudflare | LIVE | Stable | Moderate | @cf/zai-org/glm-4.7-flash |
| Ollama Cloud | LIVE | Stable | Per-model | 20 models; some paywalled (GLM-5.x) |
| InternAI | LIVE | Stable | 30 RPM, 300K TPM | 90M tokens/month |
| LongCat | ACTIVE_5M | Stable | Daily quota slots | 560B MoE, teacher/eval only |
| Baseten | DEGRADED | Stable | 120 RPM | GLM-5.2 was #1; key may expire |
| Fireworks | DEAD | — | — | 412 PRECONDITION_FAILED |
| DeepInfra | DEAD | — | — | 402 Payment Required |
| Novita | ZERO_BALANCE | — | — | 403 not enough balance |
