# NEXUS Modal + Model Strategy — June 2026

Status: provisional, evidence-gated.

## Decision

NEXUS core model work must optimize for a governed small specialist swarm, not a
single 14B+ default model. The resident production guard/router lane stays under
~3B total parameters unless the operator explicitly approves a temporary probe.

Large frontier models are useful, but they are not the core runtime. They are
teacher, judge, distiller, probe, or temporary Modal services.

## Model Lanes

| Lane | Use | Examples | Routing rule |
|---|---|---|---|
| `core` | Resident NEXUS guard/router specialists | WalledGuard-edge, Qwen3Guard-class 0.6B, small 1.5B-3B code/security utility | Must pass `ModelRegistry.validate_core_resident_budget()` |
| `probe` | Evaluation/research models above core budget | Gemma-4-12B variants, Qwen3.6-27B/35B-A3B, Qwen3-Coder-30B-A3B, Cyber-Quack-14B | Evidence-only until evals justify promotion |
| `teacher` | Labeling, judging, adversarial eval generation | Nemotron-3-Ultra-550B, GLM-5.1, Kimi K2/K2.6, MiniMax-M3 | No default routing; bounded Modal/API job only |
| `quarantine` | High-risk or unreviewed models | obliterated, abliterated, uncensored, heretic, trust_remote_code, proprietary/patent-pending claims | No automatic tool execution or public release path |
| `retired` | Removed from active routing | stale local models, broken provider paths | Registry kept for provenance only |

## Modal Contract

All Modal model work starts with the bounded pilot contract in
`nexus_os.models.modal_budget`.

Default rules:

- Max pilot spend is `$40`.
- `min_containers` must remain `0`.
- Background polling and broad health checks are disabled.
- Volume cleanup, per-run cost summary, and artifact manifest are required.
- One run means one model, one dataset slice, one eval pack, one budget cap.

## Nemotron Ultra Position

Nemotron Ultra is not impossible; it is the wrong first training spend.

The relevant model card describes a 550B total / 55B active model with a minimum
inference footprint of 4xB200/GB200/GB300/B300 or 8xH100. Fine-tuning adds
adapter compatibility, distributed training, optimizer/checkpoint overhead,
activation memory, and method validation risk on top of inference cost.

Use under this budget:

- short controlled serving;
- teacher labels;
- judge comparisons;
- long-context eval generation;
- distillation into small NEXUS specialists.

Do not attempt large-model refusal-vector or obliteration work before the method
is proven on 0.6B, 1B, and <=3B models with deterministic evals.

## Evidence Basis

Local inputs:

- `Downloads/ARCHIVIST/allnexusMODALbenchtraintuneFULLpack.txt`
- `Downloads/ARCHIVIST/allDATASETevalutionandTRAINsets.txt`
- `Downloads/ARCHIVIST/allSECrelatedmodelandsets.txt`
- `Downloads/ARCHIVIST/allSECandFABLE-MYTHOSrelatedmodeltracesetstxt.txt`
- `Downloads/ARCHIVIST/1706fancyMODELS.txt`
- `Downloads/ARCHIVIST/2026-06-16-memory-layer-synthesis.md`
- June `Downloads/NEXUSlogs/*`

Repo enforcement:

- `nexus_os.models.registry.ModelEntry.role`
- `nexus_os.models.registry.ModelRegistry.validate_core_resident_budget()`
- `nexus_os.models.registry.ModelRegistry.list_quarantined_models()`
- `nexus_os.models.modal_budget.ModalRunContract`
- `nexus_os.monitoring.provider_health.ProviderHealthMonitor.CHECK_INTERVAL == 0`
