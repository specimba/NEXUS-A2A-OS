# Kilo Snapshot Forensic Deep Dive - 2026-06-08

Read-only investigation. No Kilo files, snapshots, logs, DB files, or processes were modified.

## Verdict

`C:\Users\speci.000\.local\share\kilo\snapshot` is not a normal small cache. It is a sensitive Git/LFS snapshot mirror of `C:\Users\speci.000\Documents\NEXUS` plus failed Git packing garbage.

Current classification:

- **High suspicion / high sensitivity**: contains NEXUS source, docs, datasets, backups, logs, `.grok`, `.devin`, `.agents`, and secret/key/token-like path names.
- **Primary disk cause**: failed/interrupted Git pack creation on `2026-06-05`, not regular user-facing Kilo usage.
- **Runtime concern**: one Kilo server process is still live from a deleted Windsurf extension version.

## Process Evidence

| PID | Process | Command | Start | Finding |
| ---: | --- | --- | --- | --- |
| `97656` | `kilo.exe` | `kilo.exe serve --port 0` | `2026-05-28T01:03:50+03:00` | Running from deleted path `C:\Users\speci.000\.windsurf\extensions\kilocode.kilo-code-7.2.20-win32-x64\bin\kilo.exe`. Parent process was not found. |
| `60340`, `71572`, `91296` | `devin.exe` | `acp --agent-type summarizer` | `2026-05-18` to `2026-05-28` | Long-lived Windsurf Devin summarizer workers. |
| `64344`, `85360`, `85952` | `devin.exe` | `acp` | `2026-05-18` to `2026-05-28` | Long-lived Windsurf Devin ACP workers. |

Installed/on-disk Kilo state:

- Global CLI exists: `C:\Users\speci.000\AppData\Roaming\npm\node_modules\@kilocode\cli`, package `@kilocode/cli`, version `7.2.0`.
- Windsurf extension folders currently present: `kilocode.kilo-code-7.3.12-win32-x64` and `kilocode.kilo-code-7.3.16-win32-x64`.
- Running process path version `7.2.20` no longer exists on disk.

Interpretation: Kilo was likely launched by Windsurf, then Windsurf/Kilo updated or was partially cleaned while the old server process remained resident. This is orphaned stale runtime behavior.

## Snapshot Size Breakdown

| Component | Size | Count | Notes |
| --- | ---: | ---: | --- |
| Full snapshot tree | `40.103 GiB` | `2506` files | Under `C:\Users\speci.000\.local\share\kilo\snapshot`. |
| Dominant snapshot ID `c1478df...` | `40.095 GiB` | `2410` files | Created `2026-04-21`; large writes happened `2026-06-05`. |
| Git garbage `tmp_pack_*` | `18.649 GiB` | `7` files | Confirmed by `git count-objects -vH` as `size-garbage: 18.64 GiB`. |
| Valid Git packs | `16.868 GiB` | `9` `.pack` files | Largest valid pack is `13.689 GiB`. |
| Git loose objects | `1.70 GiB` | `2313` loose objects | From `git count-objects`. |
| LFS object | `2.875 GiB` | `1` file | Stored under `lfs\objects`. |
| Kilo session diffs | `0.053 GiB` | dozens | JSON diffs, sensitive but not the disk cause. |

Largest files:

| File class | Size | Timestamp |
| --- | ---: | --- |
| `pack-4c47...pack` | `13.689 GiB` | created `2026-06-05T05:37`, written until `06:13` |
| `tmp_pack_kQ0xw7` | `6.757 GiB` | `2026-06-05T11:25` to `11:28` |
| `tmp_pack_58d2fC` | `6.757 GiB` | `2026-06-05T06:32` to `06:34` |
| `pack-0138...pack` | `3.147 GiB` | `2026-06-05T06:28` to `06:31` |
| `tmp_pack_S59BsP` | `3.145 GiB` | `2026-06-05T07:25` to `07:26` |
| LFS object hash `a961...` | `2.875 GiB` | `2026-06-05T06:02` to `06:03` |

## Git Evidence

The dominant nested repository is:

`C:\Users\speci.000\.local\share\kilo\snapshot\c1478df17dcc92fb168eb2f707bfd4be1359d9fb\1ez1mr9vui4u4`

Sanitized Git config shows:

