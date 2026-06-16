# Kilo Snapshot Retrieval Execution - 2026-06-08

## Scope

Recovered from:

- `D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot`

Review extraction:

- `docs/handoff/kilo-missing-review-2026-06-08/manifest.json`
- `docs/handoff/KILO_SNAPSHOT_MISSING_REVIEW_EXTRACT_2026-06-08.json`

Live restore policy:

- No blind restore into deleted legacy `src/` layout.
- Valuable logic was ported into canonical `nexus_os/` paths.
- Snapshot contents remain available in the review folder for audit.

## Retrieved Review Blobs

`19` missing-live blobs were extracted into:

`docs/handoff/kilo-missing-review-2026-06-08/files/`

The manifest records blob IDs, byte counts, SHA-256 hashes, and extraction paths. The extraction report states `live_paths_modified=false`.

## Ported Into Canonical Code

| Recovered source | Canonical target | Decision |
|---|---|---|
| `src/nexus_os/security/sanitizer.py` | `nexus_os/security/sanitizer.py` | Ported. Replaced broken wrapper that imported deleted `src.*`. |
| `src/nexus_os/stress_lab/cloud_attack_bee_v2.py` | `nexus_os/stresslab/cloud_attack_bee_v2.py` | Ported. Package import/path layout fixed. |
| `src/nexus_os/stress_lab/cloud_report_bee.py` | `nexus_os/stresslab/cloud_report_bee.py` | Ported. `REPO_ROOT` fixed for current package layout. |
| `src/nexus_os/stress_lab/cloud_swarm_orchestrator.py` | `nexus_os/stresslab/cloud_swarm_orchestrator.py` | Ported. Relative imports fixed; import-time D: directory creation removed. |
| `tasks/pending/2026-05-27-memory-unification-activation.task.md` | same | Restored as pending task. |

Additional hardening:

- `nexus_os/stresslab/__init__.py` now uses lazy exports. This prevents package import from eagerly importing `isc_runner`, which imports `ModelRelay` and can start background model health polling.
- `nexus_os/relay/model_relay.py` now defaults `RELAY_HEALTH_INTERVAL` to `0` and `RELAY_HEALTH_STARTUP_SWEEP` to `0`. If health polling is explicitly enabled, startup sweep is still opt-in. This preserves the NEXUS rule: model discovery may list models, but background inference/health polling must be lazy.
- `tests/governor/test_trust_scoring.py` and `tests/monitoring/test_token_guard.py` now import canonical `nexus_os.*` modules instead of deleted legacy `src.nexus_os.*`.

## Not Blindly Restored

The remaining recovered `src/nexus_os/*` files were not restored directly because current canonical root files already exist and are generally newer or equivalent:

- `governor/*`
- `mcp/*`
- `monitoring/*`
- `security/contamination_detector.py`
- `security/meta_attack_detector.py`
- `security/shortcut_neuron_detector.py`

These stay in the review folder for diff-only inspection.

## Token Guard / Policy Diff Decision

Recovered:

- `docs/handoff/kilo-missing-review-2026-06-08/files/src/nexus_os/monitoring/token_guard.py`
- `docs/handoff/kilo-missing-review-2026-06-08/files/src/nexus_os/monitoring/token_policy.py`

Decision:

- `token_policy.py` is byte-identical to current `nexus_os/monitoring/token_policy.py`; no port needed.
- `token_guard.py` has the same class/function API surface as current `nexus_os/monitoring/token_guard.py` (`33` common definitions, `0` recovered-only, `0` live-only). Diff is formatting/comment-level plus current wording. No port needed.

## Live-Untracked Protection Matrix

Generated:

- `docs/handoff/KILO_SNAPSHOT_LIVE_UNTRACKED_PROTECTION_MATRIX_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_LIVE_UNTRACKED_PROTECTION_MATRIX_2026-06-08.csv`
- `docs/handoff/KILO_SNAPSHOT_P1_CODE_AGENT_INTAKE_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_P0_SENSITIVE_AGGREGATE_SCAN_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_P0_SENSITIVE_AGGREGATE_SCAN_2026-06-08.json`
- `docs/handoff/KILO_SNAPSHOT_P2_KNOWLEDGE_DATA_DISPOSITION_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_P2_KNOWLEDGE_DATA_DISPOSITION_2026-06-08.csv`
- `docs/handoff/KILO_SNAPSHOT_P2_KNOWLEDGE_DATA_DISPOSITION_2026-06-08.json`
- `docs/handoff/KILO_SNAPSHOT_P2_DATASET_BENCHMARK_MANIFEST_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_P2_DATASET_BENCHMARK_MANIFEST_2026-06-08.csv`
- `docs/handoff/KILO_SNAPSHOT_P2_CANONICAL_DOC_QUEUE_2026-06-08.md`
- `docs/handoff/KILO_SNAPSHOT_P2_CANONICAL_DOC_QUEUE_2026-06-08.csv`

Summary:

| Bucket | Count | Action |
|---|---:|---|
| `P0_sensitive` | 46 | Hold for local secret scan before any public tracking. |
| `P1_code_agent` | 6 | Git intake review; all are live, not restore targets. |
| `P2_knowledge_data` | 624 | Canonicalize docs/research/tasks; registry/archive datasets and benchmarks. |
| `P2_model_asset` | 11 | Model registry or D archive; do not git-track weights blindly. |
| `P3_manual` | 115 | Manual script/archive review. |
| `P4_generated` | 26 | Ignore/quarantine after review. |

P1 rows:

