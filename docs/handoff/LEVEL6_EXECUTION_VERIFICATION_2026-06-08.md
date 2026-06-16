# Level 6 Execution Verification - 2026-06-08

Purpose: verify the operator-provided Level 6 cleanup log and determine whether the command actually executed.

## Verdict

The Level 6 cleanup **did execute**.

It was not a no-op. It stopped approved stale Kilo/Windsurf/Devin processes, moved approved stale app/cache targets to D: quarantine, removed the Kilo snapshot from C:, and restored C: above the healthy target.

## Operator Log Summary

Command run:

```powershell
python -m nexusctl disk-rescue level6 --execute --stop-approved-processes --approved-stale-apps --notion-caches --kilo-snapshot --quarantine-root D:\NEXUS_COLD\level6_quarantine_20260608
```

Before:

- `C:` free: `83.42 GiB`
- `D:` free: `357.39 GiB`

After:

- `C:` free: `144.34 GiB`
- `D:` free: `259.49 GiB`

Tool-reported estimate:

- `estimated_c_gib_relieved=63.145`

## Post-State Verification

Current live drive check:

| Drive | Free | Used | Total | Free % |
| --- | ---: | ---: | ---: | ---: |
| `C:` | `144.28 GiB` | `783.70 GiB` | `927.98 GiB` | `15.55%` |
| `D:` | `259.49 GiB` | `671.26 GiB` | `930.75 GiB` | `27.88%` |

Current quarantine root:

`D:\NEXUS_COLD\level6_quarantine_20260608`

- Exists: yes
- Size: `63.144 GiB`
- Files: `88414`
- Last write: `2026-06-08T02:16:44+03:00`

Largest quarantined payloads:

| Quarantine item | Size | Files |
| --- | ---: | ---: |
| `Users_speci.000_.local_share_kilo_snapshot` | `40.103 GiB` | `2506` |
| `Users_speci.000_.windsurf` | `9.639 GiB` | `23330` |
| `Users_speci.000_AppData_Roaming_Jan` | `3.569 GiB` | `2571` |
| `Users_speci.000_AppData_Roaming_Notion_Partitions` | `3.166 GiB` | `29628` |
| `Users_speci.000_.cursor` | `2.764 GiB` | `24361` |
| `Users_speci.000_Music_DJ.Studio_Exports_2212chilldeepmix.wav` | `2.049 GiB` | `1` |
| `Users_speci.000_AppData_Roaming_Windsurf` | `1.309 GiB` | `4622` |
| `Users_speci.000_AppData_Roaming_Cursor` | `0.431 GiB` | `1385` |

## Source Paths Removed From C:

All checked source paths now report missing on C:

- `C:\Users\speci.000\.local\share\kilo\snapshot`
- `C:\Users\speci.000\.windsurf`
- `C:\Users\speci.000\AppData\Roaming\Windsurf`
- `C:\Users\speci.000\AppData\Local\Programs\Windsurf`
- `C:\Users\speci.000\.cursor`
- `C:\Users\speci.000\AppData\Roaming\Cursor`
- `C:\Users\speci.000\AppData\Roaming\Jan`
- `C:\Users\speci.000\AppData\Roaming\Notion\Partitions`
- `C:\Users\speci.000\AppData\Roaming\Notion\Cache`
- `C:\Users\speci.000\AppData\Roaming\Notion\Code Cache`
- `C:\Users\speci.000\AppData\Roaming\Notion\GPUCache`
- `C:\Users\speci.000\Music\DJ.Studio\Exports\2212chilldeepmix.wav`

## Process Check

Current process scan found no matching live processes for:

- `kilo`
- `devin`
- `windsurf`

## Remaining Kilo State On C:

The Kilo snapshot is gone, but small Kilo state remains:

- `C:\Users\speci.000\.local\share\kilo\bin`
- `C:\Users\speci.000\.local\share\kilo\log`
- `C:\Users\speci.000\.local\share\kilo\storage`
- `C:\Users\speci.000\.local\share\kilo\tool-output`
- `auth.json`
- `kilo.db`
- `kilo.db-shm`
- `kilo.db-wal`
- `telemetry-id`

This is intentional for now. These files are much smaller than the snapshot and can contain auth/session metadata, so they should not be blindly deleted.

## Why It Looked Like Nothing Happened

The command produced a standard table and returned to the prompt. There was no progress bar for large `Move-Item` operations. The real proof is the post-state:

- C: increased from about `83.42 GiB` free to `144.28 GiB` free.
- Kilo snapshot source is gone from C:.
- `D:\NEXUS_COLD\level6_quarantine_20260608` contains the moved payloads.

## Notes

The operator log also shows an Ollama pull before cleanup:

`hf.co/mradermacher/L3.1-Dark-Reasoning-LewdPlay-evo-Hermes-R1-Uncensored-8B-GGUF:Q5_K_M`

That pull completed successfully and is separate from the cleanup operation.

