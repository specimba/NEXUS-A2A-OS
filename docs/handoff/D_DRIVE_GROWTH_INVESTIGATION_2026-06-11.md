# D Drive Growth Investigation - 2026-06-11

## Scope

Read-only investigation of D: free-space collapse. No files were moved or deleted.

Current check timestamp: `2026-06-11T02:08:34.5249807+03:00`

## Current Disk State

| Drive | Free bytes | Free GiB | Used GiB |
|---|---:|---:|---:|
| `D:` | `33712013312` | `31.40` | `899.35` |

Last recorded post-purge D: free value from the Kilo closeout was `184212033536` bytes. Current delta is `150500020224` bytes, or `140.16 GiB` less free space.

## Source-Ranked Evidence Matrix

| Evidence | Strength | Finding |
|---|---|---|
| `Get-PSDrive D` live counter | High | D: has `31.40 GiB` free and `899.35 GiB` used. |
| D: 24-hour recursive file scan | High | `8212` recent files found; visible recent growth is led by `D:\NEXUS_COLD\level7_backup_20260610` at `31.33 GiB`. |
| D: root visible size scan | High | Readable root data totals far below reported used space; visible top roots are `NEXUS_COLD 214.699 GiB`, `NEXUS_RECOVERY 79.319 GiB`, `Backu 74.098 GiB`, `ollama_models 24.775 GiB`, `$RECYCLE.BIN 13.174 GiB`. |
| Level7 backup live-vs-backup compare | High | Checked roots had `0` backup-only files and only tiny source-size differences, so the `31.327 GiB` level7 backup is a duplicate of live NEXUS data for the checked scope. |
| `Downloads\NEXUSlogs` lines in `NEXUSbenchmarkMODELresearchlog-04.txt` | High | Agent work used `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS` as an active workspace and wrote dataset outputs there. |
| Elevated VSS/fsutil/chkdsk attempts | Medium | `vssadmin`, `fsutil`, and `chkdsk D:` were blocked by privilege/lock errors, leaving protected/system allocation unresolved. |

Actionable insight: the immediate visible 24-hour dump is the redundant `level7_backup_20260610`, but the larger D: pressure is a cold-storage policy problem: old rescue copies, model caches, and protected/unreadable allocation are all competing on the same disk.

## Confirmed Last-24h Growth

Cutoff used: `2026-06-10T01:51:38.2314200+03:00`

| Prefix | Recent GiB | Recent files | Latest write |
|---|---:|---:|---|
| `D:\NEXUS_COLD\level7_backup_20260610` | `31.33` | `5398` | `2026-06-10 21:07:59` |
| `D:\NEXUS_COLD\level5_migrations_20260605` | `16.64` | `2561` | `2026-06-11 01:49:48` |
| `D:\ollama_models\blobs` | `0.53` | `244` | `2026-06-11 01:40:56` |
| `D:\NEXUS_OS_AUDIT\logs` | `0.01` | `6` | `2026-06-11 01:51:47` |

### `level7_backup_20260610` Breakdown

| Path | GiB | Files |
|---|---:|---:|
| `D:\NEXUS_COLD\level7_backup_20260610\NEXUS\models` | `26.099` | `3236` |
| `D:\NEXUS_COLD\level7_backup_20260610\NEXUS\benchmarks` | `2.784` | `281` |
| `D:\NEXUS_COLD\level7_backup_20260610\NEXUS\research` | `1.335` | `449` |
| `D:\NEXUS_COLD\level7_backup_20260610\NEXUS\datasets` | `1.067` | `1298` |
| `D:\NEXUS_COLD\level7_backup_20260610\NEXUS\upload` | `0.037` | `71` |

Extension weight inside level7:

| Extension | GiB | Files |
|---|---:|---:|
| `.safetensors` | `17.263` | `23` |
| `.gguf` | `8.405` | `25` |
| `.jsonl` | `2.151` | `204` |
| `.parquet` | `0.982` | `22` |
| `.pdf` | `0.891` | `287` |
| `.arrow` | `0.867` | `18` |

Live NEXUS comparison:

| Scope | Live GiB | Level7 backup GiB | Result |
|---|---:|---:|---|
| `models` | `26.857` | `26.099` | Backup is not larger than live. |
| `benchmarks` | `2.784` | `2.784` | Size match. |
| `research` | `1.335` | `1.335` | Size match. |
| `datasets` | `1.067` | `1.067` | Size match. |
| checked file-path diff | n/a | n/a | `0` backup-only files; `91` tiny size differences totaling about `0.01 GiB`. |

Decision: `level7_backup_20260610` is a strong purge candidate after confirmation because it appears to duplicate live NEXUS models, benchmarks, research, datasets, upload, logs, and vault paths.

## Persistent Large D: Chunks

