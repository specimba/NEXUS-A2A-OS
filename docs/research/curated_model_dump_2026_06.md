# NEXUS Curated Model & Paper Dump — 2026-06-05

Source: `C:\Users\speci.000\Downloads\ARCHIVIST\megaLinkModelPaperdump-02.txt` (200KB, 7290 lines)
Author: user-curated list of HF models + arxiv papers + dataset references

## Contents Summary
- Lines 1–1500: Research paper (SDPO — Reinforcement Learning via Self-Distillation, arxiv 2601.20802)
- Lines 1500–7290: Curated HF model links, datasets, papers

## Gemma 4 Family — Notable Models
All Gemma 4 abliterated/uncensored variants in the dump are 12B — too large for RTX 4070 8GB (~6GB Q4, very tight).
**No Gemma 4 E2B abliterated variant exists yet** in the curated list.

| HF ID | Type | Notes |
|---|---|---|
| `google/gemma-4-12B` | base | Multimodal unified (text/audio/image/video), encoder-free |
| `burtenshaw/gemma-4-12b-sdpo-pi-mono-trace-feedback-v2` | SDPO fine-tune | Trained on badlogicgames/pi-mono traces via SDPO (self-distillation) |
| `OpenYourMind/gemma-4-12B-it-abliterated-uncensored` | abliterated | Refusal removed |
| `AEON-7/Gemma-4-12B-it-AEON-Abliterated-K4-BF16` | abliterated K4 | |
| `osmapi/osmGemma-4-12B-uncensored-bf16` | uncensored | |
| `dealignai/Gemma-4-12B-it-JANG_4M-CRACK` | fine-tune | |
| `MoonRide/gemma-4-12B-it-heretic` | heretic | |
| `DuoNeural/Gemma4-12B-IT-Abliterated` | abliterated | |
| `litert-community/gemma-4-12B-it-litert-lm` | liteRT-LM export | |
| `igorls/gemma-4-12B-it-heretic` | heretic | |

## Small/Fit-Friendly Models (RTX 4070 8GB)

| HF ID | Size | Purpose |
|---|---|---|
| `Goekdeniz-Guelmez/Qwen3-4B-Thinking-2507-gabliterated` | 4B | Abliterated thinking |
| `mradermacher/Qwen3-4B-Thinking-2507-gabliterated-GGUF` | 4B Q4 | Ready-to-use GGUF |
| `SicariusSicariiStuff/IBM_granite-4.1-3b_Abliterated` | 3B | Granite abliterated |
| `mradermacher/granite-4.1-3b-Abliterated-AND-Disinhibited-GGUF` | 3B Q4 | Ready-to-use |
| `Goekdeniz-Guelmez/JOSIE-4B-Thinking` | 4B | Thinking model |
| `Lazarus-Ai/ReAligned-Qwen3.5-0.8B-FP8` | 0.8B | FP8, ultra-light |
| `Jackrong/Qwen3.5-0.8B-Claude-4.6-Opus-Reasoning-Distilled-GGUF` | 0.8B | Distilled |
| `mr`adermacher/nirukti-0.5B-v3-GGUF` | 0.5B | Tiny |

## Agent / Reasoning Models
| HF ID | Size | Notes |
|---|---|---|
| `armand0e/Qwen3.5-9B-Pi-Agent` | 9B | Pi-agent, too big for our VRAM |
| `TeichAI/Claude-Opus-4.6-Reasoning-887x` | unknown | Reasoning dataset |
| `Vigp17/agentcode-32b` | 32B | Code agent |
| `hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled` | 35B-A3B | MoE distilled |
| `momix-44/Huihui-Qwen3.6-35B-A3B-Claude-4.6-Opus-abliterated` | 35B | Abliterated |

## Datasets
- `badlogicgames/pi-mono` — trace dataset, 627+ records, used in SDPO training
- `Trendyol/Qwen3-14B-BaronLLM-v2-Q8` — Q8 quant
- `AlicanKiraz0/Qwen3-14B-BaronLLM-v2-Q4_0-GGUF` — Q4_0 GGUF

## Papers
- **arxiv 2601.20802** — "Reinforcement Learning via Self-Distillation" (Hübotter et al, ETH Zurich, Jan 2026)
  - SDPO method: LLM generates its own training data via self-distillation, then trains on its own outputs
  - Relevant for offline guard improvement without human labels

## NEXUS Storage Reference
- `huggingface.co/buckets/specimba/nexus-storage` — user-created HF bucket for NEXUS work

## Strategic Implications for NEXUS Guard
1. **Gemma 4 E2B IT (already downloaded) is the right guard target** — no E2B abliterated exists, so we abliterate locally
2. **Gemma 4 12B is too big for 8GB VRAM** — skip abliterated 12B family
3. **Qwen3-4B-Thinking gabliterated** is a 4B alternative worth testing if E2B doesn't suffice
4. **Granite 4.1 3B abliterated** is a lighter alternative
5. **SDPO paper** offers a path to fine-tune our own guard without external labels — but requires self-distillation pipeline
6. **Pi-mono traces** could be used for guard training (synthetic adversarial prompts)

## Constraint
- C: drive has 0.7 GB free → **NO new model downloads**
- Only 0.5–3B Q4 GGUF variants could fit (~500MB–1.5GB) if disk space freed
