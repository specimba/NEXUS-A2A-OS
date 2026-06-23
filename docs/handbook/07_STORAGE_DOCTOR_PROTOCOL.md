# NEXUS Storage Doctor Protocol

Status: active operator protocol  
Created: 2026-06-18

## Purpose

Prevent panic cleanup after sudden disk-space changes. The June disk incident
showed that large free-space swings can come from hidden/system allocation
release, restore/shadow storage, pagefile policy, virtual disks, sparse files, or
cache compaction. NEXUS must classify those causes before proposing deletion of
project, model, dataset, GROSS, ARCHIVIST, or personal files.

## Canonical Entry Points

- `python -m nexusctl doctor hygiene --report-only`
- `python -m nexusctl disk-rescue level6` for dry-run cleanup plans
- `python -m nexusctl disk-rescue level6 --execute ...` only after explicit
  operator approval for exact action flags and paths

## Required Sequence

1. Capture drive accounting for `C:` and `D:`.
2. Compare against the last baseline if available.
3. If free space changed by `>=50 GiB`, classify the cause before cleanup.
4. If filesystem-used bytes and visible scanned bytes differ by `>=25 GiB`,
   run hidden-allocation diagnostics before proposing visible file deletion.
5. Rank cleanup candidates by risk and reclaim, but do not execute.
6. Ask the operator for exact approval listing path, action, expected reclaim,
   risk, and rollback/quarantine location.

## Protected Until Explicit Approval

- `C:\Users\speci.000\Documents\NEXUS`
- `D:\GROSS`
- `D:\NEXUS_RECOVERY`
- `D:\NEXUS_COLD` except explicitly selected cache/quarantine batches
- NEXUS model, dataset, benchmark, research, `.git`, and evidence folders
- Docker/WSL VHDX files unless using owner-aware tooling
- Windows system files such as `pagefile.sys`, `swapfile.sys`, `hiberfil.sys`

## Hidden Allocation Diagnostics

Run these from an elevated shell when the report shows large unexplained deltas:

- `vssadmin list shadowstorage`
- `vssadmin list shadows`
- `fsutil volume diskfree C:`
- `fsutil volume diskfree D:`
- `Get-Volume`
- Event Log/Sysmon review for the incident window

## Stop Rules

- Do not delete visible project/model/evidence files to solve a hidden-space
  accounting problem.
- Do not touch Downloads blindly; it contains active NEXUS/GROSS/ARCHIVIST
  evidence.
- Do not move Kilo/Windsurf/browser state while owner processes are active.
- Do not treat a backup, quarantine, or junction migration as successful without
  post-action `Test-Path`, size, and junction verification.
- If live free space is already above the healthy target, prefer recording the
  baseline over further cleanup.

## Healthy Targets

- Emergency floor: `50 GiB` free on `C:`.
- Operational floor: `100 GiB` free on `C:`.
- Healthy target: about `15%` free on `C:` or higher.
- Current `doctor hygiene` output is the source of truth for live free space.

