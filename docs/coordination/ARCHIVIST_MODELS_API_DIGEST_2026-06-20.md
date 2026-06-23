# ARCHIVIST Models & API Curation Digest — 2026-06-20

**Status:** Evidence-only curation from `C:\Users\speci.000\Downloads\ARCHIVIST\`
**Source files inspected:**
- `1706fancyMODELS.txt` — 4.2 KB, 167 lines.
- `2006fancyMODELSandNewPaPeRs.txt` — 14.7 KB, 446 lines.
**Reader:** NEXUS remains canonical; all listed items are evidence candidates, not approved imports.

---

## Section A — Ready-to-Use API Platforms (Verified)

### A.1 LongCat API (Meituan / Meituan-LongCat)

| Item | Verified Detail | Source line |
|------|------------------|--------------|
| Provider | `meituan-longcat` (HuggingFace org + GitHub org + product chat at https://longcat.chat/) | `2006…txt:51-59` |
| Base URL (OpenAI format) | `https://api.longcat.chat/openai/v1` | `2006…txt:157` |
| Base URL (Anthropic format) | `https://api.longcat.chat/anthropic` | `2006…txt:355` |
| Authentication | HTTP `Authorization: Bearer YOUR_API_KEY` | `2006…txt:283` |
| Active model | `LongCat-2.0-Preview` (dual OpenAI / Anthropic endpoint) | `2006…txt:79,144,239` |
| Context window | outputs up to **128k tokens** | `2006…txt:316` |
| Quota policy | Beta only; paid recharge "not currently available" | `2006…txt:78-87,279` |
| Slot release windows (UTC) | 01:00, 07:00, 13:00, 15:00 UTC (Phase 2 Beta); legacy slots at 09:00/21:00 UTC+8 | `2006…txt:75,98-102` |
| Retired models (effective 2026-05-29) | LongCat-Flash-Chat, LongCat-Flash-Thinking, LongCat-Flash-Thinking-2601, LongCat-Flash-Lite, LongCat-Flash-Omni-2603, LongCat-Flash-Chat-2602-Exp | `2006…txt:75,76` |
| Code provisioning examples | Codex TOML, OpenCode JSON config, OpenAI/Anthropic SDK with custom `base_url` | `2006…txt:128-235,344-358` |
| Exposed API key (treated UNVERIFIED) | `ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J` | `2006…txt:115-116` |

**NEXUS integration touchpoints (read-only references, no code edits executed):**

| To integrate | Reference |
|---|---|
| Add provider stub | `NEXUS\nexus_os\gmr\pool_config.py` |
| Add model entry | `NEXUS\nexus_os\models\registry.py` |
| Proxy via ModelRelay | `NEXUS\nexus_os\brain_api.py` lines 86-99 (primary 7350 / fallback 7355 sequence) |
| Authenticate request | Path C VAP record + KAIJU evaluation |

**Security notes:**
- The `ak_2N…bH8J` key is in plain text inside an ARCHIVIST file. Treat as a leaked artifact until the operator confirms ownership and rotation.
- Do **not** ship the key as a default; gate registration on user-provided env var (`LONGCAT_API_KEY`).

---

### A.2 Other API Surfaces Identified

| Platform | Endpoint / Pattern | Source line | Notes |
|---|---|---|---|
| Codex CLI | npm package `@openai/codex`, Node ≥ v18 | `2006…txt:128-138` | Documented as a deployment path for LongCat, not a hosted API. |
| OpenCode | `opencode.ai`, npm `opencode-ai`, JSON provider entry | `2006…txt:178-235` | Compatible with Many models, including LongCat. |

---

## Section B — Models by Class

### B.1 General Reasoning / Distillation

| Model | Size | Origin | Source line | Evidence grade proposal |
|-------|------|--------|--------------|--------------------------|
| VibeThinker-1.5B | 1.5B | WeiboAI | `2006…txt:25,119` | E0 (paper claims only; no local eval here) |
| VibeThinker-3B | 3B | WeiboAI | `2006…txt:26,120` | E0 |
| TFPI (Thinking-Free Policy Initialization) | arXiv 2509.26226 + Tencent-Hunyuan code | `2006…txt:29-33` | E1 (one paper) |
| Nanbeige4.1-3B | 3B | Nanbeige | `2006…txt:35-40` | E0 |
| Reasoning-Embedding | paper arXiv 2601.21192 + HKUST-KnowComp | `2006…txt:42-46` | E0 (concept; weights not listed) |

### B.2 Agentic / SWE Tooling

