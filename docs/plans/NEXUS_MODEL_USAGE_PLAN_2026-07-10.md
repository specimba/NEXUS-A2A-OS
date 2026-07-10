# NEXUS Model Usage Plan — Distilled from NEXUSantiGRAVnexlog-11.txt (12,478 lines)

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Source** | Full read of NEXUSantiGRAVnexlog-11.txt (12,478 lines, 0% surface sweep) |
| **Purpose** | Distill the operator-defined NEXUS model architecture into an actionable usage plan |
| **Policy** | GND-001 full-coverage reads only |

## Executive Summary

The NEXUS model system is organized around a **3-tier VRAM budget** with **8GB ceiling**, designed to use **fine-tuned, uncensored, abliterated/heretic** models rather than relying on cloud-side content filters. Governance is handled by **fine-tuned small-model stacks** inside the bouncer/security/guard team. This plan distills the full antiGRAV-11 design into operational guidance.

## 1. The Canonical 3-Tier Workflow (Operator-Defined, antiGRAV-11 L2442)

```
User prompt
  ↓
[TIER 0: Anchors] FunctionGemma-270M + BashGemma-270M-merged + EmbeddingGemma
  (tool selection + refinement, ~750MB)
  ↓
[TIER 1: Guard Stack] Llama-Guard-3-1B + FunctionGemma + Gemma-3-1B
  (VATS gatekeeping, ~1GB)
  ---1GB GPU TOTAL after this point---
  ↓
[TIER 2: Rotatable Task SLMs] Mythos-nano-OBLITERATED + VibeThinker-3B
  (math/code + tool-use, 2-2.5GB)
  ---3.5GB VRAM MAX after this---
  ↓
[TIER 3: Cloud Elevation] ModelRelay → free frontier (GLM-5.2, DeepSeek-V4, Kimi-K2.7, MiniMax-M3)
  (if task needs higher reasoning/deep search)
  ↓
[FINAL CHECK] Local SLM gate re-checks output
  ↓
DONE
```

**Key principle**: Local-first always. Fugu-style multi-LLM intel distillation (Trinity 3-role + Dawid-Skene EM) on the collaborative tier.

## 2. Model Pools (Verified from antiGRAV-11)

### Tier 0: Anchors (always loaded, <800MB)
| Role | Model | Size | Quant | VRAM |
|------|-------|------|-------|------|
| Intent classification | `google/functiongemma-270m-it` | 270M | Q4_K_M | ~350MB |
| Command poison check | `potteryrage/bashgemma-270m` | 270M | Q4_K_M | ~400MB |
| Embeddings | `nomic-ai/nomic-embed-text-v1.5` | 137M | FP16 | ~80MB |

