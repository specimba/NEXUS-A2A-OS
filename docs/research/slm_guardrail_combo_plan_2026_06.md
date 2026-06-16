# SLM Guardrail Combo Plan - 2026-06-06

## Target Architecture (NEXUS OS Governance Layers)

```
User Query
   |
   v
[1] Pre-Filter: Meta-Attack Detector (46 categories, regex+heuristic)
   |   + RefusalMancer query classifier (protects against FP override)
   v
[2] BOUNCER Ensemble (conservative: both must agree UNSAFE)
   |   - Gemma 4 E2B IT Q4_K_M (2.96 GB, already on disk)
   |   - Qwen2.5-Guard Q4 (1.5B, already running)
   v  (if safe)
[3] Tool Synthesis: FunctionGemma 270M (general function calls)
   |   - Generates JSON function-call schema
   v
[4] Bash Specialization: BashGemma 270M (PEFT on FunctionGemma)
   |   - For bash intent: translate to find/grep/ls/cat/wc/sort
   |   - 57.4% NLC2CMD accuracy on NL2Bash
   v
[5] Hermes Docker Sandbox + seccomp + network policy
   |   - Read-only root, dropped capabilities
   |   - Per-pattern 2026 NemoClaw/OpenShell baseline
   v
[6] KAIJU Gate: pre-execution policy check (per 2026-06-03 anchored summary)
   v
[7] Execute + VAP audit log
   v
Output to user
```

## What Each Layer Does (with NEXUS OS governance mapping)

| Layer | Component | OWASP ASI | NEXUS Layer | Role |
|---|---|---|---|---|
| 1 | Meta-Attack Detector | ASI01, ASI02, ASI06 | L1 Identity & Privilege | Block known attack patterns pre-model |
| 1 | RefusalMancer | ASI09 (FP override) | L7 Audit | Prevent false-positive blocking of benign queries |
| 2 | Gemma 4 E2B IT | All categories | L2/L3/L4 Trust + Memory | Reasoning-based safety classification |
| 2 | Qwen2.5-Guard | All categories | L2 Trust | Pre-trained safety classifier (independent of E2B) |
| 3 | FunctionGemma 270M | ASI02, ASI05 | L5 RCE | Generate valid function-call JSON (no shell escape) |
| 4 | BashGemma 270M | ASI05, ASI06 | L5 RCE | Bash-specialized tool calls (limited scope: find/grep/ls/etc.) |
| 5 | Hermes Docker Sandbox | ASI05 | L5 RCE | Contain execution (sandbox escape mitigation) |
| 6 | KAIJU Gate | ASI03, ASI04, ASI10 | L1 Identity | Pre-execution policy enforcement |
| 7 | VAP Audit | All | L7 Audit | Tamper-evident log of every action |

## Models Inventory (Verified on Disk or to Download)

| Model | Source | License | Size | Status |
|---|---|---|---|---|
| Gemma 4 E2B IT Q4_K_M | `unsloth/gemma-4-E2B-it-GGUF` | Apache 2.0 | 2.96 GB | **On disk** (`models/gemma-4-e2b/`) |
| Qwen2.5-Guard Q4 | `qwen2.5-guard-q4:latest` | Apache 2.0 | ~1.5 GB | **Running in Ollama** |
| Llama-Guard3 1B | `llama-guard3:1b` | Llama 3 Community | ~1 GB | Running in Ollama (low weight) |
| Special-Virus 1.2B | `special-virus:latest` | (custom) | 1.2 GB | Running (60% FP — flag for replacement) |
| FunctionGemma 270M | `unsloth/functiongemma-270m-it` | Gemma terms | ~150 MB Q4 | **To download** |
| BashGemma 270M | `potteryrage/bashgemma-270m` | Apache 2.0 | ~30 MB PEFT | **To download** (PEFT, needs FunctionGemma base) |

## Why BashGemma as PEFT on FunctionGemma

BashGemma is **not** a standalone model — it's a LoRA adapter (rank=64, alpha=128) trained for 36 minutes on 9,153 NL2Bash examples. The model card explicitly says:

