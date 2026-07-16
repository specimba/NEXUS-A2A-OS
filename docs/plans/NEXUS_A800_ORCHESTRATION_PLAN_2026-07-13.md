# NEXUS A800 GPU Orchestration Plan — 2026-07-13

> Deep synthesis of 30h Grok session, PAPERS master distillation, D:
> assets, cloud suite scripts, CDP knowhow, and A800 current state.
> Operator directive: make every GPU-hour count toward NEXUS fine-tune / merge / model testing.

## 1. Current A800 State (as of 2026-07-13 ~03:06 UTC)

| Field | Value |
|-------|-------|
| Notebook | `6a4bd983-...` (run page) |
| Tick | **315 DONE** (advanced from 87 during monitoring) |
| Checkpoint | `tinylm_a800_t314_20260713T030423Z.pt` |
| Report | `/home/mw/project/NEXUS_session4/reports/a800/A800_TICK_315_20260713T030612Z.json` |
| GitHub proof | `specimba/NEXUS_discovery_GPU` commit `3b5c711` |
| Project usage | ~72-74% (needs gentle pruning) |
| Calm PID | 9204 |
| Heartbeat | `sleep_fail 240s fail=7` = alive but slow sweep |

**Calibration**: The A800 trained ~228 ticks in ~36 hours unsupervised.
The calm loop micro-batch trainer is the proven engine. Do NOT replace it;
redirect its *objective* toward NEXUS deliverables.

## 2. Training methods unlocked by PAPERS master distillation (P0 queue)

| Priority | Method | Source | What it enables on A800 |
|----------|--------|--------|--------------------------|
| **P0a** | SERA SVG-SFT | papers10 | Soft-verified repo-native SFT; 26x cheaper than RL |
| **P0b** | RIFT trust-weighted loss | papers09 | Use failures as training signal; Beta-posterior = reward weight |
| **P0c** | Fugu soft-target SFT | papers10 | Distill frontier models via CDP-captured traces; trust-posterior-weighted |
| **P0d** | CLEANER purification | papers04/10 | Purify trajectories before training; SOTA at 1/3 steps |
| **P0e** | FAPO flawed-positive check | papers10 | Detect flawed RLVR rollouts; process-check judge |
| **P0f** | FTPO not DPO | papers13/09 | Final-token preference pairs; 90% slop suppression <1% quality loss |
| **P0g** | OPSD/SDPO | papers10 | Self-distillation removes frontier-teacher dependency |
| **P0h** | Does-RLVR | papers10 | Spend RL only where base model ~0%; save budget |
| **P0i** | TMAX (DPPO + FP32 head) | papers10 | Open terminal-agent RL; taxonomy-generated envs |
| **P0j** | DPPO + TDScaling | papers10 | Spend generation budget on trajectory DIVERSITY not volume |

## 3. Local assets ready for A800 consumption

### D:\NEXUS_MODELS\gguf (local inference / merge / stress)
| Model | Size | Role |
|-------|------|------|
| VibeThinker-3B Q4_K_M | 1.9 GB | Math/code verifier; CDP classifier |
| VibeThinker-1.5B Q4_K_M | 1.04 GB | Ultra-compact reasoning |
| Qwen2.5-Coder-1.5B Q4_K_M | 1.04 GB | Fast code gen |
| DeepSeek-R1-Distill-1.5B Q4_K_M | 1.04 GB | Reasoning baseline |
| Nemotron Safety Guard 8B Q4_K_M | 4.58 GB | Guard model |

### D:\NEXUS_MODELS\datasets (A800 SFT seed)
| Dataset | Size | Type |
|---------|------|------|
| glaive-function-calling-v2 | 258 MB | Function calling (permissive) |
| hermes-function-calling-v1 | 63 MB | Function calling (permissive) |
| APIGen-MT-5k | 121 MB | API generation (permissive) |
| UltraInteract_sft | 163 MB | Multi-turn SFT (permissive) |
| xlam-function-calling-60k | gated | Need HF agree |

### D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\datasets (benchmarks)
| Asset | Role |
|-------|------|
| bench_llama-guard3_1b.json | Guard benchmark |
| bench_qwen2.5-guard-q4.json | Qwen guard eval |
| bench_gemma4-e2b-guard.json | Gemma guard eval |
| bench_functiongemma.json | Function calling guard |
| bench_special-virus.json | Virus guard eval |
| fused_attack_train/test.jsonl | Red-team training data |
| fused_benign_train/test.jsonl | Benign baseline |
| scenarios_001-1000_EN.jsonl | 1000 adversarial scenarios |
| guard_plane_ensemble_test.json | Ensemble evaluation |
| decision_locator_*.py | Decision location probes |
| attack_kb.py / attack_kb_index.json | Attack knowledge base |

