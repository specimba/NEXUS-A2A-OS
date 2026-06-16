# Kilo Snapshot P3 Manual Closeout - 2026-06-09

## Scope

Classifies the remaining `P3_manual`, `P2_model_asset`, and `P4_generated` live-untracked protection rows. It does not stage, move, delete, or restore files.

## Counts

### Risk

| Value | Rows |
|---|---:|
| `P3_manual` | `115` |
| `P4_generated` | `26` |
| `P2_model_asset` | `11` |

### Prefix

| Value | Rows |
|---|---:|
| `datasets` | `85` |
| `upload` | `38` |
| `models` | `13` |
| `benchmarks` | `8` |
| `research` | `8` |

### Disposition

| Value | Rows |
|---|---:|
| `preserve_research_tooling_review_before_tracking` | `75` |
| `manifest_only_external_evidence` | `38` |
| `ignore_or_purge_generated_after_review` | `26` |
| `model_registry_or_d_archive_no_blind_git_tracking` | `11` |
| `preserve_model_tooling_no_weights_blind_tracking` | `2` |

### Release gate

| Value | Rows |
|---|---:|
| `PASS` | `150` |
| `BLOCK` | `2` |

## Release Blockers

| Risk | Path | Gate | Disposition |
|---|---|---|---|
| `P3_manual` | `datasets/retrain_classifier_v3.py` | `BLOCK` | `preserve_research_tooling_review_before_tracking` |
| `P3_manual` | `upload/DERDDRE-01.txt` | `BLOCK` | `manifest_only_external_evidence` |

## Decision

- P3 research/benchmark scripts are preserved as local research tooling candidates, not public upload bodies.
- P2 model assets are registry/archive candidates; do not blindly track weights or model payloads.
- P4 generated rows are safe to ignore or purge only after explicit review; they are not recovery blockers.
- Any `BLOCK` row must be represented as manifest-only in external bundles.
