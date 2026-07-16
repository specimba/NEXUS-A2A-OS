# NEXUS cloud train / bench / dataset plan — 2026-07-11

**Status:** live on Intern **NEXUS-GPU-test2** (A100, extended ~4h+) + suite on GH  
**Priority order remains:** 1 (trace/training solidification) → 3 (curation) → 2 (lanes)

## Why this exists
Micro matmul ticks proved GPU + JuiceFS + GH. Next layer uses **D:\NEXUS_MODELS** research + **Documents\NEXUS** scripts + **HF Hub** search to build real train/bench/merge/stress paths under `/data/NEXUS` (visible as `/root/NEXUS`).

## Assets
| Location | Role |
|----------|------|
| `D:\NEXUS_MODELS\datasets\` | glaive, hermes, APIGen, UltraInteract, gated xlam pending |
| `D:\NEXUS_MODELS\{gguf,loras,benchmarks,safetensors}` | local models / experiments |
| `Documents\NEXUS\nexus_os\{finetune,dataset_forge,bench,stresslab}` | in-repo frameworks |
| `Documents\NEXUS\docs\research\HF_HUB_DEEP_SEARCH_2026-06-22.md` | prior HF catalog |
| `scripts/nexus_cloud_suite/` on `specimba/NEXUS_discovery_GPU` | **cloud orchestrator (this drop)** |

## Cloud suite (GH)
- `hf_dataset_deep_search.py` — Hub search by category  
- `build_nexus_sft_mix.py` — mix + synthetic security/tool edges  
- `train_and_stress.py` — TinyLM SFT-like train + matmul ladder + EMA merge dry-run + edge battery  
- `run_suite.py` — full pipeline + GH upload to `reports/session4/cloud_suite/`  
- `SECURITY.md` — env-only tokens, edge-case rules  

## Security (0 drama, many edge cases)
- No tokens in files; redact in logs  
- Soft-fail gated HF datasets  
- Non-finite loss abort, empty batch, OOM catch  
- Train only on license-clean mixes; Fable5 CoT stays reference-only  

## Roadmap
1. **Now (A100 timed):** suite every N ticks + classic train tick  
2. **A800 unlimited:** TokenHD 0.6B (plan S3/S1.4) when F-2 gate clear for DPO later  
3. **Merges/fine-tunes:** promote TinyLM → peft LoRA on small HF base when deps present  
4. **Local D: sync:** optional `rclone`/manual copy of glaive shards into `/data/NEXUS/datasets` for richer mixes  

## Operator
- HF agree: `Salesforce/xlam-function-calling-60k` when ready  
- Never paste tokens into Cline chat  
- Keep Explorer on `/root/NEXUS` → JuiceFS  
