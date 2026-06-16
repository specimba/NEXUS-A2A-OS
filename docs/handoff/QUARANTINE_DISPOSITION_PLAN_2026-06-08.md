# Level 6 Quarantine Disposition Plan - 2026-06-08

## Scope

Quarantine root:

`D:\NEXUS_COLD\level6_quarantine_20260608`

This folder is not trash. It is the controlled landing zone for Level 6 C: rescue moves. It contains removed app caches, stale IDE state, one personal media file, and the high-risk Kilo snapshot mirror. Keep it out of indexing, sync, repo commits, and automation summaries.

## Current Inventory

Status after approved purge at `2026-06-08`: only the Kilo snapshot remains in this quarantine root.

| Quarantine item | Size GiB | Files | Classification | Disposition |
|---|---:|---:|---|---|
| `Users_speci.000_.local_share_kilo_snapshot` | 40.103 | 2,506 | Sensitive Kilo/NEXUS mirror and failed Git pack storm evidence | Hold short-term, do not restore to C |

Remaining quarantine: about `40.103 GiB`, `2,506` files.

## Approved Purge Execution

The operator approved purge for Windsurf, Jan, Notion cache, Cursor, and the DJ Studio WAV.

Deleted:

| Deleted item | Size GiB | Files |
|---|---:|---:|
| `Users_speci.000_.windsurf` | 9.639 | 23,330 |
| `Users_speci.000_AppData_Roaming_Jan` | 3.569 | 2,571 |
| `Users_speci.000_AppData_Roaming_Notion_Partitions` | 3.166 | 29,628 |
| `Users_speci.000_.cursor` | 2.764 | 24,361 |
| `Users_speci.000_Music_DJ.Studio_Exports_2212chilldeepmix.wav` | 2.049 | 1 |
| `Users_speci.000_AppData_Roaming_Windsurf` | 1.309 | 4,622 |
| `Users_speci.000_AppData_Roaming_Cursor` | 0.431 | 1,385 |
| `Users_speci.000_AppData_Local_Programs_Windsurf` | 0.114 | 1 |
| Notion cache/code/GPU cache remnants | 0.001 | 9 |

Result:

- Delete errors: `0`.
- Missing targets: `0`.
- Remaining quarantine root: `40.103 GiB`, `2,506` files.
- Current C: free after purge check: `142.56 GiB`.
- Current D: free after purge check: `279.80 GiB`.

## Why It Exists

Level 6 did execute and moved the selected C: pressure sources to D:. C: relief was about `63.145 GiB`, bringing C: above the 15 percent free-space health threshold. The quarantine root is the rollback boundary: we can restore selected app settings if needed, but we avoid accidental permanent loss until the operator confirms the system is stable.

## High-Risk Item: Kilo Snapshot

The Kilo snapshot is the main reason this folder must not be treated as normal cache.

Verified facts:

- It contains a mirror-like view of `C:\Users\speci.000\Documents\NEXUS`.
- It includes Git object/pack data, failed `tmp_pack_*` garbage, LFS data, and sensitive path names.
- It was associated with an orphaned stale `kilo.exe serve --port 0` process from a deleted Windsurf extension path.
- It should not be restored to C: unless a specific missing artifact is identified and extracted manually.

Disposition: keep for a short forensic hold, then purge or move to an offline encrypted archive. Do not rehydrate the whole snapshot.

## Recommended Lifecycle

### Stage 1 - Freeze Now

Keep the quarantine folder intact for short-term recovery.

Rules:

- Do not index it into NEXUS memory/vector stores.
- Do not sync it to cloud.
- Do not commit, summarize secrets, or expose its contents.
- Do not restore full IDE/app trees blindly.

### Stage 2 - Fast Purge Candidates

After explicit operator approval, the safest first purge set is:

- Notion cache remnants: about `3.167 GiB`.
- DJ Studio WAV: about `2.049 GiB`, because the operator already marked it for purge.
- Jan app/model state: about `3.569 GiB`, because Jan is retired.
- Cursor state: about `3.195 GiB`, because Cursor is uninstalled/not used.

Expected D: recovery from this set: about `11.0 GiB`.

### Stage 3 - IDE Reinstall Confidence Window

Hold Windsurf state until either:

- Fresh Windsurf reinstall is verified working, or
- The operator confirms Windsurf is permanently retired.

Then purge:

- `Users_speci.000_.windsurf`
- `Users_speci.000_AppData_Roaming_Windsurf`
- `Users_speci.000_AppData_Local_Programs_Windsurf`

Expected D: recovery: about `11.1 GiB`.

### Stage 4 - Kilo Forensic Closeout

Hold the Kilo snapshot until one of these is true:

- A final metadata manifest exists and no missing NEXUS files are found.
- The restored NEXUS repo remains stable through at least one full test cycle.
- The operator explicitly accepts that Kilo incident recovery is complete.

Then choose one:

- Purge to recover about `40.1 GiB` on D:.
- Move to encrypted/offline cold archive if the Kilo incident evidence still matters.

## Approval Matrix

| Action | Impact | Risk | Approval needed |
|---|---:|---|---|
| Keep remaining Kilo snapshot | Uses 40.103 GiB on D | Low immediate risk, high space cost | No |
| Purge Kilo snapshot | Recover about 40.1 GiB | High forensic/provenance risk | Explicit yes only |

## Next Decision

Recommended next move:

1. Keep Kilo snapshot under forensic hold until NEXUS recovery and tests are stable.
2. If the Kilo incident no longer matters, request explicit Kilo purge.
3. If Kilo evidence still matters, create a metadata manifest and move the snapshot to encrypted/offline cold archive.