| Model / Repo | Class | Source line | NEXUS relevance |
|---|---|---|---|
| FastContext-1.0-4B-SFT | repo-local explorer | `2006…txt:1-2` | Augments `nexus_os/vault/semantic_backend.py` `LocalBackend`/`HybridBackend`. |
| Scale-SWE-Agent (AweAI-Team) | agent | `2006…txt:9` | Comparison point for `nexusclaw/heavyskill_relay.py`. |
| SWE-Lego family + `Terminal-Lego-Qwen3-8B`, `SWE-Review-8B` | SWE-agent + reviewer | `2006…txt:15-21` | Consumable as HeavySkill add-on; matches `knowledge.md:389` HeavySkill relay pattern. |
| VibeThinker-3B-litert-lm (LiteRT-LM port) | edge runtime | `1706…txt:26` | Useful context for TWAVE wrapper paths. |
| LiteRT community models (EmbeddingGemma-300M) | edge embedding | `1706…txt:33-37` | Could inform NEXUS L0/L1 cascade (`knowledge.md:175`). |

### B.3 Distillation / Compression-Ready

| Model / Repo | Compressed-format variants | Source line | NEXUS relevance |
|---|---|---|---|
| `DavidAU/Qwen2.5-1.5B-VibeThinker-heretic-uncensored-abliterated` | uncensored GGUF | `1706…txt:121` | **Behavior-Control Lab only**: normal routing denied; lab routing allowed only with KAIJU/VAP controls, no tools, no credentials, and no public release path. |
| `PrunaAI/WeiboAI-VibeThinker-1.5B-HQQ-8bit-smashed` | 8-bit HQQ | `1706…txt:122` | Reinforces NEXUS Quantized Path-A work (`knowledge.md:282`). |
| `squ11z1/Chronos-1.5B` | 1.5B distilled | `1706…txt:125` | Survey only. |
| Qwen3.6-27B-MTP / Carwin-28B-MTP (Jackrong, kai-os, isneezekittens, FINAL-Bench) | 27–28B MTP variants | `1706…txt:1-7,11-13` | Multi-token prediction is already in `NEXUS_V3_ARCHITECTURE.md:149`. |
| DFlash + PARO + SparseLoRA + Flash-colreduce (z-lab family) | sparsified 397B / 30B / 27B | `1706…txt:151-159` | Quant correctness — NEXUS-local `rotor_quant.py` analog. |
| DFlash Qwen3.5-4B / gemma-4-31B GGUF | local GGUF | `1706…txt:160-164` | Fits `Nexus OS / TWAVE` low-VRAM lane. |

### B.4 Safety / Adversarial-Scope

| Model | Status | Source line | Rule |
|-------|--------|--------------|------|
| `huihui-ai/Huihui-Nex-N2-mini-abliterated` | uncensored | `2006…txt:430` | Behavior-Control Lab only; normal routing denied. |
| `edougawa/Nex-N2-mini-Abliterated` + `Abliterated-NVFP4` | uncensored | `2006…txt:432,436` | Behavior-Control Lab only; normal routing denied. |
| `OBLITERATUS/Qwen3.6-27B-OBLITERATED` | uncensored | `1706…txt:13` | Behavior-Control Lab only; normal routing denied. |
| `SC117/Huihui-Nex-N2-mini-abliterated-APEX-GGUF` | uncensored quantized | `2006…txt:438` | Behavior-Control Lab only; normal routing denied. |
| `wuwangzhang1216/abliterix` repo | abliteration tooling | `2006…txt:434` | Reference tooling, not a model. |
| `prefeitura-rio/models` | org listing | `2006…txt:417` | None identified yet. |
| `internlm/WildClawBench` (dataset) | benchmark corpus | `2006…txt:420,422` | Adds to NEXUS `benchmarks/` evaluation coverage. |

### B.5 Organization Accounts (Fresh Sources)

| Account | URL | Source line |
|--------|-----|-------------|
| AllenAI | https://huggingface.co/allenai  | `2006…txt:5-7` |
| AweAI-Team | https://huggingface.co/AweAI-Team  | `2006…txt:9-11` |
| SWE-Lego | https://huggingface.co/SWE-Lego  | `2006…txt:17-21` |
| WeiboAI | https://huggingface.co/WeiboAI  | `2006…txt:25-26` |
| Tencent-Hunyuan | https://github.com/Tencent-Hunyuan/Thinking-Free_Policy_Initialization  | `2006…txt:29` |
| meituan-longcat | https://huggingface.co/meituan-longcat  | `2006…txt:51-57` |
| Nanbeige | https://huggingface.co/Nanbeige  | `2006…txt:36-39` |
| nex-agi | https://huggingface.co/nex-agi  | `2006…txt:428` |
| apodex | https://huggingface.co/apodex  | `1706…txt:147-149` |
| huihui-ai | https://huggingface.co/huihui-ai  | `2006…txt:430` |
| litert-community | https://huggingface.co/litert-community  | `1706…txt:33-37` |
| KaLM-Embedding | https://huggingface.co/KaLM-Embedding  | `1706…txt:135` |
| z-lab | https://github.com/z-lab  | `1706…txt:152-156` |

---

## Section C — Map to Existing NEXUS Pillars

