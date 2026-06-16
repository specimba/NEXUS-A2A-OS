# Level 5 Disk Rescue And Audit Check - 2026-06-05

## Current State

- C: recovered from near-zero/unstable free space to 95.58 GiB free after Level 5 migration.
- D: is now the cold storage target for large NEXUS project and Git storage.
- The main pressure source was not the moved folders themselves. Active `git.exe` and `git-lfs.exe` processes were writing large loose objects under `.git\objects` while cleanup was running.
- Repository read check passed after migration with `git -c status.showUntrackedFiles=no status --short`.

## Executed Moves

| Source | Destination | Action | Result |
|---|---|---|---|
| `C:\Users\speci.000\Documents\NEXUS\models` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\models` | Move + junction | Done |
| `C:\Users\speci.000\Documents\NEXUS\benchmarks` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\benchmarks` | Move + junction | Done |
| `C:\Users\speci.000\Documents\NEXUS\foundry_datasets` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\foundry_datasets` | Move + junction | Done |
| `C:\Users\speci.000\Documents\NEXUS\datasets` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\datasets` | Move + junction | Done |
| `C:\Users\speci.000\Documents\NEXUS\.git\lfs` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\.git\lfs` | Move + junction | Done |
| `C:\Users\speci.000\Documents\NEXUS\.git\objects` | `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\.git\objects` | Move + junction | Done |

## Verification

- Junction verification passed for `models`, `benchmarks`, `foundry_datasets`, `datasets`, `.git\lfs`, and `.git\objects`.
- C/D drive check after migration: C free 95.58 GiB, D free 129.84 GiB.
- Git check after migration showed only six existing tracked modifications:
  - `nexus_os/__init__.py`
  - `nexus_os/bridge/server.py`
  - `nexus_os/cron/__init__.py`
  - `nexus_os/db/__init__.py`
  - `nexus_os/engine/__init__.py`
  - `pyproject.toml`

## Remaining C: Pressure Matrix

| Candidate | Size | Priority | Recommendation |
|---|---:|---|---|
| `C:\Users\speci.000\AppData\Local\Packages\SpotifyAB.SpotifyMusic_zpdnekdrzrea0` | 12.31 GiB | Low project value, app cache/package risk | Do not manual-delete blindly. Uninstall/reset app or cache-clean with user approval. |
| `C:\Users\speci.000\AppData\Local\Google\Chrome\User Data\Default\Service Worker` | 4.68 GiB | Low project value, browser state risk | Clear Chrome site data/cache only after closing Chrome and confirming browser session safety. |
| `C:\Users\speci.000\AppData\Local\Google\Chrome\User Data\OptGuideOnDeviceModel` | 3.98 GiB | Low project value | Candidate for Chrome model/cache cleanup after Chrome shutdown. |
| `C:\Users\speci.000\AppData\Local\wsl\{78ec8773-4856-4cdf-be73-4b6b2177e602}` | 11.60 GiB | Medium/high runtime value | Move/export only through WSL-safe procedure, not direct file move. |
| `C:\Users\speci.000\AppData\Local\Docker\wsl` | 4.75 GiB | Medium runtime value | Use Docker/WSL shutdown and Docker-supported relocation/cleanup only. |
| `C:\Users\speci.000\AppData\Local\Temp\DABD0504-A782-4440-82DE-9C4D759FEED7` | 4.00 GiB | Likely runtime temp VHD | Locked by Docker/WSL-like runtime; do not force while mounted. |
| `C:\Users\speci.000\Documents\NEXUS\node_modules` | 1.66 GiB | Rebuildable project cache | Safe next project-level D junction candidate. |
| `C:\Users\speci.000\Documents\NEXUS\.nexus-worktrees` | 1.34 GiB | Project state | Move only after checking worktree status. |
| `C:\Users\speci.000\Documents\NEXUS\research` | 1.33 GiB | Evidence/research | Keep or move with junction, not delete. |
| `C:\Users\speci.000\AppData\Local\hermes\hermes-agent` | 2.49 GiB | Active agent surface | Do not delete. Consider D relocation only with Hermes config update. |

## Audit Finding

The Windows audit stack did not completely fail.

- `Sysmon` service is running and `SysmonDrv` is running.
- `D:\NEXUS_OS_AUDIT\logs\realtime\nexus_sysmon_20260605.jsonl` is current and growing.
- `D:\NEXUS_OS_AUDIT\config\sysmon_bookmark.json` is advancing.
- `D:\NEXUS_OS_AUDIT\logs\realtime\watchdog_20260605.log` reports healthy forwarder status through the afternoon.
- Sysmon captured the Level 5 `.git\objects` move at `2026-06-05T12:12Z`, including file-delete records and recreation of `.git\objects`.

The real gaps:

- The old monitor/automation did not consume `D:\NEXUS_OS_AUDIT\logs\realtime\*.jsonl`, so captured events were not surfaced to the operator.
- Sysmon config covers file create/delete for `Documents\NEXUS`, `.grok`, and `GROSS`; it is not a full filesystem backup or snapshot layer.
- Native SACL/auditpol verification still requires administrator privileges and could not be proven from Codex.
- The no-admin FileSystemWatcher script exists but was not proven active in this check.
- D: target paths such as `D:\NEXUS_COLD` are not part of the current Sysmon path filter unless the source path also matches.

## Next Level 5 Options Requiring Confirmation

1. Move rebuildable NEXUS project caches to D with junctions: `node_modules`, `.next`, `venv`, `.venv`, `tests_tmp`. Expected gain: about 2.4 GiB.
2. Run a Chrome-safe cache cleanup after closing Chrome: Service Worker, Code Cache, Cache, and on-device model caches. Expected gain: about 5 to 9 GiB.
3. Run a WSL/Docker-safe cleanup pass after explicit shutdown/export decision. Expected gain: about 4 to 16 GiB depending on Docker/WSL profile retention.
4. Convert the audit forwarder into an operator-facing sentinel that reads only the latest JSONL tail and reports high-risk deletes/moves under NEXUS, `.grok`, and GROSS.

