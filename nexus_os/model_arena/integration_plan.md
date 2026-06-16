# ModelArena Integration Plan — Paper-Derived Techniques

## Overview
ModelArena (mini_arena.py) evaluates models for security and performance. This plan integrates:
- **HQQ Compression** (PrunaAI) — VRAM-constrained model optimization
- **TIES-Merging** — Resolving interference in multi-model ensembling
- **ASTRA Risk Assessment** — Steerability and risk scoring for agents
- **Intern-S1 Training Patterns** — Parameter-efficient fine-tuning

## Phase A: HQQ Integration (VRAM Optimization)
**Target**: `nexus_os/relay/model_relay.py`

Add compression endpoint:
```
POST /v1/compress/hqq
{
  "model": "deepseek-r1-8b",
  "bits": 8,
  "group_size": 128
}
```

Implementation:
1. Add HQQ quantizer class wrapping pruna_hqq
2. Apply during model load when VRAM budget < 16GB
3. Cache compressed weights in ~/.nexus_os/compressed/

## Phase B: TIES-Merging (Multi-Model Ensembling)
**Target**: `nexus_os/vault/memory_adapter.py`

Add merge endpoint:
```
POST /v1/merge/ties
{
  "base_model": "deepseek-r1-8b",
  "merge_models": ["special-virus:latest", "qwen2.5:1.5b"],
  "sparsity": 0.5
}
```

Implementation:
1. Resolve parameter interference via TIES sparsity
2. Store merged model signatures in vault trust store
3. Track merge lineage for audit trail

## Phase C: ASTRA Risk Integration
**Target**: `nexus_os/monitoring/trust_scorer.py`

Add risk scores to benchmark results:
- Steerability score (0-1)
- Alignment resistance (0-1)  
- Adversarial robustness (0-1)

Implementation:
1. Extend BenchmarkResult with `astra_risk_score`
2. Query ASTRA framework during stress tests
3. Feed into TrustKernel scoring

## Phase D: Intern-S1 Training Patterns
**Target**: `nexus_os/relay/model_relay.py`

Add LoRA fine-tuning endpoint:
```
POST /v1/fine-tune/intern-s1
{
  "model": "deepseek-r1-8b",
  "dataset": "stress_test_results",
  "lora_rank": 16
}
```

Implementation:
1. Use Intern-S1 parameter efficiency patterns
2. Apply to benchmark-failure correction
3. Track LoRA weights in vault for lineage

## Verification
- Run against existing benchmark datasets (ernie/)
- Measure VRAM reduction (target: 40% with HQQ)
- Validate merge integrity via unit tests
- Integrate with existing test suite (pytest)