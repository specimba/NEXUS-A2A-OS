# Kilo Snapshot Deep Triage - 2026-06-08

## Scope

Input evidence:

- Kilo snapshot: `D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot`
- Redacted compare report: `docs/handoff/KILO_SNAPSHOT_RECOVERY_COMPARE_2026-06-08.json`
- High-value candidate CSV: `docs/handoff/KILO_SNAPSHOT_HIGH_VALUE_CANDIDATES_2026-06-08.csv`

This investigation was read-only against the Kilo snapshot. No snapshot blobs were restored into live paths.

## Main Correction

The raw counts looked worse than the real recovery situation.

| Raw bucket | Current deeper meaning |
|---|---|
| `missing_in_live_repo=19` | Real recovery queue. These are absent from the filesystem. |
| `different_from_current_index=472` | Mostly stale snapshot-vs-index differences. Only `21` live files differ from both current index and snapshot. |
| `not_tracked_in_current_index=1613` | Mostly live files that still exist but are not protected by Git. This is a protection/intake problem, not immediate data loss. |

## Missing Live Files

Current missing-live count: `19`.

| Class | Count | Meaning |
|---|---:|---|
| Missing code under legacy `src/nexus_os/*` | 18 | Must compare against current root `nexus_os/*`; do not recreate legacy `src` layout blindly. |
| Missing task doc | 1 | Likely recoverable planning task. |

### Missing Code Queue

| Snapshot path | Current equivalent | Finding |
|---|---|---|
| `src/nexus_os/governor/__init__.py` | `nexus_os/governor/__init__.py` | Root exists; minor export/init differences. |
| `src/nexus_os/governor/trust_kernel.py` | `nexus_os/governor/trust_kernel.py` | Root exists and is larger/newer: 761 lines vs 631 snapshot lines. Review only for lost small details. |
| `src/nexus_os/governor/trust_scoring.py` | `nexus_os/governor/trust_scoring.py` | Near-identical: similarity `0.997`. Low restore priority. |
| `src/nexus_os/mcp/__init__.py` | `nexus_os/mcp/__init__.py` | Root exists and is larger. Snapshot was tiny. |
| `src/nexus_os/mcp/server.py` | `nexus_os/mcp/server.py` | Root exists and is much larger: 576 lines vs 3 snapshot lines. Do not restore snapshot. |
| `src/nexus_os/monitoring/__init__.py` | `nexus_os/monitoring/__init__.py` | Normalized text identical. Not lost. |
| `src/nexus_os/monitoring/semantic_drift_monitor.py` | `nexus_os/monitoring/semantic_drift_monitor.py` | Normalized text identical. Not lost. |
| `src/nexus_os/monitoring/token_guard.py` | `nexus_os/monitoring/token_guard.py` | Root exists, similarity `0.974`; review diff before deciding. |
| `src/nexus_os/monitoring/token_policy.py` | `nexus_os/monitoring/token_policy.py` | Normalized text identical. Not lost. |
| `src/nexus_os/security/__init__.py` | `nexus_os/security/__init__.py` | Root exists; minor export/init differences. |
| `src/nexus_os/security/contamination_detector.py` | `nexus_os/security/contamination_detector.py` | Normalized text identical. Not lost. |
| `src/nexus_os/security/meta_attack_detector.py` | `nexus_os/security/meta_attack_detector.py` | Root exists and is larger/newer: 1129 lines vs 760 snapshot lines. Do not overwrite. |
| `src/nexus_os/security/sanitizer.py` | `nexus_os/security/sanitizer.py` | High-risk regression candidate: snapshot has 271 lines with `TerminalSanitizer` and `VerifiableOutput`; root is 5-line shim. Review/port needed. |
| `src/nexus_os/security/shortcut_neuron_detector.py` | `nexus_os/security/shortcut_neuron_detector.py` | Normalized text identical. Not lost. |
| `src/nexus_os/stress_lab/__init__.py` | `nexus_os/stresslab/__init__.py` | Root package exists under `stresslab`, but not equivalent. Low priority. |
| `src/nexus_os/stress_lab/cloud_attack_bee_v2.py` | none | Real missing candidate: `CloudAttackBeeV2`, 336 snapshot lines. |
| `src/nexus_os/stress_lab/cloud_report_bee.py` | none | Real missing candidate: `CloudReportBee`, 264 snapshot lines. |
| `src/nexus_os/stress_lab/cloud_swarm_orchestrator.py` | none | Real missing candidate: `CloudSwarmOrchestrator`, 512 snapshot lines. |

### Missing Task

`tasks/pending/2026-05-27-memory-unification-activation.task.md`

This is a real missing planning artifact. It is a P0 pending task titled:

`[Lane A] Memory Unification - Reconcile`

Purpose: inventory all memory-related code paths and external services, document TrustKernel/VAP interaction with memory systems, and produce a memory reconcile document. This aligns with the user's repeated memory-system concerns. It is a candidate for controlled restore or recreation.

## Different From Current Index

Raw count: `472`.

After hashing the live working-tree subset:

