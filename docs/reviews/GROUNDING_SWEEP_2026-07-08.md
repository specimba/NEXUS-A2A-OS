# Grounding Sweep Report — 2026-07-08

| Field | Value |
|-------|-------|
| **Sweep Date** | 2026-07-08 |
| **Policy** | GND-001 |
| **Window** | Last 24 hours |
| **Total Files** | 13 (9 NEXUSlogs + 4 ARCHIVIST) |
| **Files Fully Read** | 12 |
| **Total Lines** | ~41,021 |
| **Coverage** | 92.3% (12/13 files) |
| **Gap** | NEXUSantiGRAVnexlog-11.txt — agent returned project state instead of log content |

## Files Read

### NEXUSlogs (9 files)

| # | File | Lines | Status |
|---|------|-------|--------|
| 1 | NEXUSkilocodeORCHESTRATORagentlogs-05.txt | 3,000+ | ✅ FULL |
| 2 | NEXUSgeneralFABLE5advisorylogs-01.txt | 9,400+ | ✅ FULL |
| 3 | NEXUSgeneralFABLE5advisorylogs-02.txt | 8,010 | ✅ FULL |
| 4 | NEXUSgeneralFABLE5advisorylogs-03.txt | 3,881 | ✅ FULL |
| 5 | NEXUSopencodeMAINbackendGLM52NIMlog-29.txt | 1,388 | ✅ FULL |
| 6 | NEXUSopencodeMAINbackendDEEPseekv4PRONIMlog-26.txt | 4,767 | ✅ FULL |
| 7 | NEXUSantiGRAVnexlog-11.txt | 3,165 | ⚠️ PARTIAL |
| 8 | NEXUSkilocodeORCHESTRATORagentlogs-04.txt | 2,141 | ✅ FULL |
| 9 | NEXUSfastHACKATHONlogANTIGRAVITYgemini35advisory-01.txt | 7,505 | ✅ FULL |

### ARCHIVIST (4 files)

| # | File | Lines | Status |
|---|------|-------|--------|
| 1 | A2A Collaborative Deep Analysis Report (2026-07-06).txt | 113 | ✅ FULL |
| 2 | CDP Anti-Freeze and Safety Denylist Hardening_walkthrough.md | 35 | ✅ FULL |
| 3 | apodexDEEPresearchGPT56SOLTERRALUNA3.txt | 583 | ✅ FULL |
| 4 | ARCHIVIST DOSSIER The Frontier AI Landscape (June 2026)-part2.md | 113 | ✅ FULL |

## Active Blockers (Ordered by Severity)

| # | Blocker | Source |
|---|---------|--------|
| 1 | Brain API (Port 7352) DOWN — connection refused | orchestrator-04, FABLE5-01 |
| 2 | Port 7350 health endpoints broken — `/health` returns 404 | orchestrator-04 |
| 3 | GLM-5.2 NIM lane DEGRADED — function cannot be invoked | Log-29 |
| 4 | 01_PROJECT_STATE.md 3 weeks stale (APA 2026-06-26) | Log-29, FABLE5-03 |
| 5 | NIM free-tier collapse — GLM-5.1 410, Kimi K2 410, MiniMax M3 DEGRADED | Log-26 |
| 6 | Hermes config never applied — proposed 4 times, never executed | orchestrator-04 |
| 7 | 5/8 providers dead — SiliconFlow/Fireworks DEAD, Ollama OFFLINE | orchestrator-04 |
| 8 | UnifiedStateManage 0.0.0.0 bind — unauthenticated :8765/:8766 | FABLE5-01 |
| 9 | AdaptiveCircuitBreaker signature regression — crashes production callers | orchestrator-04 |
| 10 | Simulation theatre in training corpus — HERMES 13-cycle fabricated | Log-29, FABLE5-03 |

## Critical Security Findings