- `core.worktree=C:/Users/speci.000/Documents/NEXUS`
- `core.bare=false`
- Git LFS filters enabled.
- Credential helpers/providers exist, values redacted.

`git count-objects -vH`:

- `count: 2313`
- `size: 1.70 GiB`
- `in-pack: 3320`
- `packs: 4`
- `size-pack: 16.85 GiB`
- `prune-packable: 93`
- `garbage: 7`
- `size-garbage: 18.64 GiB`

The object store has almost no refs and `git status --short` presents indexed files as added. This looks like a Kilo-managed snapshot index, not a normal checked-out project clone.

## What Kilo Captured

The snapshot index has `2295` NEXUS files.

Top indexed areas:

| Area | Indexed count |
| --- | ---: |
| `research` | `304` |
| `src` | `264` |
| `docs` | `244` |
| `datasets` | `199` |
| `benchmarks` | `169` |
| `models` | `149` |
| `nexus_os` | `114` |
| backup/shadow copies | `246` combined across backup dirs |
| hidden agent surfaces | `74` across `.agents`, `.devin`, `.grok`, `.gemini`, `.pi`, `.playwright-mcp`, `.session` |
| logs/evidence/upload/download | `141` |

Secret-sensitive path scan:

- `51` indexed paths matched secret/key/token/jwt/auth/credential-like names.
- Values were not read or printed.
- This confirms the snapshot must be treated as sensitive evidence.

## Session Diff Evidence

Kilo session diff files are JSON arrays with entries shaped like:

- `file`
- `before`
- `after`
- `additions`
- `deletions`
- `status`

Largest session diffs:

| File | Size | Entries | Last write |
| --- | ---: | ---: | --- |
| `ses_169214f77ffe69c25jRViuYVht.json` | `33.14 MiB` | `2926` | `2026-06-05T12:30:17+03:00` |
| `ses_1780d4213ffeLI13AzjF8jfQiu.json` | `16.42 MiB` | `1894` | `2026-06-05T18:37:07+03:00` |
| `ses_16e1f0fccffeygc77LusZnSAJh.json` | `1.42 MiB` | `118` | `2026-06-04T17:31:28+03:00` |

These are not the 40 GiB problem, but they are sensitive because they contain before/after file diffs.

## Cause Hypothesis

Most likely sequence:

1. Windsurf launched Kilo as a background `serve --port 0` process.
2. Kilo created a Git/LFS snapshot of the NEXUS workspace at `C:\Users\speci.000\Documents\NEXUS`.
3. On `2026-06-05`, during the broader NEXUS disk rescue/recovery period, Kilo/Git repeatedly packed a large snapshot that included model, dataset, benchmark, backup, log, and evidence surfaces.
4. Several Git pack operations were interrupted or abandoned, leaving `18.649 GiB` of `tmp_pack_*` garbage.
5. Windsurf/Kilo extension version changed on disk, but the old Kilo server process kept running from the deleted `7.2.20` path.

This is not proof of malicious exfiltration. It is proof of uncontrolled local duplication of a sensitive workspace plus stale orphaned agent process behavior.

## Recommended Containment

Do not delete blindly.

Recommended action after operator approval:

```powershell
python -m nexusctl disk-rescue level6 --execute --stop-approved-processes --approved-stale-apps --notion-caches --kilo-snapshot --quarantine-root D:\NEXUS_COLD\level6_quarantine_20260608
```

This quarantines the full Kilo snapshot to D: and stops the stale approved Kilo/Windsurf worker processes first.

Reason to quarantine the full snapshot instead of only deleting `tmp_pack_*`:

- `tmp_pack_*` gives about `18.649 GiB` relief.
- Full snapshot gives `40.103 GiB` relief.
- The valid packs and session diffs still contain sensitive NEXUS mirror data.
- The running Kilo process is from a deleted extension version, so preserving the whole snapshot in D: quarantine is safer than partial mutation on C:.

Post-action checks:

1. Verify `kilo.exe` PID is gone.
2. Verify `C:\Users\speci.000\.local\share\kilo\snapshot` no longer exists on C: or is intentionally junctioned later.
3. Verify quarantine exists under `D:\NEXUS_COLD\level6_quarantine_20260608`.
4. Verify C: free space increases by about `40 GiB` from Kilo alone.
5. Add a future guard: block background Kilo/Windsurf snapshotting of `C:\Users\speci.000\Documents\NEXUS` unless explicitly approved.

