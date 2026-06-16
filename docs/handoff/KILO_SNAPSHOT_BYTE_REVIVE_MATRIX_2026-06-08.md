# Kilo Snapshot Byte Revive Matrix - 2026-06-08

## Scope

Evidence source:

- Kilo snapshot quarantine: `D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot`
- JSON report: `docs/handoff/KILO_SNAPSHOT_BYTE_COMPARE_HIGH_VALUE_2026-06-08.json`
- CSV row matrix: `docs/handoff/KILO_SNAPSHOT_BYTE_COMPARE_HIGH_VALUE_2026-06-08.csv`

This was read-only. No file was restored, deleted, moved, or overwritten.

The Kilo snapshot is a Git object/index snapshot, not a raw filesystem mirror. Byte equality here means Kilo snapshot Git blob bytes compared against the live file hashed with the same Git path/filter rules. For model/data binaries this is raw byte-equivalent. For Windows text files this avoids false loss reports from CRLF working-tree conversion.

## High-Value Prefixes Checked

`benchmarks`, `datasets`, `models`, `src`, `nexus_os`, `research`, `docs`, `.agents`, `tests`, `tasks`, `evidence`, `logs`, `upload`.

Total selected high-value rows compared: `1,676` out of `2,295` snapshot-tracked files.

## Relation Summary

| Relation | Count | Meaning |
|---|---:|---|
| `byte_identical_to_snapshot` | 390 | Live file still equals the Kilo snapshot blob. Not a restore target. |
| `live_matches_current_index_not_snapshot` | 341 | Live tracked file matches current Git index, but Kilo is stale. Do not restore Kilo. |
| `live_differs_from_snapshot_and_index` | 98 | Live tracked file differs from both Kilo and current index. Treat as active dirty work; do not overwrite. |
| `live_differs_from_snapshot_untracked` | 828 | Live file exists but is untracked and differs from Kilo. Protect/intake live version first. |
| `missing_live` | 19 | Live filesystem path is absent. These are the only direct revive candidates. |

## Prefix Matrix

| Prefix | Snapshot rows | Identical | Current-index newer | Tracked changed | Live untracked changed | Missing |
|---|---:|---:|---:|---:|---:|---:|
| `.agents` | 39 | 0 | 0 | 0 | 39 | 0 |
| `benchmarks` | 169 | 34 | 0 | 0 | 135 | 0 |
| `datasets` | 199 | 44 | 5 | 7 | 143 | 0 |
| `docs` | 244 | 28 | 16 | 13 | 187 | 0 |
| `evidence` | 11 | 0 | 0 | 0 | 11 | 0 |
| `logs` | 46 | 0 | 0 | 0 | 46 | 0 |
| `models` | 149 | 57 | 3 | 1 | 88 | 0 |
| `nexus_os` | 114 | 24 | 40 | 47 | 3 | 0 |
| `research` | 309 | 179 | 1 | 0 | 129 | 0 |
| `src` | 264 | 0 | 246 | 0 | 0 | 18 |
| `tasks` | 8 | 1 | 0 | 0 | 6 | 1 |
| `tests` | 72 | 18 | 26 | 25 | 3 | 0 |
| `upload` | 52 | 5 | 4 | 5 | 38 | 0 |

## Kind Matrix

| Kind | Rows | Identical | Current-index newer | Tracked changed | Live untracked changed | Missing |
|---|---:|---:|---:|---:|---:|---:|
| `data_or_benchmark` | 294 | 62 | 7 | 4 | 221 | 0 |
| `docs_or_research` | 642 | 209 | 15 | 14 | 403 | 1 |
| `generated_or_cache` | 45 | 19 | 0 | 0 | 26 | 0 |
| `model_or_weight` | 60 | 49 | 0 | 0 | 11 | 0 |
| `sensitive_path` | 102 | 6 | 37 | 11 | 46 | 2 |
| `source_or_script` | 533 | 45 | 282 | 69 | 121 | 16 |

