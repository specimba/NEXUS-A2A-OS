# D: Balanced Cleanup Execution - 2026-06-11

## Scope

Operator-selected profile: `Balanced`.

Deleted only the approved redundant backup/cache surfaces:

- `D:\$RECYCLE.BIN`
- `D:\NEXUS_COLD\level7_backup_20260610`
- `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\AppData\Local\pnpm`
- `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\.lmstudio`

Protected paths were not targeted:

- `D:\ollama_models`
- `D:\Ollama_Backup`
- `D:\NEXUS_RECOVERY`
- `D:\Backu`
- `D:\GROSS`
- `C:\Users\speci.000\Documents\NEXUS`

## Disk Result

| Checkpoint | D: free | D: used |
|---|---:|---:|
| Pre-delete, `2026-06-11T04:35:12.4183404+03:00` | 36.26 GiB | 894.48 GiB |
| Post-delete, `2026-06-11T05:07:15.2331936+03:00` | 201.65 GiB | 729.09 GiB |

Approximate reclaimed space: `165.39 GiB`.

## Target Verification

| Path | Exists After | Files | Size |
|---|---:|---:|---:|
| `D:\NEXUS_COLD\level7_backup_20260610` | false | 0 | 0.000 GiB |
| `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\AppData\Local\pnpm` | false | 0 | 0.000 GiB |
| `D:\NEXUS_COLD\migrated_from_C\Users\speci.000\.lmstudio` | false | 0 | 0.000 GiB |

The pnpm cache initially left a reserved-name `nul` file residue at `246` bytes. It was removed with a guarded extended-path delete limited to the approved pnpm target tree.

## Protected Area Verification

| Path | Exists | Files | Size |
|---|---:|---:|---:|
| `D:\NEXUS_RECOVERY` | true | 301,804 | 79.320 GiB |
| `D:\ollama_models` | true | 291 | 19.910 GiB |
| `D:\GROSS` | true | 5,531 | 1.220 GiB |
| `D:\Ollama_Backup` | true | 68 | 0.000 GiB |
| `D:\Backu` | true | 7,320 | 74.100 GiB |

## Prevention Change

Updated `scripts/cold_storage_backup.py` so future cold-storage runs cannot silently recreate the same pressure pattern:

- Default invocation is manifest-first dry run; no copy happens unless `--full` is passed.
- Full backup is refused if cold-storage free space is below `120 GiB`.
- Retention pruning runs automatically after every full backup; `--prune` is retained only as a compatibility flag.
- `backup_directory()` resolves `SOURCE_ROOT` at call time instead of capturing it at import time.
- Fixed `print_summary()` large-file reporting, which referenced a missing `manifest.large_gb` attribute.

## Verification

Command:

```powershell
python -m pytest tests/scripts -v --tb=short -p no:cacheprovider
```

Result: `23 passed in 11.94s`.

Full repository test suite was not run because this pass changed only a cleanup utility and added focused script-layer regression tests in an already dirty workspace.