| Path | GiB | Files | Classification | Initial action |
|---|---:|---:|---|---|
| `D:\NEXUS_COLD\migrated_from_C` | `120.191` | `428323` | Emergency user-profile migration from C: | Candidate for staged purge after rollback window closes. |
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529` | `79.319` | `301804` | Full June 5 NEXUS recovery copy | Candidate for archive/delete after verifying no unique recovery need remains. |
| `D:\Backu` | `74.098` | `7320` | Older personal/backup folder | User-review only; do not delete blindly. |
| `D:\NEXUS_COLD\level5_migrations_20260605` | `63.181` | `16505` | Cold NEXUS migration copy, currently touched by agents | Freeze as read-only; stop agents using it as workspace. |
| `D:\ollama_models` | `24.775` | `297` | Local Ollama model store | Keep until model manifest says unused. |
| `D:\$RECYCLE.BIN` | `13.174` | `38` | Old deleted ZIPs and small metadata | Low-risk purge after confirmation. |
| `D:\MyModels` | `6.367` | `10` | Manual model store | Review before purge. |

## `migrated_from_C` Breakdown

| Path | GiB | Files | Meaning |
|---|---:|---:|---|
| `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\AppData\Local\pnpm` | `81.274` | `420028` | Duplicated pnpm/project store, includes Git/LFS/model payloads. |
| `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\.lmstudio` | `38.918` | `8295` | Duplicated LM Studio model cache. |

Largest files include Qwen/Gemma safetensors and GGUF blobs plus pnpm Git-LFS model object duplicates. This is not canonical NEXUS source; it is a broad user-profile rescue copy.

## `NEXUS_RECOVERY` Breakdown

| Path | GiB | Files | Meaning |
|---|---:|---:|---|
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\.git` | `41.470` | `11851` | Huge Git object database from recovery copy. |
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\models` | `25.099` | `228` | Duplicate model payloads. |
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\benchmarks` | `2.784` | `279` | Duplicate benchmark payloads. |
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\foundry_datasets` | `2.757` | `218` | Duplicate dataset payloads. |
| `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\node_modules` | `1.662` | `147433` | Disposable dependency tree. |

## Agent Log Correlation

`C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSbenchmarkMODELresearchlog-04.txt` contains direct evidence that an agent ran dataset fusion from the cold backup path:

- Outputs were written to `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS\datasets\fused_*.jsonl`.
- The log explicitly identifies a "smoking gun" path split between canonical `C:\Users\speci.000\Documents\NEXUS` and cold backup `D:\NEXUS_COLD\level5_migrations_20260605\NEXUS`.

This means future agents must be told: do not run builds, tests, scripts, or dataset fusion from `D:\NEXUS_COLD`; use it only as cold storage unless explicitly approved.

## Hidden Allocation Gap

Visible readable root data sums to about `421.71 GiB`, but D: reports `899.35 GiB` used. Protected allocation remains unresolved because these read-only checks were blocked:

```powershell
vssadmin list shadowstorage
vssadmin list shadows
fsutil volume diskfree D:
chkdsk D:
```

All returned privilege or lock errors in this environment. Run them from a true Administrator PowerShell if the visible cleanup does not restore enough free space.

## Ranked Cleanup Plan Requiring Confirmation

| Rank | Candidate | Reclaim GiB | Risk | Reason |
|---:|---|---:|---|---|
| 1 | Empty `D:\$RECYCLE.BIN` | `13.174` | Low | Already deleted items, mostly old ZIPs from 2024. |
| 2 | Delete `D:\NEXUS_COLD\level7_backup_20260610` | `31.327` | Low-Medium | New duplicate backup; checked scope has `0` backup-only files. |
| 3 | Delete `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\AppData\Local\pnpm` | `81.274` | Medium | Duplicated pnpm/Git-LFS model cache inside cold user-profile migration. |
| 4 | Delete `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\.lmstudio` | `38.918` | Medium | Duplicated LM Studio model cache inside cold user-profile migration. |
| 5 | Delete entire `D:\NEXUS_COLD\migrated_from_C` | `120.191` | Medium-High | Fastest cleanup if June 5 C: profile rollback is no longer needed. |
| 6 | Delete `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\node_modules` | `1.662` | Low | Disposable dependency tree inside recovery copy. |
| 7 | Delete/archive entire `D:\NEXUS_RECOVERY\NEXUS_20260605_140529` | `79.319` | Medium-High | Full old repo recovery copy; verify no unique recovery need first. |
| 8 | Review `D:\Backu` | `74.098` | High | Personal/legacy backups; must not purge blindly. |
| 9 | Review `D:\ollama_models` | `24.775` | High | Could be active Ollama model store. |

## Recommended Immediate Choice

For a safe first pass, ask for confirmation to run only ranks 1 and 2. That should recover about `44.50 GiB` with low operational risk and bring D: from about `31.40 GiB` free to about `75.90 GiB` free, before touching old recovery or personal backup material.

For a stronger second pass, approve ranks 1, 2, 3, and 4. That should recover about `164.69 GiB`, mostly from duplicate backup/cache material, while leaving the broader recovery copies intact.

Do not approve ranks 7-9 until recovery uniqueness and personal-backup value are reviewed.