### Tier 1: Guard/Governance Stack (<1.5GB total)
| Role | Primary | Plan B |
|------|---------|--------|
| VATS Gatekeeper (Security) | `meta-llama/Llama-Guard-3-1B` (1.0B) | `meta-llama/Llama-3.2-1B-Instruct` |
| Function-call validator | `google/functiongemma-270m-it` (270M) | `huggermax/VibeThinker-3B-tool-calling-GGUF` |
| Pre-filter classifier | `Andycurrent/Gemma-3-1B-it-GLM-4.7-Flash-Heretic-Uncensored-Thinking_GGUF` (1.0B) | `Qwen/Qwen2.5-1.5B-Instruct` |
| Embedding classifier | `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (1.5B) | - |

**Total: 2.27B params / ~1.8GB VRAM at 8-bit**

### Tier 2: Rotatable Task SLMs (2-2.5GB VRAM)
| Role | Primary | Plan B |
|------|---------|--------|
| Math/Code verifier (uncensored) | `usermma/Mythos-nano-OBLITERATED` (2.5GB footprint) | - |
| Multi-turn tool-caller | `refinedneuro/refinedtoolcallv5-3b` (2.5GB Q6_K) | `huggermax/VibeThinker-3B-tool-calling-GGUF` |
| Coding specialist (3B) | `mradermacher/VibeThinker-3B-Agentic-GGUF` | `Qwen/Qwen2.5-Coder-3B-Instruct`; uncensored: `prithivMLmods/VibeThinker-3B-heretic_decensored-GGUF` |
| Heavy coding (12B if full VRAM) | `yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF` (Q4_K_M = 6.87GB) | `huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF` (9B) |

**Total local rotatable: ~5.0GB peak when 12B loaded, ~1.5GB when 3B only**

### Tier 3: Cloud Elevation (via ModelRelay TIER_PRIMARY)
| Provider | Model | Context | Notes |
|----------|-------|---------|-------|
| kilocode | `z-ai/glm-5.2` | 1M | Free reasoning primary |
| baseten | `zai-org/GLM-5.2` | 131k | Backup |
| kilocode | `nvidia/nemotron-3-ultra-550b-a55b:free` | 1M | 550B MoE |
| nim | `nvidia/nemotron-3-ultra-550b-a55b` | 1M | 8 RPM, 70s cooldown, 95s timeout |
| opencode | `deepseek-v4-flash-free` | 1M | Fast tier |
| opencode | `north-mini-code-free` | 32k | 0.7s latency |
| kilocode | `minimax/minimax-m3` | 512K | Serial-only on NIM |
| nim | `minimaxai/minimax-m3` | 512K | Hangs intermittently — avoid |
| nim | `qwen/qwen3.5-122b-a10b` | 122K | NIM-only |
| kilocode | `moonshotai/kimi-k2.7-code` | 262K | Code specialist |

### Guard Cascade (Production L0-L3)
| Tier | Model | Size | License |
|------|-------|------|---------|
| L1 (WalledGuard-Edge) | `walledai/walledguard-edge` | 0.60B | apache-2.0 |
| L2 (Llama-Guard) | `meta-llama/Llama-Guard-3-1B` | 1.50B | llama3.2 |
| L3 (Granite confirmer) | `ibm-granite/granite-guardian-3.2-3b-a800m` | 3.30B | apache-2.0 |

## 3. Model Architecture Decisions (antiGRAV-11 L4001-6000)

### What was corrected during research
1. **35B local was WRONG** — 35B at Q4_K_M = ~20GB, forces 12GB weights to spill to system RAM, PCIe bottleneck drops to <1 tok/s. **Decision**: 35B models = **Cloud-Only A2A lane only** (CyberStrike-OffSec-35B, InternScience/Agents-A1, Ornith-1.0-35B-AEON).
2. **Mythos-nano base was WRONG** — base model has refusal overhead. **Decision**: Use `usermma/Mythos-nano-OBLITERATED` (heretic abliteration via OBLITERATUS by elder-plinius). Safety handled by bouncer team BEFORE prompt reaches generator.
3. **VibeThinker-3B is for math/code verification, NOT autonomous agent** — model card explicitly says NOT trained for tool-calling. **Decision**: Use `refinedneuro/refinedtoolcallv5-3b` for multi-turn tool calling instead.
4. **GMR strategy = ChimeraRouter + ModelRelay** — Chimera = strategy, ModelRelay = execution. L3 ensemble: VibeThinker-3B, Nanbeige4.1-3B, fugu.

## 4. VibeThinker-3B Family (Verified Picks)

### For local coding (3B class)
| Model | Use Case | Notes |
|-------|----------|-------|
| `mradermacher/VibeThinker-3B-Agentic-GGUF` | Primary coding | VibeThinker fine-tune with agentic focus |
| `prithivMLmods/VibeThinker-3B-heretic_decensored-GGUF` | Uncensored coding | Heretic abliterated |
| `mradermacher/VibeThinker-3B-OBLITERATED-i1-GGUF` | OBLITERATED (max removed filters) | elder-plinius OBLITERATUS method |
| `RefinedNeuro/VibeThinker-3B-Hermes-GGUF` | Hermes function calling | Adds tool-use to VibeThinker base |

## 5. Cloud Tier Rotation (persistent_router.py)

### TIER_PRIMARY (8 models, alternate_on_quota_or_rate_limit)
1. `kilocode/z-ai/glm-5.2` (free reasoning, 1M ctx)
2. `baseten/zai-org/GLM-5.2`
3. `kilocode/nvidia/nemotron-3-ultra-550b-a55b:free` (free 550B, 1M ctx)
4. `nim/nvidia/nemotron-3-ultra-550b-a55b`
5. `opencode/deepseek-v4-flash-free`
6. `kilocode/minimax/minimax-m3`
7. `nim/minimaxai/minimax-m3`
8. `nim/qwen/qwen3.5-122b-a10b`

### TIER_FALLBACK (logging/memory consistency)
- `longcat/LongCat-2.0` (1M ctx, 128K output)
- `internai/intern-s2-preview` (256K ctx, thinking_mode)

### TIER_SPECIALIST (code/SWE/agentic)
- `opencode/deepseek-v4-flash-free` (85% intell, 1.4s)
- `opencode/north-mini-code-free` (0.7s)
- `kilocode/nvidia/nemotron-3-super-120b-a12b:free`
- `ollama-cloud/qwen3-coder:480b`
- `ollama-cloud/devstral-small-2:24b`
- `baseten/moonshotai/Kimi-K2.7-Code` (262k ctx, $0.40/M)

## 6. Guard Stack (L0-L4 Cascade)

### GMR Security Stack (model_rotator.py)
| Tier | Model | Size | VRAM |
|------|-------|------|------|
| L0 | BashGemma 270M (bashgemma-270m-merged) | 270M | ~400MB |
| L1 | FunctionGemma 270M (functiongemma:latest) | 270M | ~350MB |
| L2 | GLiGuard-300M | 300M | ~500MB |
| L3 | arch-guard-300m | 300M | ~600MB |
| L4 | Meta-attack detector (regex, 46 categories) | 0 | 0MB |
| Heavy | gemma4-e2b-guard (Option A) | 2.3B | 1800MB |
| Heavy | gemma2-2b-abliterated | 2.0B | 1400MB |

**Total L0+L1: 750MB; Peak with L2: 1350MB**

### MCP Guard Options (mcp/guard_eval.py)
- **Option A**: Gemma4-E2B (2.3B combined guard+function)
- **Option B**: BERT-tiny (~15MB) + FunctionGemma — `mrm8488/bert-tiny-ft-prompt-injection`
- **Option C**: Llama Prompt Guard 2 86M + FunctionGemma (GATED) — `meta-llama/Llama-Prompt-Guard-2-86M`
- **Option D**: ShieldGemma 2B Q4 + FunctionGemma (GATED) — `google/shieldgemma-2b`

## 7. Embedding Model Selections (Top 10 by downloads)

| Model | Downloads | Size | License |
|-------|-----------|------|---------|
| `nomic-ai/nomic-embed-text-v1.5` | 15.8M | 137M | apache-2.0 |
| `Qwen/Qwen3-Embedding-0.6B` | 10.6M | 600M | - |
| `BAAI/bge-small-en-v1.5` | 62.9M | 33M | mit |
| `jinaai/jina-embeddings-v3` | 2.8M | 570M | cc-by-nc-4.0 |
| `google/embeddinggemma-300m` | 1.6M | 300M | apache-2.0 |
| `Qwen/Qwen3-Embedding-4B` | 2.6M | 4B | - |
| `Qwen/Qwen3-Embedding-8B` | 2.7M | 8B | - |

## 8. Critical Findings and Fixes Applied

### GLM-5.2 Invisibility Bug (FIXED, antiGRAV-11 L6162)
**Root cause**: Python Relay `/v1/models` returned only hardcoded `["minimax-m3:cloud", "minimax-m2.7", *OLLAMA_CLOUD_MODELS]`. `OLLAMA_CLOUD_MODELS` only contained 3 entries.
**Fix**: Inject `baseUrl` for `opencode` and `kilocode` in `config/models.registry.json`; regenerate artifacts; update `/v1/models` and `/api/models` to consume dynamic `ALL_ACTIVE_CLOUD_MODELS`.

### Cloud Health Check Bug (P0, antiGRAV-11 L8208)
**Bug**: `model_relay.py:_check_health()` POSTs to local Ollama:11434 for ALL model names. Cloud-only models like `minimax-m3:cloud` always return 404.
**Fix pending**: Must use provider-specific health check endpoints.

### NIM Rate Limit Cascade (FIXED, antiGRAV-11 L6045)
**Root cause**: MiniMax-M3 on NIM has slow KV-cache warm-up (38s first, 60s+ subsequent). 8 RPM budget burned.
**Fix applied**: `NIM_HEAVY_COOLDOWN = 70s`, `HEAVY_PROBE_TIMEOUT = 95s`, serial-only. Kimi-K2.6 tool-calling bug noted (don't route tools there).

## 9. Registry Schema v3 (current canonical)

Registry v3 features (per antiGRAV-11 L6063-6104):
- Per-provider `quota` (windows rps/rpm/rph/rpd, tokens, metering, credit, confidence HIGH/MEDIUM/LOW/CONFLICTED, degradation class)
- `outputLicense` (permissive|restricted|unknown)
- `providerQuirks` (kind enum: tool_calling_broken, silent_degradation, dollar_then_dead, no_free_tier, dynamic_throttle, intermittent_hang, silent_rename)
- `allowedLanes`

## 10. Action Items (Synthesized)

### P0 — Immediate
1. **Apply DPO judge fix** — `gen_guard_dpo_pairs.py` still references `intern-s2-preview`; replace with `deepseek-v4-pro` (NIM)
2. **Fix cloud health check** — `_check_health` POSTs to local Ollama for cloud models (always 404)
3. **Adopt llama-server router mode** — replaces Ollama reinstall blocker
4. **Apply registry v3 to all CLIs** — opencode, kilo, cline, hermes, mimo all need to consume v3 schema

### P1 — Core
5. **Build Stack v0** — 3.5B pinned anchors + 1.5B guard + 3B rotatable; wire to ChimeraRouter
6. **Implement Owl-Alpha prefix rule** — promote unknown vendor prefixes to candidates
7. **Wire ProviderRefresher to `_start_health_loop`** — 3600s daemon thread with `chat_probe=False`
8. **Update TIER_PRIMARY** — already done in log; verify in code

### P2 — Polish
9. **Replace GMR security L0-L3** with <1B specialized fine-tunes per `ernie_IBM_1B_fallback_matrix.txt`
10. **Add DFlash block diffusion** to MTP-capable slots (Qwen3.5 class, 1.4-2.2x dense)
11. **Build Trial Needle-26M as intent anchor** (MIT license, frees ~250MB pinned budget)

## 11. Model-File Quick Reference

| File | Purpose | Status |
|------|---------|--------|
| `config/models.registry.json` | Canonical registry (v3) | LIVE |
| `scripts/gen_model_registry.py` | Generator | ACTIVE |
| `nexus_os/gmr/chimera_router_v2.py` | ChimeraRouter (strategy) | LIVE |
| `nexus_os/model_relay/persistent_router.py` | TIER_* rotation | LIVE |
| `nexus_os/model_relay/peer_review.py` | LLM-PeerReview (Dawid-Skene EM) | LIVE |
| `nexus_os/gmr/tandem_routing.py` | Tandem rider (high-cap → local SLM) | LIVE |
| `nexus_os/gmr/coger.py` | CogER (Elastic Reasoning L1-L4) | LIVE |
| `nexus_os/nexusclaw/trinity_fugu_workflow.py` | Trinity 3-role + Fugu soft-target | LIVE |
| `nexus_os/nexusclaw/agent_pool.py` | Worker pool | LIVE |
| `nexus_os/governor/trust_kernel.py` | 11-element trust | LIVE |
| `nexus_os/security/guard_router.py` | L0-L4 guard cascade | LIVE |
| `docs/coordination/ARCHIVIST_MODELS_API_DIGEST_2026-06-20.md` | Source of truth for model inventory | LIVE |
| `docs/plans/NEXUS_MILESTONES_2026-H2.md` | M0-M6 roadmap | LIVE |
| `docs/plans/NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md` | 3.5B cascade + bouncer | OPERATOR-APPROVAL-PENDING |

## 12. References

- `NEXUSantiGRAVnexlog-11.txt` lines 1-12478 (FULL READ per GND-001)
- `NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md` — sibling plan
- `NEXUS_UPGRADED_PLAN_2026-07-08.md` — master plan
- `NEXUS_MILESTONES_2026-H2.md` — M0-M6 roadmap
- `docs/coordination/ARCHIVIST_MODELS_API_DIGEST_2026-06-20.md` — model inventory
- `docs/policies/GND-001_24h_deep_grounding.md` — full-coverage reading policy
