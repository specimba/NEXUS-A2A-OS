# HF Hub Search Results — Papers09/10 NEXUS Upgrade
**Date:** 2026-06-22
**Searcher:** NEXUS planning synthesis
**Output:** `D:\NEXUS_MODELS\datasets\hf_search_results.json`

## Summary

| Search Category | Top Result | Likes | Downloads | Notes |
|-----------------|-----------|-------|-----------|-------|
| VibeThinker-3B | `prithivMLmods/VibeThinker-3B-GGUF` | 608 | 32K | **DOWNLOADED** Q4_K_M 1.9 GB |
| VibeThinker-1.5B | `mradermacher/VibeThinker-1.5B-GGUF` | (variant) | — | **DOWNLOADED** Q4_K_M 1.04 GB |
| AceReason-Nemotron-14B | `nvidia/AceReason-Nemotron-14B` | 97 | 1152 | Not downloaded (14B too big for 8GB VRAM) |
| Qwen2.5-Coder-1.5B | `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` | 93 | 247K | **DOWNLOADED** Q4_K_M 1.04 GB |
| DeepSeek-R1-Distill-Qwen-1.5B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | 1527 | 611K | **DOWNLOADED** Q4_K_M 1.04 GB |
| GLM-5.2 GGUF | `unsloth/GLM-5.2-GGUF` | 251 | 42K | **CANNOT DOWNLOAD** — Q4_K_M is 540 GB (~744B params) |
| Nemotron Safety Guard 8B | `nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3-GGUF` | 21 | 2690 | **DOWNLOADED** Q4_K_M 4.58 GB |
| Intern-S1 | `internlm/Intern-S1` | 260 | 10K | Not downloaded (97 safetensors shards, hundreds of GB) |
| MiniMax-M3 (me!) | `MiniMaxAI/MiniMax-M3` | 1207 | 120K | I'm already running on this |
| MiniMax-M3 GGUF | `unsloth/MiniMax-M3-GGUF` | 112 | 29K | Available for local fallback |
| SWE-bench Verified | `princeton-nlp/SWE-bench_Verified` | 358 | 710K | Dataset, gold standard |
| OpenHands-SFT | `SWE-Gym/OpenHands-SFT-Trajectories` | 15 | 384 | SWE agent trajectories |
| OpenHands Rebench | `nebius/SWE-rebench-openhands-trajectories` | 132 | 5K | Bigger OpenHands dataset |
| glaive-function-calling-v2 | `glaiveai/glaive-function-calling-v2` | 514 | 49K | **DOWNLOADED** 258 MB |
| Hermes-Function-Calling | `NousResearch/hermes-function-calling-v1` | — | — | **DOWNLOADED** 63 MB |
| APIGen-MT-5k | `Salesforce/APIGen-MT-5k` | — | — | **DOWNLOADED** 121 MB |
| UltraInteract-SFT | `openbmb/UltraInteract_sft` | — | — | **DOWNLOADED** 163 MB |
| xlam-function-calling-60k | `Salesforce/xlam-function-calling-60k` | 642 | 27K | **ACCESS DENIED** (gated repo) |
| arthur_prompt_injection_benchmark | `Arthur-AI/arthur_prompt_injection_benchmark` | 0 | 17 | Empty download (likely auth) |
| harpreetsahota/adversarial-prompts | (same) | 4 | 33 | Empty download (likely auth) |
| mcp-tool-use-quality-benchmark | `rogue-security/mcp-tool-use-quality-benchmark` | 3 | 13 | MCP-specific benchmark, not downloaded |

## Models Downloaded to D: (9.5 GB total)

| Path | Size | VRAM | Use |
|------|------|------|-----|
| `D:\NEXUS_MODELS\gguf\vibethinker-1.5b\` | 1.04 GB | ~1 GB | Reasoning baseline + forge eval |
| `D:\NEXUS_MODELS\gguf\vibethinker-3b\` | 1.8 GB | ~2 GB | Reasoning teacher candidate |
| `D:\NEXUS_MODELS\gguf\qwen25-coder-1.5b\` | 1.04 GB | ~1 GB | Code specialist |
| `D:\NEXUS_MODELS\gguf\deepseek-r1-distill-1.5b\` | 1.04 GB | ~1 GB | Reasoning baseline (DeepSeek R1 distill) |
| `D:\NEXUS_MODELS\gguf\nemotron-safety-guard-8b\` | 4.58 GB | ~5 GB | Verifier role (safety gate) |

Total model size: 9.5 GB. Free D: space: 580 GB.

## Datasets Downloaded to D: (607 MB total)

| Path | Size | Use |
|------|------|-----|
| `D:\NEXUS_MODELS\datasets\glaive-function-calling-v2\` | 258.6 MB | Function calling training |
| `D:\NEXUS_MODELS\datasets\test-hermes-function-calling-v1\` | 63.7 MB | Function calling training (alternate) |
| `D:\NEXUS_MODELS\datasets\test-APIGen-MT-5k\` | 121.9 MB | API/tool generation |
| `D:\NEXUS_MODELS\datasets\test-UltraInteract_sft\` | 163.6 MB | General SFT |
| `D:\NEXUS_MODELS\datasets\adversarial-prompts\` | 0 MB | (gated, did not download) |
| `D:\NEXUS_MODELS\datasets\arthur-prompt-injection\` | 0 MB | (gated) |
| `D:\NEXUS_MODELS\datasets\xlam-function-calling-60k\` | 0 MB | (gated — needs approval) |

## Gated Datasets — Operator Action Required

These need approval from HF Hub (usually automatic for xlam):
- `Salesforce/xlam-function-calling-60k` (27K downloads — best MCP tool training set)
- `Arthur-AI/arthur_prompt_injection_benchmark` (17 downloads — small)
- `harpreetsahota/adversarial-prompts` (33 downloads — small)

**Operator workflow:** visit each URL → click "Agree and access repository" → re-run download.

## GLM-5.2 — Cannot Download (Too Big)

`unsloth/GLM-5.2-GGUF` Q4_K_M = 540 GB (model is ~744B params, all 11 shards). Exceeds 8GB VRAM AND our 580 GB free D: drive. **GLM-5.2 free path not viable.**

Alternative GLM-5.2 access paths:
- NIM (currently 429 throttled)
- SiliconFlow (key DEAD)
- Ollama Cloud (paywalled)
- Novita AI (zero balance)
- Hugging Face Spaces (demo only)

**Status:** Wait for NIM quota reset or find another free host.

## Recommended Next Steps

1. **Test downloaded models via Ollama**: `ollama serve` then `ollama run vibethinker:3b`
2. **Forge pipelines**: convert `glaive-function-calling-v2` and `UltraInteract_sft` to NEXUSDataset format
3. **Train Nemotron Safety Guard with adversarial prompts** — once we have those
4. **Apply LongCat + InternAI as log/memory fallback tier** — Fugu dispatch is wired
5. **Watch for NIM GLM-5.1 reset + GLM-5.2 release**

## References

- HF Hub search results: `D:\NEXUS_MODELS\datasets\hf_search_results.json`
- papers09 batch: 89 papers, 6 NEXUS categories (already integrated)
- papers10 batch: 129 papers (just started — 6 deep-dived via subagent)
- Sakana paper synthesis: `docs/research/NEXUS_SAKANA_PAPERS10_UPGRADE_BLUEPRINT_2026-06-22.md`