## Missing-Live Queue

Direct revive candidates are limited to `19` snapshot paths:

| Snapshot path | Class | Bytes | Action |
|---|---|---:|---|
| `src/nexus_os/governor/__init__.py` | source | 505 | Compare against root `nexus_os/governor/__init__.py`; likely no direct restore. |
| `src/nexus_os/governor/trust_kernel.py` | source | 24,259 | Diff against root `nexus_os/governor/trust_kernel.py`; root is likely newer. |
| `src/nexus_os/governor/trust_scoring.py` | source | 13,433 | Diff against root equivalent; likely low restore priority. |
| `src/nexus_os/mcp/__init__.py` | source | 113 | Compare against root package; likely no direct restore. |
| `src/nexus_os/mcp/server.py` | source | 131 | Snapshot was tiny; root server is likely canonical. |
| `src/nexus_os/monitoring/__init__.py` | source | 114 | Compare only. |
| `src/nexus_os/monitoring/semantic_drift_monitor.py` | source | 6,177 | Compare only. |
| `<redacted-sensitive-path:.py>` | sensitive-name source | 26,273 | Review manually from snapshot blob; do not auto-restore. |
| `<redacted-sensitive-path:.py>` | sensitive-name source | 17,119 | Review manually from snapshot blob; do not auto-restore. |
| `src/nexus_os/security/__init__.py` | source | 309 | Compare against root package. |
| `src/nexus_os/security/contamination_detector.py` | source | 35,702 | Compare against root equivalent. |
| `src/nexus_os/security/meta_attack_detector.py` | source | 42,481 | Root is likely newer; diff only. |
| `src/nexus_os/security/sanitizer.py` | source | 8,940 | P0 port candidate; snapshot likely has unique sanitizer/verifiable-output logic. |
| `src/nexus_os/security/shortcut_neuron_detector.py` | source | 16,114 | Compare against root equivalent. |
| `src/nexus_os/stress_lab/__init__.py` | source | 65 | Low priority unless `stress_lab` package is revived. |
| `src/nexus_os/stress_lab/cloud_attack_bee_v2.py` | source | 15,557 | P0 revive/port candidate. |
| `src/nexus_os/stress_lab/cloud_report_bee.py` | source | 11,733 | P0 revive/port candidate. |
| `src/nexus_os/stress_lab/cloud_swarm_orchestrator.py` | source | 21,800 | P0 revive/port candidate. |
| `tasks/pending/2026-05-27-memory-unification-activation.task.md` | task/doc | 1,578 | P0/P1 recreate or restore as pending memory-unification task. |

## Recovery Decision

Do not restore whole prefixes from Kilo. The data says:

- `src` is mostly a legacy-layout snapshot: `246` paths already match current index under the canonical repo state, and only `18` legacy `src` paths are absent.
- `benchmarks`, `datasets`, `docs`, `research`, `.agents`, `logs`, `upload`, and parts of `models` are mostly live-untracked material. The work is protection/intake, not blind restore.
- `nexus_os` and `tests` contain active tracked and dirty current work. Kilo is evidence for comparison only; overwriting would likely destroy newer work.

## Next Execution Slice

1. Extract the `19` missing-live blobs into a review-only folder, not live paths.
2. Port only unique logic from `src/nexus_os/security/sanitizer.py` and the three `src/nexus_os/stress_lab/*` modules after diff review.
3. Restore or recreate `tasks/pending/2026-05-27-memory-unification-activation.task.md` if it is still relevant.
4. Build a protection matrix for the `828` live-untracked changed files, starting with `docs`, `research`, `datasets`, `benchmarks`, `.agents`, `upload`, and source-like files.
5. Keep the 40 GiB Kilo quarantine until steps 1-4 are reviewed. After that, purge only with an explicit approval and a final preserved manifest.