### D:\NEXUS_COLD\level5_migrations\foundry_datasets
| Asset | Role |
|-------|------|
| merge_manifest.json | TIES/DARE merge recipes |

## 4. A800 execution protocol (concrete)

### Phase 1 — SFT data fabrication on A800 (P0a + P0d + P0j)

```text
1. Capture frontier traces via CDP browser automation:
   - Grok: REPLY_COLLECTED synthesis + capability map
   - ChatGPT: MCP architecture extraction
   - Gemini: cloud deployment recommendation
   - Qwen deep: deep research + scoring output
   - DeepSeek: fast code review
   - Meta AI: HTML/CSS tricks
   → All traces land in NEXUS_session4/traces/YYYY-MM-DD/

2. CLEANER-purify the raw trajectories:
   - Remove tool-call failures
   - Deduplicate near-identical turns
   - Strip PII / secrets
   → Clean file: train.jsonl

3. RIFT trust-weight the traces:
   - Each trace scored by TrustKernel Beta posterior (already computed)
   - High-trust traces keep full weight
   - Low-trust traces keep PARTIAL weight (not discarded → RIFT)
   → Weighted file: train_weighted.jsonl

4. SFT on TinyLM base (or small HF base like Qwen2.5-1.5B):
   - A800 notebook: new_cell("sft_rift")
   - Dataset: /data/NEXUS/rift_trains/train_weighted.jsonl
   - Epochs: 1-2, lr 2e-4, r=16 (QLoRA if deps present)
   - Checkpoint every 50 steps to /data/NEXUS/checkpoints/

5. Proof: GH commit with loss curve + eval probe scores
```

### Phase 2 — Style tuning via FTPO (P0f)

```text
1. Generate style pairs from SFT model output:
   - Prompt: "Rewrite this NEXUS operator response without slop"
   - Preferred: model output (cleaned)
   - Rejected: raw verbose output
   → Pairs file: style_pairs.jsonl

2. FTPO train (not DPO): final-token preference optimization
   - Base: Phase 1 SFT checkpoint
   - Method: Antislop/FTPO from papers13
   - Expected: 90% slop reduction, <1% quality loss

3. Proof: benchmark guard scores before/after FTPO
```

### Phase 3 — Guard-DPO from red-team corpus (P0f + P0g)

```text
1. Feed D:\NEXUS_COLD adversarial scenarios into Fable5:
   - scenarios_001-1000_EN.jsonl → 1000 adversarial prompts
   - Run through current guard stack (walledguard-edge, Llama-Guard-3-1B, Granite)
   - Log every miss → candidate DPO negative

2. Build guard preference pairs:
   - Rejected: guard misses (should have blocked)
   - Preferred: guard correctly blocks
   → Pairs: guard_dpo_v1.jsonl

3. DPO/OPSD train on Llama-Guard-3-1B:
   - OPSD preferred (self-distillation; no frontier teacher)
   - OR standard DPO if compute allows

4. Proof: 1000-scenario red-team recall before/after
```

### Phase 4 — Arena Scoring V2 wiring (bridge to local)

```text
1. Arena SFT:
   - SFT model learns to score model outputs like a human judge
   - Training data: Bradley-Terry pairwise comparisons from CDP lane outputs
   - Target: replace synthetic 0.45 defaults with real arena scores

2. Shadow Arena MVP:
   - Shadow-route real tasks to challenger models
   - Blinded pairwise judging with position randomization
   - Style-controlled Bradley-Terry (length/markdown covariates)
   - Bootstrap CIs (≥1000 resamples)

3. Proof: leaderboard correlation with human preference
```

## 5. A800 control via CDP (automation not babysitting)

### Existing CDP tools (verified working)

| Tool | Purpose | Status |
|------|---------|--------|
| `lane_stack_preflight.mjs` | multi-lane dedupe → restore → probe | ✅ Working |
| `grok_cdp_context_probe.mjs` | host-aware match + wake + probe | ✅ Working |
| `send_grok_cdp.ps1` | auto dedupe + CDP restore + verify + read | ✅ Working |
| `control_surface_doctor.ps1` | Port 9224 lane ownership | ✅ Working |
| `multi_lane_a2a_cycle.mjs` | role-send A2A protocol | ✅ Working |
| `a2a_cycle_evidence.mjs` | CDP + DOM delta + screenshots | ✅ Working |