- `nexus_os/__main__.py`
- `nexus_os/cli.py`
- `nexus_os/stresslab/__init__.py`
- `tests/claw/test_config_integrity.py`
- `tests/claw/test_locks.py`
- `tests/claw/test_store.py`

The P1 review found that the three Claw tests are part of a larger live untracked `nexus_os/claw` module. Treat `nexus_os/claw` and `tests/claw` as a protected intake set, not cleanup debris.

Claw intake verification:

- `python -m pytest tests\claw -v --tb=short -p no:cacheprovider`
- Result: `99 passed in 1.15s`

CLI entrypoint verification:

- `python -m nexus_os.cli version`
- Result: `NEXUS OS version 3.0.0`

P0 sensitive aggregate scan:

- Selected rows: `46`
- Files scanned: `46`
- Files with configured secret-like patterns: `19`
- Missing now: `0`
- Oversize skipped: `0`
- Prefixes with signals: mostly `logs` and `docs`
- Exact sensitive paths and secret values were not emitted.

P2 knowledge/data disposition:

- Rows: `624`
- Existing files now: `624`
- Missing now: `0`
- Duplicate blob groups: `50`
- Rows in duplicate groups: `137`
- High-strength evidence rows: `330`
- Medium-strength evidence rows: `293`
- Low-strength evidence rows: `1`

P2 category split:

| Category | Rows | Disposition |
|---|---:|---|
| `dataset_benchmark_registry` | `180` | Manifest/hash first; do not bulk stage JSONL/CSV. |
| `canonical_doc_candidate` | `113` | Review frontmatter/provenance and track or merge explicitly. |
| `research_dataset_mirror` | `82` | Dedupe against benchmark canonical paths. |
| `model_metadata_registry` | `75` | Preserve metadata; do not track weights blindly. |
| `docs_archive` | `55` | Keep archive; do not promote without fresh synthesis. |
| `external_agent_skill_reference` | `39` | Preserve as external skill reference only. |
| `research_intake` | `38` | Synthesize before canonical policy/doc adoption. |
| `evidence_archive` | `31` | Preserve read-only evidence. |
| `operator_task_queue` | `5` | Review active status before tracking. |

Action queues created:

- Dataset/benchmark manifest: `262` rows, including `213` canonical candidates and `49` duplicate mirror/reference rows.
- Canonical doc queue: `161` rows across research, wiki, coordination, operations, governance, security, tasks, reviews, handbook, and routing-needed lanes.

P2 source-ranked evidence:

- `docs/research/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md`: High; raw Downloads remain evidence inputs and ModelRelay checks stay lazy.
- `docs/TRANSITION_MANIFEST.md`: High; docs taxonomy provides the routing map.
- `docs/research/STRESS_LAB_DATASET_ROADMAP_2026-05-22.md`: Medium; dataset payloads need evaluator/registry gates.
- `.agents/skills/onboardingv2/SKILL.md`: Medium; third-party LaunchDarkly skill reference, not NEXUS governance.
- `docs/archive/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_FREEZE_2026-05-26.json`: Medium; preserve as redacted security evidence, not current policy without a fresh scan.

P2 Defender release gate:

- `C:\Users\speci.000\Downloads\ARCHIVISTsingleBIGfiletest\ARCHIVIST\NEXUS-bundle-2026-06-08.md` triggered Microsoft Defender as `Trojan:Python/ReverseShell.SA` on `2026-06-08` between `16:44:04` and `16:49:17`.
- Investigation report: `docs/handoff/P2_DEFENDER_ARCHIVIST_BUNDLE_INVESTIGATION_2026-06-08.md`.
- Gate artifacts: `docs/handoff/DEFENDER_ARCHIVIST_SOURCE_GATE_2026-06-08.md`, `docs/handoff/DEFENDER_ARCHIVIST_BUNDLE_GATE_2026-06-08.md`.
- Implemented gate: `scripts/release_bundle_gate.py`.
- Release policy: single-file upload bundles must be manifest-only; raw offensive/test payload bodies and inline execution examples block release.

## Verification

Command:

```powershell
python -m pytest tests/scripts/test_kilo_snapshot_forensics.py tests/security/test_terminal_sanitizer.py tests/stress/test_cloud_stresslab_recovery.py -v --tb=short -p no:cacheprovider
```

Result:

- `7 passed`
- Import smoke test returned `{'sanitizer': 'OK', 'queries': 33, 'report_class': 'CloudReportBee'}`
- No cloud calls were made.
- No swarm run was executed.
- No ModelRelay health-loop warning appeared after lazy stresslab exports.

Additional command:

```powershell
python -m pytest tests/claw/test_config_integrity.py tests/claw/test_locks.py tests/claw/test_store.py -v --tb=short -p no:cacheprovider
```

Result:

- `24 passed`

Latest full-suite command:

```powershell
python -m pytest tests/ -v --tb=short -p no:cacheprovider
```

Result:

- `1612 passed, 30 skipped, 8 warnings in 222.25s`

## Remaining Work

1. Secret-scan/path-review the `19` P0-sensitive files with positive aggregate signals locally before any public tracking.
2. Decide explicit Git intake for `nexus_os/claw`, `tests/claw`, `nexus_os/__main__.py`, `nexus_os/cli.py`, and `nexus_os/stresslab/__init__.py`.
3. Execute P2 intake in explicit batches: canonical docs first, dataset manifests second, external skill references third, logs/evidence archive fourth.
4. Keep the 40 GiB Kilo quarantine until the sensitive and P1/P2 intake decisions are complete.
