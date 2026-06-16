# Level 6 Controlled Cleanup Protocol - 2026-06-05

## Current State

- `C:` remains above emergency state after Level 5, but the remaining pressure is mostly app state under `C:\Users\speci.000\AppData` and tool-local state under `C:\Users\speci.000\.local`.
- `D:` is the migration/quarantine target. The Level 6 rollback root is `D:\NEXUS_COLD\level6_quarantine_20260605`.
- `C:\Users\speci.000\Downloads` remains protected. It contains active NEXUS/GROSS logs and must not be cleaned blindly.
- `C:\Users\speci.00\osman-workspace\*.gguf` is a different Windows profile, not `speci.000`; do not treat it as current-user cleanup without explicit cross-profile approval.

## Kilo Finding

`C:\Users\speci.000\.local\share\kilo\snapshot` is a Git/LFS-shaped snapshot store, not a normal small cache. The dominant snapshot is about `40.10 GiB` and contains Git packs, LFS objects, session diffs, logs, and interrupted Git pack garbage. `git count-objects` against the snapshot store reported about `18.64 GiB` of Git garbage in `tmp_pack_*` files plus large valid packs and LFS payloads.

Two Kilo processes were live during dry-run:

- `C:\Users\speci.000\AppData\Roaming\npm\node_modules\@kilocode\cli\...\kilo.exe`
- `C:\Users\speci.000\.windsurf\extensions\kilocode.kilo-code-7.2.20-win32-x64\bin\kilo.exe`

This explains why Kilo looked closed in the GUI but still protected the snapshot path. Treat Kilo snapshot contents as sensitive because session diffs include NEXUS planning/governance/research text. Recommended action is quarantine the full snapshot after stopping Kilo, not blind permanent deletion.

## Folder Purpose Classification

| Path | Purpose | Recommendation |
| --- | --- | --- |
| `C:\MyFlaskAI` | Legacy SEQUENCE Desk v10 Flask source pack plus backups and one GGUF model. | Move/archive candidate only after confirmation. |
| `C:\tmp` | Temporary NEXUS clones/worktrees/build artifacts. | Move/archive candidate after no active shell depends on it. |
| `C:\GitHubVs` | Legacy `seqnce-app` workspace with Python `.venv`/ML dependencies. | Move/archive candidate. |
| `C:\Users\speci.000\AppData\Roaming\npm` | Global npm CLI installs, not just disposable cache. Includes Codex/OpenCode/Kilo/Grok/Qwen/Sanity style shims. | Do not purge globally; prune package-by-package later. |
| `C:\Users\speci.000\AppData\Roaming\slobs-client` | Streamlabs OBS app state. `Media` contains stream assets; `Partitions` is Electron cache. | Clean cache only after stopping Streamlabs; do not touch `Media` without explicit approval. |
| `C:\Users\speci.000\AppData\Roaming\Jan` | Jan app state and local Llama.cpp model. | User confirmed Jan unused; safe to quarantine. |

## Dry-Run Results

Command verified:

```powershell
python -m nexusctl disk-rescue level6 --approved-stale-apps --notion-caches --kilo-snapshot
```

Result:

- Estimated relief without Kilo: `23.972 GiB`.
- Kilo snapshot action blocked because Kilo was running.
- Streamlabs OBS was running, but it is no longer included unless `--streamlabs-caches` or combined `--approved-caches` is selected.

Full simulated recommended command including process stop and Kilo:

```powershell
python -m nexusctl disk-rescue level6 --stop-approved-processes --approved-stale-apps --notion-caches --kilo-snapshot
```

Result:

- Estimated relief: `64.075 GiB`.
- Includes `40.103 GiB` Kilo snapshot quarantine.
- Does not stop Streamlabs and does not touch Streamlabs media/cache.

Full simulated optional command including legacy candidates and both Notion/Streamlabs caches:

```powershell
python -m nexusctl disk-rescue level6 --stop-approved-processes --approved-stale-apps --approved-caches --kilo-snapshot --legacy-project-candidates
```

Result from the earlier combined dry-run:

- Estimated relief: `71.313 GiB`.
- Includes `5.637 GiB` legacy C-root candidates: `C:\MyFlaskAI`, `C:\tmp`, `C:\GitHubVs`.

## Execution Gates

Use dry-run first. Execution requires explicit operator confirmation.

Recommended Batch A:

```powershell
python -m nexusctl disk-rescue level6 --execute --stop-approved-processes --approved-stale-apps --notion-caches --kilo-snapshot
```

This moves the approved stale apps, Jan data, DJ WAV, Notion caches, and the Kilo snapshot to `D:\NEXUS_COLD\level6_quarantine_20260605`. It does not touch Downloads, npm globals, Program Files, ProgramData, WSL, Docker, Streamlabs, or the `speci.00` profile.

Optional Batch B:

```powershell
python -m nexusctl disk-rescue level6 --execute --legacy-project-candidates
```

This moves `C:\MyFlaskAI`, `C:\tmp`, and `C:\GitHubVs` only after separate approval.

## Nexusctl Integration

`nexusctl disk-rescue level6` is now the reusable Level 6 entrypoint. It wraps `scripts\nexus_level6_controlled_cleanup.ps1` and is dry-run by default. Execution is disabled unless `--execute` is passed with explicit action flags.
