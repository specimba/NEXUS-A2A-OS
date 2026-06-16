# Kilo Snapshot Recovery Findings - 2026-06-08

## Scope

Evidence source:

`D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot`

Generated metadata report:

`docs/handoff/KILO_SNAPSHOT_RECOVERY_COMPARE_2026-06-08.json`

Command used:

```powershell
python -m nexusctl disk-rescue kilo-forensics --out docs\handoff\KILO_SNAPSHOT_RECOVERY_COMPARE_2026-06-08.json
```

This pass was read-only. It did not restore, delete, mutate, index, sync, or print file contents. Sensitive-looking paths were redacted in the JSON report.

## What The Snapshot Is

The snapshot contains multiple Git dirs. The tool selected the largest indexed Git dir:

`D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot\c1478df17dcc92fb168eb2f707bfd4be1359d9fb\1ez1mr9vui4u4`

Selection evidence:

| Git dir tracked files | Count |
|---|---:|
| Selected dominant NEXUS mirror | 2,295 |
| Other snapshot Git dirs | 240, 571, 314, 771 |

Git config evidence:

| Field | Value |
|---|---|
| `core.worktree` | `C:/Users/speci.000/Documents/NEXUS` |
| `user.name` | `opusmanSEEKv4` |
| `user.email` | redacted |
| `filter.lfs.required` | `true` |

Conclusion: this is a Kilo-managed Git/LFS snapshot of NEXUS, not a normal cache.

## Why It Is 40 GiB

| Category | Files | Size GiB | Meaning |
|---|---:|---:|---|
| Git tmp pack garbage | 7 | 18.649 | Failed/interrupted pack creation. This is the largest waste source. |
| Valid Git packs | 9 | 16.868 | Snapshot object storage. Useful only for extracting candidate blobs. |
| Git LFS object | 1 | 2.875 | Large LFS object captured by snapshot. |
| Loose Git objects | 2,313 | 1.710 | Normal snapshot object residue. |
| Git metadata/other | 167 | ~0.001 | Config/index/hooks/refs and small state. |

The biggest single files were one `13.689 GiB` `.pack`, two `6.757 GiB` `tmp_pack_*` files, one `3.147 GiB` `.pack`, one `3.145 GiB` `tmp_pack_*`, and one `2.875 GiB` LFS object.

Conclusion: the 40 GiB was mostly Git pack storm plus valid snapshot storage, not active Kilo chat usage.

## What Kilo Captured

The selected snapshot tracked `2,295` paths.

Top captured prefixes:

| Prefix | Count |
|---|---:|
| `research` | 309 |
| `src` | 264 |
| `docs` | 244 |
| `datasets` | 199 |
| `benchmarks` | 169 |
| `models` | 149 |
| `nexus_os` | 114 |
| `nexus_os_backup_untracked` | 82 |
| `nexus_os_shadow_backup` | 82 |
| `nexus_os_untracked_backup` | 82 |
| `scripts` | 60 |
| `upload` | 52 |
| `backups` | 47 |
| `logs` | 46 |
| `.agents` | 39 |

Sensitive-looking tracked path count: `174`. The report redacts these paths by default.

Conclusion: Kilo captured source, backups, datasets, models, logs, uploads, agent config, and sensitive-looking paths. It must not be indexed into memory or cloud systems.

## Live NEXUS Comparison

Fast path-presence comparison:

| Result | Count |
|---|---:|
| Snapshot path exists as live file | 2,275 |
| Snapshot path missing from live filesystem | 18 |
| Snapshot path exists but is not a file | 2 |

Current Git-index comparison:

| Result | Count |
|---|---:|
| Same as current tracked index | 210 |
| Different from current tracked index | 472 |
| Not tracked in current index | 1,613 |

Interpretation:

- The Kilo snapshot contains a very large untracked/recovery surface.
- The `472` index differences are review candidates, not automatic restore candidates.
- The `18` missing live files are the first true recovery queue because the current filesystem no longer has them.

## First Recovery Queue: Missing Live Paths

Non-sensitive missing paths found in the selected Kilo snapshot:

