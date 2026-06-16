# NEXUS Emergency Tidiness C: Scan - 2026-06-08

Read-only scan and dry-run approval matrix. No files were deleted or moved.

## Current Drive State

| Drive | Free | Used | Total | Free % | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `C:` | 83.86 GiB | 844.12 GiB | 927.98 GiB | 9.04% | Below healthy target |
| `D:` | 360.26 GiB | 570.48 GiB | 930.75 GiB | 38.71% | Good migration target |

Working threshold:

- Emergency floor: 50 GiB free.
- Operational floor: 100 GiB free.
- Healthy target: about 15% free on C:, approximately 139 GiB for this drive.
- Current gap to healthy target: about 55 GiB.

## What Was Wrong Last Time

| Finding | Current correction |
| --- | --- |
| Level 5 migration was real, but it looked like theater because the operator-facing audit did not surface the captured file moves. | Junctions are verified for `models`, `benchmarks`, `foundry_datasets`, `datasets`, `.git\objects`, and `.git\lfs` into `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS`. |
| Level 6 docs claimed Batch A completed, but current disk state contradicts that. | `D:\NEXUS_COLD\level6_quarantine_20260605` is absent, and `C:\Users\speci.000\.local\share\kilo\snapshot` still exists on C: as a normal directory. |
| Kilo was treated like a normal closed app. | Kilo is still live from `C:\Users\speci.000\.windsurf\extensions\kilocode.kilo-code-7.2.20-win32-x64\bin\kilo.exe`. The snapshot must not be moved while Kilo is live unless the approved process-stop gate is used. |
| The Level 6 tool had a stale hard-coded quarantine root and a dry-run estimate crash when all actions were blocked. | `scripts\nexus_level6_controlled_cleanup.ps1` now defaults to a date-current quarantine root and reports `estimated_c_gib_relieved=0` cleanly for blocked/no-relief runs. |
| Downloads was tempting but not a real priority. | Downloads remains protected because it contains NEXUS/GROSS/ARCHIVIST evidence. Current cleanup should not touch it blindly. |

## Current Large Targets

| Path | Size | Priority | Classification | Safe action |
| --- | ---: | --- | --- | --- |
| `C:\pagefile.sys` | 95.997 GiB | Level 6 | Windows virtual memory | Do not delete. Only admin pagefile policy change with reboot plan. |
| `C:\Users\speci.000\.local\share\kilo\snapshot` | 40.103 GiB | Level 2 | Kilo Git/LFS snapshot, sensitive session evidence | Stop Kilo, then quarantine/move to D. |
| `C:\Users\speci.000\AppData\Local\Packages\SpotifyAB.SpotifyMusic_zpdnekdrzrea0` | 14.643 GiB | Level 4 | Store app package/cache | Reset/uninstall via Windows app path only. |
| `C:\Users\speci.000\Music\DJ.Studio` | 12.231 GiB | Level 2/3 | Personal media | User already approved WAV purge; move/quarantine selected output first. |
| `C:\Users\speci.000\AppData\Local\wsl` | 11.631 GiB | Level 5 | WSL VHD/runtime | WSL-safe export/move/compact only. |
| `C:\Users\speci.00\osman-workspace` | 9.938 GiB | Level 4 | Different Windows profile model workspace | Cross-profile approval required. |
| `C:\Users\speci.000\.windsurf` | 9.639 GiB | Level 2 | Broken IDE state plus Kilo extension | Quarantine after stopping related devin/kilo processes. |
| `C:\Users\speci.000\AppData\Roaming\npm` | 6.518 GiB | Level 4 | Global npm CLI installs, not disposable cache | Do not global-purge; package-by-package only. |
| `C:\Users\speci.000\AppData\Local\Temp` | 5.270 GiB | Level 3/5 | Temp plus locked runtime VHD risk | Clean only after owner detection/shutdown. |
| `C:\Users\speci.000\AppData\Local\Docker` | 4.799 GiB | Level 5 | Docker Desktop VHD/logs | Docker-safe cleanup/relocation only. |
| `Chrome Service Worker + model/cache paths` | 8.893 GiB | Level 3 | Browser cache/on-device model | Close Chrome, then cache cleanup only. |
| `C:\Users\speci.000\AppData\Roaming\Jan` | 3.569 GiB | Level 2 | Unused Jan model/app state | Quarantine approved. |
| `C:\Users\speci.000\AppData\Roaming\Notion` | 3.228 GiB | Level 1/2 | Electron cache/app state | Quarantine cache folders only. |
| `C:\Users\speci.000\AppData\Roaming\slobs-client` | 3.065 GiB | Level 3 | Streamlabs OBS app state | Cache-only; do not touch Media. |
| `C:\Users\speci.000\.cursor` | 2.764 GiB | Level 2 | Unused Cursor state | Quarantine approved. |
| `C:\MyFlaskAI` | 2.344 GiB | Level 4 | Legacy SEQUENCE/Flask project pack | Quarantine only after explicit legacy approval. |
| `C:\tmp` | 2.207 GiB | Level 4 | Temporary clones/build artifacts | Quarantine after active-shell check. |
| `NEXUS node_modules` | 1.662 GiB | Level 1 | Rebuildable project cache | Optional move/junction or reinstall cleanup. |

