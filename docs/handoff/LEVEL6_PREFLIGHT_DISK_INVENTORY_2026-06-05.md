# Level 6 Preflight Disk Inventory - 2026-06-05

Read-only inventory before any last-level cleanup/migration.

## Drive State

| Drive | Free | Used | Note |
|---|---:|---:|---|
| C: | 94.12 GiB | 833.86 GiB | Stable after Level 5 Git/project junction migration |
| D: | 132.72 GiB | 798.03 GiB | Current cold-storage target |

## Largest C: Root Buckets

| Path | Size | Classification | Risk |
|---|---:|---|---|
| `C:\Users` | 249.95 GiB | User data, app state, developer caches | Mixed |
| `C:\Windows` | 44.99 GiB | OS | Do not manual-delete |
| `C:\Program Files` | 30.14 GiB | Installed software | Use uninstallers only |
| `C:\ProgramData` | 24.52 GiB | App/system data, package caches | Use app-specific cleanup |
| `C:\Program Files (x86)` | 18.51 GiB | Installed software | Use uninstallers only |
| `C:\$WinREAgent` | 2.44 GiB | Windows update/recovery residue | Candidate only after Windows update health check |
| `C:\MyFlaskAI` | 2.34 GiB | Legacy project/backups | Move/archive candidate |
| `C:\tmp` | 2.21 GiB | Temporary project clones | Clean/move candidate |
| `C:\GitHubVs` | 1.09 GiB | Legacy/dev workspace | Move/archive candidate |
| `C:\home` | 0.75 GiB | User/dev path | Review before action |

## Single Largest Files

| Path | Size | Last Write | Classification | Recommendation |
|---|---:|---|---|---|
| `C:\pagefile.sys` | 96.00 GiB | 2026-06-02 | System virtual memory | Do not delete. Last-level system-setting candidate: cap or move pagefile after RAM/admin confirmation and reboot plan. |
| `C:\Users\speci.000\.local\share\kilo\snapshot\...\*` | 40.10 GiB total | 2026-06-05 | Kilo snapshot cache | Best high-impact app-cache target. Stop Kilo first, then move to D with junction or prune using Kilo-supported path. |
| `C:\Users\speci.000\AppData\Local\wsl\{...}\ext4.vhdx` | 11.60 GiB | 2026-06-05 | WSL distro disk | WSL-safe export/move/compact only. Do not raw-delete. |
| `C:\Users\speci.00\osman-workspace\*.gguf` | 9.94 GiB total | 2026-04-10 | Secondary profile model files | Move to D/archive candidate after confirming `speci.00` is legacy. |
| `C:\Users\speci.000\AppData\Local\Docker\wsl\disk\docker_data.vhdx` | 4.65 GiB | 2026-06-05 | Docker Desktop VHD | Docker-safe cleanup/relocation only. |
| `C:\Users\speci.000\AppData\Local\Temp\...\swap.vhdx` | 4.00 GiB | 2026-06-05 | Locked runtime temp VHD | Requires identifying runtime owner/shutdown. Do not force. |
| `C:\Users\speci.000\AppData\Local\Google\Chrome\User Data\OptGuideOnDeviceModel\...` | 3.98 GiB | 1980 timestamp | Chrome on-device model/cache | Cleanup after Chrome shutdown. |
| `C:\Users\speci.000\AppData\Roaming\Jan\data\llamacpp\models\...` | 2.79 GiB | 2026-03-17 | Jan local model | Move/delete candidate after confirming not used. |
| `C:\Users\speci.000\Music\DJ.Studio\Exports\2212chilldeepmix.wav` | 2.05 GiB | 2024-12-22 | Personal media | Move to D only with user approval. |
| `C:\ProgramData\Package Cache\...\Ableton...` | 2.00 + 1.96 GiB | 2025-02-26 | Installer cache | Use app/vendor-aware cleanup only. |

## User / Personal / Developer Buckets

| Path | Size | Classification | Recommendation |
|---|---:|---|---|
| `C:\Users\speci.000\AppData` | 119.27 GiB | App state/caches | Main remaining pressure zone |
| `C:\Users\speci.000\.local` | 41.25 GiB | CLI/tool local state | Kilo snapshot dominates; high-impact target |
| `C:\Users\speci.000\Documents` | 17.63 GiB | Personal/projects | Move/archive selected legacy projects only |
| `C:\Users\speci.000\Music` | 13.03 GiB | Personal media | Move to D if user approves |
| `C:\Users\speci.000\.windsurf` | 9.64 GiB | IDE worktrees/extensions | Review/move stale worktrees |
| `C:\Users\speci.000\.unsloth` | 5.14 GiB | ML/app cache | Move/archive candidate |
| `C:\Users\speci.000\Downloads` | 3.91 GiB | Mixed evidence/downloads | Do not clean blindly; contains active NEXUS/GROSS logs |
| `C:\Users\speci.000\.bun` | 3.17 GiB | Package cache/bin | Prune cache candidate |
| `C:\Users\speci.000\.cursor` | 2.76 GiB | IDE worktrees/extensions | Review/move stale worktrees |
| `C:\Users\speci.000\.vscode` | 2.46 GiB | Extensions | Low priority |
| `C:\Users\speci.000\.ollama` | 2.24 GiB | Local model blobs | Preserve unless model inventory says stale |
| `C:\Users\speci.000\.codex` | 1.10 GiB | Codex sessions/plugins | Do not clean during active recovery |