| Path | Snapshot blob size bytes | Recovery stance |
|---|---:|---|
| `src/nexus_os/governor/__init__.py` | 505 | Review before restore |
| `src/nexus_os/governor/trust_kernel.py` | 24,259 | Review against root `nexus_os/governor/trust_kernel.py` |
| `src/nexus_os/governor/trust_scoring.py` | 13,433 | Review before restore |
| `src/nexus_os/mcp/__init__.py` | 113 | Low value unless legacy `src` package is still needed |
| `src/nexus_os/mcp/server.py` | 131 | Low value unless legacy `src` package is still needed |
| `src/nexus_os/monitoring/__init__.py` | 114 | Low value unless legacy `src` package is still needed |
| `src/nexus_os/monitoring/semantic_drift_monitor.py` | 6,177 | Review before restore |
| `src/nexus_os/security/__init__.py` | 309 | Review before restore |
| `src/nexus_os/security/contamination_detector.py` | 35,702 | Review against current root security modules |
| `src/nexus_os/security/meta_attack_detector.py` | 42,481 | Review against current root security modules |
| `src/nexus_os/security/sanitizer.py` | 8,940 | Review before restore |
| `src/nexus_os/security/shortcut_neuron_detector.py` | 16,114 | Review before restore |
| `src/nexus_os/stress_lab/__init__.py` | 65 | Low value unless legacy `src` package is still needed |
| `src/nexus_os/stress_lab/cloud_attack_bee_v2.py` | 15,557 | Review before restore |
| `src/nexus_os/stress_lab/cloud_report_bee.py` | 11,733 | Review before restore |
| `src/nexus_os/stress_lab/cloud_swarm_orchestrator.py` | 21,800 | Review before restore |

Two additional missing paths were sensitive-looking and are redacted in the report.

Most of the visible missing files are old `src/nexus_os/*` package paths. The current repo now has root-level `nexus_os/*` modules. That means these are not automatically "lost work"; they may be old duplicate layout files deleted during package migration. The review question is whether any unique logic exists in the Kilo snapshot that is not present in root `nexus_os/*`.

## Recovery Method

Do not restore the whole snapshot. For each candidate:

1. Extract one snapshot blob into a temporary review path.
2. Diff it against the current root-level equivalent or current tracked file.
3. If useful, port the logic into the current canonical package path.
4. Run focused tests.
5. Only then delete or archive the Kilo snapshot.

Restore stance:

| Candidate type | Action |
|---|---|
| Missing `src/nexus_os/*` file | Extract to temp and compare to root `nexus_os/*`; do not recreate legacy `src` tree blindly |
| Different current-index file | Use diff review only; do not overwrite |
| Not tracked in current index | Treat as evidence/intake, not canonical source |
| Sensitive redacted path | Review only with explicit operator approval |

## Tooling Added

New read-only script:

`scripts/kilo_snapshot_forensics.py`

New CLI:

```powershell
python -m nexusctl disk-rescue kilo-forensics
```

Useful options:

```powershell
python -m nexusctl disk-rescue kilo-forensics --out docs\handoff\KILO_SNAPSHOT_RECOVERY_COMPARE_2026-06-08.json
python -m nexusctl disk-rescue kilo-forensics --include-working-tree-hash
python -m nexusctl disk-rescue kilo-forensics --include-sensitive-paths
```

Default behavior is fast and safer: path presence plus Git-index comparison. Working-tree hashing is opt-in because the live repo is large and dirty.

## Verification

Focused tests:

```text
python -m pytest tests/scripts/test_kilo_snapshot_forensics.py -v --tb=short -p no:cacheprovider
2 passed in 3.51s
```

CLI help loaded successfully:

```text
python -m nexusctl disk-rescue kilo-forensics --help
exit code 0
```

Real redacted report generated:

```text
docs/handoff/KILO_SNAPSHOT_RECOVERY_COMPARE_2026-06-08.json
tracked_files=2295
missing_in_live_repo=18
different_from_current_index=472
not_tracked_in_current_index=1613
sensitive_path_count=174
```

Full suite was not run in this pass. The change is a bounded read-only CLI/script addition with a focused test.

## Next Operator Action

Review the `18` missing live paths first. My recommendation is to start with:

1. `src/nexus_os/governor/trust_kernel.py`
2. `src/nexus_os/governor/trust_scoring.py`
3. `src/nexus_os/security/contamination_detector.py`
4. `src/nexus_os/security/meta_attack_detector.py`
5. `src/nexus_os/security/shortcut_neuron_detector.py`

If those have no unique logic beyond current root `nexus_os/*`, the Kilo snapshot has served its recovery purpose and can be purged after explicit approval.