## Six-Level Cleanup Matrix

| Level | Scope | Expected C: relief | Risk | Approval |
| --- | --- | ---: | --- | --- |
| 0 | No-op health check: drive free space, process owners, junction verification, audit tail. | 0 GiB | None | No approval needed |
| 1 | Rebuildable caches only: NEXUS `node_modules`, small app caches, no browser/session stores. | 1-4 GiB | Low | Confirm cache-only |
| 2 | Approved stale app quarantine: Kilo snapshot, broken Windsurf, unused Cursor, unused Jan, Notion cache, selected DJ WAV. | 63.145 GiB | Medium because Kilo/Windsurf processes must stop | Recommended Batch A |
| 3 | Browser/media runtime caches: Chrome cache/model paths, Streamlabs cache-only, Temp after owner detection. | 10-16 GiB | Medium, requires app shutdown | Separate approval |
| 4 | Legacy project/profile migration: `C:\MyFlaskAI`, `C:\tmp`, `C:\GitHubVs`, `speci.00\osman-workspace`, Spotify app reset. | 20-28 GiB | Medium/high, mixed provenance | Separate approval |
| 5 | WSL/Docker migration/compact: WSL VHD, Docker VHD/logs. | 4-16 GiB | High, runtime/service risk | Explicit shutdown/export plan |
| 6 | Windows policy: pagefile/hibernation/update residues. | up to 96 GiB | Very high, admin/reboot risk | Only if lower levels fail |

## Verified Dry Runs

Recommended Batch A:

```powershell
python -m nexusctl disk-rescue level6 --execute --stop-approved-processes --approved-stale-apps --notion-caches --kilo-snapshot --quarantine-root D:\NEXUS_COLD\level6_quarantine_20260608
```

Dry-run estimate:

- Stops only approved matched processes for selected actions: 6 Windsurf `devin.exe` processes and 1 Kilo process.
- Moves Kilo snapshot, broken Windsurf state, unused Cursor state, unused Jan state, selected DJ WAV, and Notion cache partitions to D quarantine.
- Does not touch Downloads, npm globals, Program Files, ProgramData, WSL, Docker, Spotify, Chrome, Streamlabs, or cross-profile `speci.00`.
- Estimated C: relief: 63.145 GiB.
- Estimated C: after execution: about 146.99 GiB free, about 15.84%, which reaches the healthy target.

Optional Batch B:

```powershell
python -m nexusctl disk-rescue level6 --execute --legacy-project-candidates --quarantine-root D:\NEXUS_COLD\level6_quarantine_20260608
```

Dry-run estimate:

- Moves `C:\MyFlaskAI`, `C:\tmp`, and `C:\GitHubVs` to D quarantine.
- Estimated extra C: relief: 5.637 GiB.
- Requires separate approval because these are project/workspace folders.

Do not run yet without explicit operator approval.