| Live relation | Count | Meaning |
|---|---:|---|
| Live file matches current Git index | 441 | Kilo snapshot is stale for these paths. Do not restore. |
| Live file differs from both current index and Kilo snapshot | 21 | Active current work or later edits. Do not overwrite with Kilo. Review only if needed. |

The `21` live-differs-from-both paths are concentrated in active core surfaces:

| Prefix | Count |
|---|---:|
| `nexus_os` | 12 |
| `upload` | 5 |
| `AGENTS.md` | 1 |
| `nexusctl` | 1 |
| `pyproject.toml` | 1 |
| `tests` | 1 |

Examples:

- `nexus_os/governor/trust_kernel.py`
- `nexus_os/relay/model_relay.py`
- `nexus_os/security/meta_attack_detector.py`
- `nexus_os/vault/memory_adapter.py`
- `nexusctl/cli.py`
- `AGENTS.md`

Conclusion: these are not Kilo restore targets. They need normal Git review because current live files moved beyond both the tracked index and the Kilo snapshot.

## Live But Not Git-Protected

Raw count: `1613`. Deeper check:

| State | Count |
|---|---:|
| Live file exists but is not tracked by current index | 1610 |
| Ignored by `.gitignore` | 0 |
| Unignored and untracked | 1610 |

This is the largest operational risk. These files are live, not lost, but not protected by Git or ignore policy.

Unignored live-untracked breakdown:

| Kind | Count |
|---|---:|
| Docs/research | 704 |
| Data/benchmark | 392 |
| Source/script | 373 |
| Other | 67 |
| Model/weight | 59 |
| Backup/shadow | 15 |

Top prefixes:

| Prefix | Count | Suggested disposition |
|---|---:|---|
| `research` | 308 | Intake and canonicalize selected reports; archive raw dumps. |
| `docs` | 215 | Review for canonical docs/handoff/governance value. |
| `datasets` | 187 | Preserve, but likely move to evidence/data policy rather than track all. |
| `benchmarks` | 169 | Preserve and decide which benchmark outputs are canonical. |
| `models` | 144 | Do not track weights by default; add model inventory/ignore/archive policy. |
| `nexus_os_backup_untracked` | 82 | Compare against live `nexus_os`, then archive or purge after approval. |
| `nexus_os_shadow_backup` | 82 | Same as above. |
| `nexus_os_untracked_backup` | 82 | Same as above. |
| `wl-commons` | 65 | Investigate separately; likely external artifact. |
| `backups` | 47 | Archive policy, not repo tracking. |
| `logs` | 46 | Evidence retention policy, not raw repo tracking. |
| `upload` | 43 | Intake candidate; may include reports and packages. |
| `.agents` | 39 | Agent skill/config intake candidate; review before tracking. |
| `nexus_os` | 27 | High-value source review. |
| `evidence` | 11 | GROSS/NEXUS evidence policy; do not public-track blindly. |
| `tests` | 11 | High-value test intake. |
| `tasks` | 7 | High-value operator task intake. |

Conclusion: the user is right that the Kilo snapshot captured valuable docs/data. The key point is that most of it is already live. The immediate mission is not restore; it is protection, triage, and canonical intake.

## Priority Queue

### P0 - Recover Or Port

1. Review/port `src/nexus_os/security/sanitizer.py` into current canonical security surface if the 271-line snapshot has unique logic.
2. Review `src/nexus_os/stress_lab/cloud_attack_bee_v2.py`.
3. Review `src/nexus_os/stress_lab/cloud_report_bee.py`.
4. Review `src/nexus_os/stress_lab/cloud_swarm_orchestrator.py`.
5. Restore or recreate `tasks/pending/2026-05-27-memory-unification-activation.task.md`.

### P1 - Diff Review Only

1. `src/nexus_os/monitoring/token_guard.py` vs `nexus_os/monitoring/token_guard.py`.
2. `src/nexus_os/governor/trust_kernel.py` vs `nexus_os/governor/trust_kernel.py`.
3. `src/nexus_os/governor/trust_scoring.py` vs `nexus_os/governor/trust_scoring.py`.
4. `src/nexus_os/security/meta_attack_detector.py` vs `nexus_os/security/meta_attack_detector.py`.

Do not overwrite root files. Root files are generally newer or equivalent.

### P2 - Protect Live Untracked Work

Create a NEXUS intake matrix for:

- `docs`
- `research`
- `datasets`
- `benchmarks`
- `tests`
- `tasks`
- `.agents`
- `upload`
- live `nexus_os` untracked files

Decision per item:

- Track as canonical source/doc/test.
- Move to `D:\NEXUS_COLD` as evidence archive.
- Add to `.gitignore` if generated/cache/model/log.
- Keep live but mark as local-only evidence.

## Current Recommendation

Do not purge the Kilo snapshot yet.

Next execution slice should be:

1. Extract only the P0 missing-code blobs into a review-only temp folder.
2. Diff and port `sanitizer.py` and the three `stress_lab` modules if they contain unique logic.
3. Restore/recreate the missing memory-unification task.
4. Build a `live-untracked-protection-matrix` for the `1610` live untracked files.
5. Only after that, decide whether Kilo's 40 GiB snapshot can be purged.