## AppData Hotspots

| Path | Size | Classification | Recommendation |
|---|---:|---|---|
| `AppData\Local\Packages\SpotifyAB.SpotifyMusic_zpdnekdrzrea0` | 12.36 GiB | Store app package/cache | Reset/uninstall via app path only; do not raw-delete package. |
| `AppData\Local\Google\Chrome` | 13.20 GiB | Browser profile/cache | Close Chrome first; clear cache/model data carefully. |
| `AppData\Local\Programs\Ollama` | 6.55 GiB | Installed app/runtime | Do not delete; uninstall/relocate only if planned. |
| `AppData\Local\wsl` | 11.60 GiB | WSL VHD | WSL-safe export/move/compact only. |
| `AppData\Local\Docker` | 4.81 GiB | Docker Desktop VHD/logs | Docker-safe cleanup only. |
| `AppData\Local\Temp` | 5.28 GiB | Temp/runtime | Locked VHD dominates; shutdown owner first. |
| `AppData\Local\hermes` | 2.60 GiB | Hermes agent surface | Preserve unless Hermes relocation is planned. |
| `AppData\Roaming\npm` | 6.52 GiB | Global Node packages/cache | Review package list; prune with npm-aware commands only. |
| `AppData\Roaming\Notion` | 3.23 GiB | App cache | App cleanup candidate. |
| `AppData\Roaming\slobs-client` | 3.06 GiB | Media/cache | Cleanup candidate if not active. |

## Project / Software Buckets

| Path | Size | Classification | Recommendation |
|---|---:|---|---|
| `C:\ProgramData\Ableton` | 9.91 GiB | Installed audio content | Preserve unless user wants audio cleanup. |
| `C:\ProgramData\Package Cache` | 5.47 GiB | Installer cache | Avoid raw deletion unless using Windows/app cleanup strategy. |
| `C:\ProgramData\NVIDIA Corporation` | 3.79 GiB | GPU software/cache | Low priority; vendor cleanup only. |
| `C:\Program Files\Docker` | 4.22 GiB | Installed Docker | Preserve. |
| `C:\Program Files\Python313` | 4.15 GiB | Python runtime/dev | Preserve unless duplicate runtime strategy exists. |
| `C:\Program Files\NVIDIA GPU Computing Toolkit` | 4.08 GiB | CUDA | Preserve for ML/runtime unless intentionally downsizing. |
| `C:\Program Files (x86)\Microsoft Visual Studio` | 3.45 GiB | Dev tooling | Preserve unless workload cleanup is planned. |
| `C:\MyFlaskAI\BACKUPS` | 2.14 GiB | Legacy project backups | Good move/archive candidate. |
| `C:\tmp\nexusalpha-safe-push` | 1.24 GiB | Temporary clone | Good cleanup/archive candidate. |
| `C:\tmp\nexus-governed-mcp-python-clone` | 0.87 GiB | Temporary clone | Good cleanup/archive candidate. |

## Downloads

Downloads is only 3.91 GiB and contains active evidence inputs. It is not a priority cleanup target.

| Path | Size | Recommendation |
|---|---:|---|
| `Downloads\grokIMAGINEtestv1` | 1.99 GiB | Image output; can archive/delete if unrelated. |
| `Downloads\PAPERS` | 0.74 GiB | Research; keep or move to D evidence archive. |
| `Downloads\ERNIEsupramacyRESEARCH` | 0.31 GiB | Research; keep or move to D evidence archive. |
| `Downloads\ARCHIVIST` | 0.04 GiB | Keep. |
| `Downloads\NEXUSlogs` | 0.01 GiB | Keep. |
| `Downloads\GROSSlogs` | 0.01 GiB | Keep. |

## Live Process Constraints

- `kilo` is running; do not touch `.local\share\kilo\snapshot` until stopped.
- Many `chrome.exe` processes are running; do not clean Chrome profile/cache until Chrome is closed.
- `Codex` is running; do not clean `.codex` during active recovery.
- WSL enumeration returned access denied; WSL VHD work needs a separate approved shutdown/export/compact procedure.

## Last-Level Recommendation

The best last-level order is:

1. Stop Kilo and move `C:\Users\speci.000\.local\share\kilo\snapshot` to D with a junction. Expected C relief: about 40 GiB. This is the highest clean gain without touching OS settings.
2. Move/archive secondary profile model workspace `C:\Users\speci.00\osman-workspace` to D. Expected relief: about 9.94 GiB.
3. Close Chrome and clean browser cache/model data. Expected relief: about 5 to 9 GiB.
4. Move personal DJ Studio media to D only with explicit user approval. Expected relief: about 12.23 GiB.
5. Run WSL/Docker-safe shutdown, compact, or relocation. Expected relief: about 4 to 16 GiB, but higher operational risk.
6. Pagefile policy change is separate: `C:\pagefile.sys` is 96 GiB. This can reclaim the most space but requires admin/system-setting confirmation and likely reboot. Do not delete it directly.