| NEXUS pillar | Already-existing surface | This digest's relevance |
|--------------|---------------------------|--------------------------|
| Bridge (port 7352) | `nexus_os/api/brain_api.py` route `/api/relay/health` (line 675) | LongCat can become a new relay-style provider via 7350 / 7355 split (`brain_api.py` line 87-89). |
| Governor | `nexus_os/governor/{trust_engine_v2.py, kaiju_auth.py, skill_auditor.py}` | FastContext + LiteRT guard models (EmbeddingGemma 300M) can populate the L0 / L1 cascade. |
| Vault (8-channel) | `nexus_os/vault/memory_channels.py` (per `knowledge.md:21`) | Reasoning-Embedding + KaLM-Embedding can feed a new `EMBEDDING` channel sub-adapter (do **not** invent a new channel). |
| Engine | `nexus_os/engine/{hermes.py, forge.py, executor.py, tool_discipline.py}` | FastContext-1.0-4B may back SKILL pattern routing; SWE-Lego models map to HeavySkill. |
| GMR | `nexus_os/gmr/{rotator.py, pool_config.py, domain_mapping.py, latency_monitor.py}` | VibeThinker fast path, Nanbeige4.1-3B cost-tier, Qwen3.6-27B local-quant tier. |
| Swarm | `nexus_os/swarm/{auction.py, worker.py, foreman.py, coordinator.py}` | Round-robin / weighted-auction baselines already exist; new entrants feed auction instead of inventing `nexusclaw`-adjacent lane. |
| Monitoring | `nexus_os/monitoring/{token_guard.py, counters.py, strategies.py, trust_scorer.py}` | TokenGuard budgets per model placeholder already exists. |
| Observability | `nexus_os/observability/{squeez.py, tracing.py, langfuse_tracker.py}` | DFlash / PARO claims tie to log-compression work in `squeez.py`. |

---

## Section D — Priority-Ranked Integration List

| Priority | Item | Why | Approx effort |
|----------|------|-----|---------------|
| P0 | Add LongCat provider stub (`pool_config.py`) | First "ready-to-use" entry, OpenAI/Anthropic formats | 30 min |
| P0 | Register `LongCat-2.0-Preview` model (`models/registry.py`) | Single canonical model name; dual endpoint | 30 min |
| P1 | Add LiteRT-LM / LiteRT community EdgeGemma-300M to L0 guard cascade (`governor/`) | Replicates the L0/L1 architecture in `knowledge.md:175` | 2h |
| P1 | Catalog SWE-Lego family in HeavySkill (`nexusclaw/heavyskill_relay.py`) | Direct HeavySkill evidence base | 2h |
| P2 | Register FastContext-1.0-4B-SFT as knowledge-graph search augmentation | Strengthens `HybridBackend` | 4h |
| P2 | Evaluate TFPI paper against `engine/hermes.py` reasoning-pipeline | May reduce reasoning-token overhead | 1 day |
| P3 | Add Nanbeige4.1-3B to cost-tier options | Adds budget tier | 2h |
| P3 | Add DFlash-family GGUF metadata to model_arena catalog | Convenience | 2h |
| P4 (governor-only) | Mark `huihui-ai/*` and `OBLITERATUS/*` as behavior-control-lab-only in model intake metadata | Deny normal routing while preserving defensive research value | 30 min |

---

## Section E — Hard-NO Imports (untreated yet)

| Item | Reason |
|------|--------|
| Any file from `MIGRATE_AZURE_TO_PROVIDER_ROUTER.md` | Cross-road with REQ-2/REQ-3/REQ-4 (provider migration). |
| The exposed `ak_2N…bH8J` key | Already-leaked secret; user must decide rotation. |
| Defensive "comment_*" or "instruction_*" jailbreak dictionaries from `ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt` as raw imports | They are research artifacts, not defensive rules — see `papers09` strategic assessment for the integration pattern. |

---

## Section F — Verification Commands (read-only)

```text
# 1) Confirm paths exist
Test-Path "C:\Users\speci.000\Downloads\ARCHIVIST\2006fancyMODELSandNewPaPeRs.txt"
Test-Path "C:\Users\speci.000\Downloads\ARCHIVIST\1706fancyMODELS.txt"

# 2) Hash the source files for integrity
Get-FileHash "C:\Users\speci.000\Downloads\ARCHIVIST\2006fancyMODELSandNewPaPeRs.txt" -Algorithm SHA256
Get-FileHash "C:\Users\speci.000\Downloads\ARCHIVIST\1706fancyMODELS.txt" -Algorithm SHA256

# 3) Hit the upstream product page via http (operator-supervised)
iwr -UseBasicParsing https://api.longcat.chat/openai/v1/models # may return 401 without a key

# 4) Confirm NEXUS-side stub locations exist
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\gmr\pool_config.py"
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\models\registry.py"
```

If the operator decides to add LongCat, the steps above are the only evidence collection needed before any code-level integration. Provider key acquisition is the user's call.

