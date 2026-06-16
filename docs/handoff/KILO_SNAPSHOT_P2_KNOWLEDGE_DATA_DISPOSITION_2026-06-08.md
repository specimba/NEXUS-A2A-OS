# Kilo Snapshot P2 Knowledge/Data Disposition - 2026-06-08

## Scope

This report classifies the `624` `P2_knowledge_data` rows from the live-untracked Kilo protection matrix. It does not copy file contents, restore files, move files, alter Git state, or modify the Kilo quarantine.

CSV matrix: `docs/handoff/KILO_SNAPSHOT_P2_KNOWLEDGE_DATA_DISPOSITION_2026-06-08.csv`.

JSON summary: `docs/handoff/KILO_SNAPSHOT_P2_KNOWLEDGE_DATA_DISPOSITION_2026-06-08.json`.

## Counts

- Rows: `624`
- Existing files now: `624`
- Missing now: `0`
- Duplicate blob groups: `50`
- Rows in duplicate groups: `137`

## Prefix Matrix

| Prefix | Rows | MiB | Primary Disposition |
|---|---:|---:|---|
| `docs` | 173 | 5.45 | `track_or_merge_after_review` |
| `benchmarks` | 124 | 35.14 | `preserve_manifest_first` |
| `research` | 121 | 34.41 | `dedupe_against_benchmarks` |
| `models` | 75 | 0.23 | `preserve_metadata_no_weights` |
| `datasets` | 56 | 6.64 | `preserve_manifest_first` |
| `.agents` | 39 | 0.19 | `archive_or_agent_skill_manifest` |
| `logs` | 21 | 0.52 | `preserve_readonly_evidence` |
| `evidence` | 10 | 0.12 | `preserve_readonly_evidence` |
| `tasks` | 5 | 0.01 | `review_track_if_active` |

## Category Matrix

| Category | Rows | MiB | Evidence Strength |
|---|---:|---:|---|
| `dataset_benchmark_registry` | 180 | 41.77 | `High` |
| `canonical_doc_candidate` | 113 | 2.48 | `High` |
| `research_dataset_mirror` | 82 | 34.12 | `Medium` |
| `model_metadata_registry` | 75 | 0.23 | `Medium` |
| `docs_archive` | 55 | 2.92 | `Medium` |
| `external_agent_skill_reference` | 39 | 0.19 | `Medium` |
| `research_intake` | 38 | 0.29 | `Medium` |
| `evidence_archive` | 31 | 0.65 | `High` |
| `operator_task_queue` | 5 | 0.01 | `High` |
| `docs_unsorted` | 4 | 0.02 | `Medium` |
| `docs_transition_manifest` | 1 | 0.03 | `High` |
| `research_archive` | 1 | 0.00 | `Low` |

## Source-Ranked Evidence

| Source | Evidence Strength | Claim Used | P2 Action |
|---|---|---|---|
| `docs/research/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md` | High | Raw Downloads are evidence inputs, and ModelRelay health checks must be lazy/opt-in. | Promote as canonical evidence matrix if tracked; use to reject broad polling and blind ingest. |
| `docs/TRANSITION_MANIFEST.md` | High | Defines the governed docs taxonomy and move/archive/keep/delete buckets. | Use as routing map for docs P2 rows before staging. |
| `docs/research/STRESS_LAB_DATASET_ROADMAP_2026-05-22.md` | Medium | Describes stress-lab dataset/v7 roadmap and evaluator-gated synthesis. | Treat benchmark/data rows as dataset registry inputs, not direct canonical docs. |
| `.agents/skills/onboardingv2/SKILL.md` | Medium | Third-party LaunchDarkly onboarding skill with its own workflow/persona. | Preserve as external agent-skill reference; do not merge into NEXUS governance. |
| `docs/archive/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_FREEZE_2026-05-26.json` | Medium | Redacted ledger classifies many gitleaks hits as likely false positives. | Preserve as security evidence; do not promote to current policy without fresh scan. |

## Duplicate Signal

Large duplicate groups exist, especially benchmark JSONL mirrored under `research/papers01/RED-BLUE-PURPLE`. Keep one canonical dataset location plus references instead of tracking duplicate payloads in multiple trees.

- `223a8823145b`: `8` rows, `1065` bytes each. Examples: `models/guards/guard_collusion/adapter_config.json`, `models/guards/guard_collusion/checkpoint-1506/adapter_config.json`, `models/guards/guard_content/adapter_config.json`
- `b552935ed82b`: `4` rows, `1065` bytes each. Examples: `models/guards/guard_collusion/checkpoint-754/adapter_config.json`, `models/guards/guard_mcp/adapter_config.json`, `models/guards/guard_mcp/checkpoint-1498/adapter_config.json`
- `769291071a87`: `4` rows, `336` bytes each. Examples: `models/guards/guard_collusion/tokenizer_config.json`, `models/guards/guard_content/tokenizer_config.json`, `models/guards/guard_jailbreak/tokenizer_config.json`
- `77332727715e`: `4` rows, `68` bytes each. Examples: `logs/resource-monitor/20260527_072757/ollama_churn.csv`, `logs/resource-monitor/20260527_072820/ollama_churn.csv`, `logs/resource-monitor/20260527_075214/ollama_churn.csv`
- `c8ca92c15411`: `3` rows, `2072452` bytes each. Examples: `benchmarks/stress_lab/nexus_frontier_v5_mcp_contamination.jsonl`, `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_mcp_contamination.jsonl`, `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_mcp_contamination.jsonl`
- `50e28cf60d7e`: `3` rows, `2032828` bytes each. Examples: `benchmarks/stress_lab/nexus_frontier_v5_gray_area.jsonl`, `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_gray_area.jsonl`, `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_gray_area.jsonl`
- `507728ca2683`: `3` rows, `1950161` bytes each. Examples: `benchmarks/stress_lab/nexus_frontier_v5_memory_poison.jsonl`, `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_memory_poison.jsonl`, `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_memory_poison.jsonl`
- `d7515940ab61`: `3` rows, `1826084` bytes each. Examples: `benchmarks/stress_lab/nexus_frontier_v5_gov_bypass.jsonl`, `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_gov_bypass.jsonl`, `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_gov_bypass.jsonl`

## Recommended Intake Order

1. Track or merge high-strength canonical docs first: `docs/TRANSITION_MANIFEST.md`, current `docs/research/*`, `docs/governance/*`, `docs/operations/*`, `docs/security/*`, `docs/coordination/*`, `docs/handbook/*`.
2. Create dataset and benchmark manifests before staging any bulk JSONL/CSV payloads. Prefer one canonical data location, with duplicate mirrors referenced by hash.
3. Keep `.agents/skills/onboardingv2/*` as external vendor skill reference unless NEXUS explicitly adopts it as a local skill.
4. Preserve `logs/` and `evidence/` as investigation evidence. They should feed synthesis docs, not become canonical state by themselves.
5. Keep archive rows in archive unless a current source-ranked synthesis proves they should be promoted.

## Actionable Insight

P2 should become a governed intake queue: canonical docs first, datasets by manifest/hash, external skills as references, and logs/evidence as read-only proof inputs.
