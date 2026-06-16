# Kilo Snapshot P1 Code Agent Intake - 2026-06-08

## Scope

This intake covers the `P1_code_agent` rows from `docs/handoff/KILO_SNAPSHOT_LIVE_UNTRACKED_PROTECTION_MATRIX_2026-06-08.csv`.

These are live untracked files where Kilo has older snapshot blobs. They are not direct restore targets. They are current local work that needs protection before any purge of the Kilo quarantine or further cleanup.

## Decision Matrix

| Path | Status | Decision | Evidence |
|---|---|---|---|
| `nexus_os/__main__.py` | Live untracked | Preserve as CLI entrypoint candidate; review before tracking. | `python -m nexus_os.cli version` returned `NEXUS OS version 3.0.0`. |
| `nexus_os/cli.py` | Live untracked | Preserve as lightweight package CLI candidate; review before tracking. | `python -m nexus_os.cli version` returned `NEXUS OS version 3.0.0`. |
| `nexus_os/stresslab/__init__.py` | Live untracked | Preserve. It prevents eager stresslab imports from triggering ModelRelay health polling. | Focused stresslab recovery tests passed. |
| `tests/claw/test_config_integrity.py` | Live untracked | Preserve with the broader `nexus_os/claw` module intake. | Included in `tests/claw`; passed. |
| `tests/claw/test_locks.py` | Live untracked | Preserve with the broader `nexus_os/claw` module intake. | Included in `tests/claw`; passed. |
| `tests/claw/test_store.py` | Live untracked | Preserve with the broader `nexus_os/claw` module intake. | Included in `tests/claw`; passed. |

## Broader Module Found

The P1 tests point to a larger live untracked `nexus_os/claw` runtime:

- `23` non-`.pyc` files under `nexus_os/claw`
- `48,151` bytes total
- `11` non-`.pyc` files under `tests/claw`
- `34,898` bytes total

Primary surfaces found:

- Config integrity hash pinning: `nexus_os/claw/security/config_integrity.py`
- Secret scanning: `nexus_os/claw/security/secret_scanner.py`
- Session write locks: `nexus_os/claw/locks.py`
- Preference/tier store: `nexus_os/claw/store.py`
- Model tier and trust threshold mapping: `nexus_os/claw/tiers.py`
- Policy preset validation: `nexus_os/claw/policies/validator.py`
- Parallel/retry runner: `nexus_os/claw/runners/runner.py`

## Verification

P1 hygiene scan:

- Scope: `nexus_os/claw`, `tests/claw`, `nexus_os/__main__.py`, `nexus_os/cli.py`, `nexus_os/stresslab/__init__.py`
- Files scanned: `37`
- Files with configured secret-like patterns: `1`
- Signal file: `tests/claw/test_secret_scanner.py`
- Decision: expected synthetic scanner fixtures, not runtime credentials. Do not copy fixture values into docs.

Command:

```powershell
python -m pytest tests\claw -v --tb=short -p no:cacheprovider
```

Result:

- `99 passed in 1.15s`

Command:

```powershell
python -m nexus_os.cli version
```

Result:

- `NEXUS OS version 3.0.0`

## Disposition

Preserve the P1 rows and the broader `nexus_os/claw` module as a protected intake set. Do not purge Kilo until these files are either tracked, archived with hashes, or explicitly rejected.

Recommended next action:

1. If accepting this intake, stage explicit source/test paths only, not `git add .`.
2. Keep generated `__pycache__` files ignored/untracked.
3. Do not purge Kilo until P0 sensitive rows and P2 docs/data rows have a reviewed disposition.