```python
from peft import PeftModel
base_model = AutoModelForCausalLM.from_pretrained("unsloth/functiongemma-270m-it")
model = PeftModel.from_pretrained(base_model, "potteryrage/bashgemma-270m")
```

This means:
- We must load `unsloth/functiongemma-270m-it` first
- Then apply the BashGemma PEFT adapter
- For Ollama: merge the adapter into a single GGUF (using llama.cpp's `convert_lora_to_gguf.py` or similar)
- For HF direct load (per `datasets/guard_plane.py:103-145`): use `PeftModel.from_pretrained()`

## Plan (next 3-5 steps)

### Step 1: Download FunctionGemma 270M Q4_K_M GGUF
- HF ID: `unsloth/functiongemma-270m-it-GGUF`
- File: `functiongemma-270m-it.Q4_K_M.gguf` (or similar)
- Approx size: 150-200 MB
- Disk impact: minimal (have 92.62 GB free)

### Step 2: Download BashGemma PEFT adapter
- HF ID: `potteryrage/bashgemma-270m`
- Approx size: 30 MB
- Need to merge into FunctionGemma base for Ollama import

### Step 3: Merge BashGemma PEFT into FunctionGemma base
- Use llama.cpp's `convert_lora_to_gguf.py` (which we already discovered at `models/convert_hf_to_gguf.py`)
- Output: single merged GGUF (functiongemma-bashgemma-merged.Q4_K_M.gguf)
- Approx size: 150-200 MB

### Step 4: Import to Ollama
- `functiongemma-guard` (base + BashGemma merged)
- `functiongemma-base` (FunctionGemma only, for general tool calls)
- Modelfile: `models/functiongemma/Modelfile`

### Step 5: Wire into `datasets/guard_plane.py`
- Add to MODEL_REGISTRY:
  - `functiongemma-guard` — bash tool synthesis, weight 1.0
  - `functiongemma-base` — general function call, weight 0.8
- Update ensemble logic: when BOUNCER passes, route to FunctionGemma for tool synthesis
- For bash-detected queries (regex match), use BashGemma-merged model

### Step 6: Test combo
- Smoke test: "Find all Python files" → BashGemma output: `{"name": "find", "arguments": {"name": "'*.py'", "path": "."}}`
- Verify function-call JSON is well-formed
- Verify bash command is sandboxed (Hermes Docker pattern)
- Measure latency

## Files to Create

- `models/functiongemma/Modelfile` — Ollama import
- `models/functiongemma/merge_lora.py` — LoRA merge script
- `tests/test_functiongemma_bashgemma_combo.py` — Combo test
- `datasets/tool_synthesis.py` — New module: routes safe queries to FunctionGemma
- Update `datasets/guard_plane.py` — Add tool synthesis stage

## Constraints Honored

- **No model trashing**: All existing models preserved
- **No fine-tuning**: Using pre-trained BashGemma as-is
- **No uncensored/roleplay models**: BashGemma is a tool-calling model, not a roleplay
- **Apache 2.0 / Gemma terms**: Both models open-source
- **NEXUS OS governance**: Combo maps to OWASP ASI Top 10 + Singapore AI Governance
- **No theatre**: Every step has verifiable evidence (test output, file presence, latency)

## What Could Go Wrong

- **PEFT merge fails**: BashGemma was trained on M4 Max, may have architecture assumptions. Fallback: load via HF `PeftModel` directly (already supported in `guard_plane.py`).
- **FunctionGemma Q4 not available**: May need Q5_K_M or Q6_K. Quality should still be high (paper says 6T tokens of training, robust to quantization).
- **BashGemma scope too narrow**: Capabilities limited to find/grep/ls/cat/wc/sort. For other bash commands, fall back to FunctionGemma base + manual function spec.
- **Sandbox overhead**: Hermes Docker + seccomp adds 1-3s latency per execution. May need to keep non-sandboxed fast path for read-only ops.