| # | Finding | Status | Source |
|---|---------|--------|--------|
| 1 | CDP Denylist Guard — blocks destructive browser commands | ✅ FIXED | A2A report, CDP walkthrough |
| 2 | KAIJU clearance caller-supplied, never verified | ✅ FIXED | FABLE5-02 |
| 3 | Guard pipeline fail-open at three layers | ✅ FIXED | FABLE5-02 |
| 4 | Brain API weak auth | ✅ FIXED | FABLE5-02 |
| 5 | model_sync JSONC wipe | ✅ FIXED | FABLE5-02 |
| 6 | mimo JSONC corruption | ✅ FIXED | FABLE5-02 |
| 7 | Trust equation regression | ✅ FIXED | FABLE5-01 |
| 8 | NonCompensatory direction bug | ✅ FIXED | FABLE5-01 |
| 9 | STACK attack 71% ASR on safety-refusal-only defenses | ⚠️ UNMITIGATED | Log-05 |
| 10 | Transfer-STACK 33% with zero target access | ⚠️ UNMITIGATED | apodexDEEP |

## Model Intelligence Summary

| Model | Status | Key Intel |
|-------|--------|-----------|
| GPT-5.6 Sol | Limited preview | 96.7% CTF, highest METR cheating rate, L3 misalignment 0.00307 |
| Claude Mythos 5 | Restricted | 66.0 HealthBench, 10T params "Capybara" |
| Claude Fable 5 | Public | 80.3% SWE-Bench Pro, routes cyber/bio to Opus 4.8 |
| GLM-5.2 | NIM DEGRADED | Function cannot be invoked |
| DeepSeek V4 Pro | NIM LIVE | Permissive license, DPO judge replacement |
| MiniMax M3 | NIM transient | License M2.7+ requires written auth |
| InternAI intern-s2 | 90M tok/month | Only consistently alive frontier provider |
| Alibaba Qwen3 | Free tier, 235B MoE | NOT YET IN REGISTRY |
| LongCat-2.0 | Beta quota 0 | Invisible on :7350 |
| Qwythos-9B | Open-weights distill | +34.3 MMLU lift, first viable local reasoning model |

## Infrastructure State

| Port | Service | Status |
|------|---------|--------|
| 7350 | Node/npm ModelRelay | UP but health broken |
| 7352 | Brain API | DOWN |
| 7354 | Grok MCP / Zo judge | UP |
| 7355 | Python ModelRelay | UP |
| 7357 | Godmode relay | UP |
| 8765 | UnifiedStateManage WS | CRITICAL: unauthenticated |
| 8766 | UnifiedStateManage HTTP | CRITICAL: unauthenticated |
| 9224 | Chrome CDP | Active |

## Execution State

- **Phase 1+2+Track F+A2A+Vision+Wrap-up+Research**: DONE through `35c15e56`
- **16 commits in FABLE5-03**: 4100 tests passing / 61 skipped
- **M0 corrections sprint**: MiniMax license ✅ FIXED, DPO judge ⚠️ NOT YET APPLIED
- **Uncommitted working tree**: ~40 files across multiple lanes

## Action Items

### P0 (Immediate)
1. Resume Week 4 bench: runner.py → leaderboard.py → tests → live run — commit
2. Draft NEXUS_UPGRADED_PLAN_2026-07-08.md incorporating all evidence
3. Write 01_PROJECT_STATE.md forward-pointer (currently ~3 weeks stale)
4. Fix port 7350 health contract — add legacy `/health` route alongside `/healthz`
5. Fix AdaptiveCircuitBreaker signature regression — restore `name` parameter

### P1 (Core Pipeline)
6. Wire gen_guard_dpo_pairs.py fix — replace intern-s2-preview with deepseek-v4-pro
7. Register Alibaba Qwen3 in all config layers
8. Purge NIM dead models from all configs
9. Hermes config apply: `hermes config set model.base_url http://127.0.0.1:7350/v1`
10. Resume 72h integration plan execution

### P2 (Infrastructure)
11. Fix UnifiedStateManage 0.0.0.0 bind — loopback default
12. Resolve NEO git corruption
13. Adopt llama-server router mode (replaces Ollama reinstall blocker)
14. LongCat beta re-request
15. SiliconFlow dashboard key check