### Automation loop (operator-free A800 control)

```text
# --- BEGIN: A800_calibrate.sh (run once to align A800 with NEXUS needs) ---
REPO=/home/mw/project/NEXUS_session4
TRAIT_SRC=/data/NEXUS/traces          # CDP-captured frontier traces
BENCH_SRC=/data/NEXUS/benchmarks      # rsync of D:\NEXUS_COLD\*\bench_*.json
LORAS_SRC=/data/NEXUS/loras           # adapter-only outputs

mkdir -p $TRAIT_SRC $BENCH_SRC $LORAS_SRC $REPO/runs/{sft,ftp0,guard,arena}

# rsync new traces from Windows CDP capture
rsync -av --progress /mnt/c/Users/speci.000/Downloads/NEXUSlogs/cdp_traces/ $TRAIT_SRC/

# rsync benchmark assets from D: drive
rsync -av --progress /mnt/d/NEXUS_COLD/level5_migrations_20260605/NEXUS/datasets/bench_*.json $BENCH_SRC/
# --- END ---
```

### Monitor loop (run every 15 min via cron, NOT Grok context)

```text
# --- BEGIN: a800_cron_check.ps1 ---
# Lightweight one-shot; no AI context consumed
$latest = gh api repos/specimba/NEXUS_discovery_GPU/contents/reports/session4/a800/LATEST.json -H "Accept: application/vnd.github.raw" | ConvertFrom-Json
$age = (Get-Date).ToUniversalTime() - [datetime]::Parse($latest.stamp)
if ($age.TotalMinutes -gt 20) { Write-Output "WARN: tick stale $($age.TotalMinutes)min" }
elseif ($latest.tick -ge 500) { Write-Output "DONE: target reached" }
else { Write-Output "OK: tick=$($latest.tick) age=$($age.TotalMinutes)min" }
# --- END ---
```

## 6. Cloud suite promotion path

The existing `scripts/nexus_cloud_suite/` on `specimba/NEXUS_discovery_GPU`
has all the scaffolding: hf_dataset_deep_search.py, build_nexus_sft_mix.py,
train_and_stress.py, run_suite.py. Promote them:

```text
1. Upload D:\NEXUS_MODELS\datasets seeds to `/data/NEXUS/datasets/`
2. Upload D:\NEXUS_COLD bench jsons to `/data/NEXUS/benchmarks/`
3. Run build_nexus_sft_mix.py → outputs train.jsonlTrain
4. Run train_and_stress.py — single command does: train → matmul ladder → EMA merge dry-run → edge battery
5. run_suite.py — full pipeline + GH upload to reports/session4/cloud_suite/
```

## 7. Operator decision checklist

| # | Decision | Why |
|---|----------|-----|
| 1 | Confirm SFT base model for A800: TinyLM (current) or Qwen2.5-1.5B (HF) | Determines checkpoint format + merge path |
| 2 | Which CDP lane captures to use as traces: all 7 or subset | Volume vs. diversity tradeoff |
| 3 | When to prune Project: now (gentle) or after current run | 72% is safe; >85% needs action |
| 4 | Guard-DPO scope: which 3 guard model gets the first DPO pass | WalledGuard-Edge, Llama-Guard, or Granite |
| 5 | Arena shadow mode: start with pairwise Grok vs ChatGPT | Require minimum 100 battle pairs before BT fit |

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| A800 notebook hang (tick 87 history) | Kernel Interrupt + cell-level rerun; never full restart unless frozen |
| Project >85% | Terminal `rm -rf` of old checkpoints; keep last 2 only |
| JuiceFS `du` hang | Never call `du -sh`; use `ls -lh` + `find -mtime +7` instead |
| New notebook creation | `ALLOW_OPEN_NEW_NB` unset; if UI misfires, kill calm + reuse existing mon |
| Calm process death | Heartbeat .ps1 script restarts once; repeat death → hard stop |
| CDP lag during A800 runs | Close non-essential :9224 tabs (keep only the capture lane needed) |

## 9. Next concrete step

1. Run `lane_stack_preflight.mjs --port 9224` → confirm STACK_READY
2. Run `grok_cdp_context_probe.mjs` on all 6 mapped lanes → collect DOM snapshots
3. Send Fable5 traces from all lanes via `send_grok_cdp.ps1` + director
4. On A800: new_cell("sft_rift_v1") with captured traces
5. Let calm loop run; check GH LATEST every 30 min via lightweight PS1
6. DO NOT use Grok/GPT context for monitoring — use cron + GitHub API
