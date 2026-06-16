---
id: NODE-MIG-NEXUS_TIDINESS_PROTOCOL
authority_scope: experimental
origin_sha256: 0c54270557d6760ae6aceec8ca93146e571da543e92baa4e8c043d316d2a83d3
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-9666A0
---
# NEXUS Tidiness Protocol

**Version:** 1.0  
**Date:** 2026-05-21  
**Canonical path:** `docs/operations/NEXUS_TIDINESS_PROTOCOL.md`  
**Rollback reference:** `codex/specimba/rollback-pre-tidiness-20260521-001353` @ `f5fe558`

<!-- CANARY: 55f1924814a63c885cb2d3b401b589de -->
---

## Purpose

NEXUS OS generates research evidence, agent logs, benchmark data, and handoff artifacts at a high velocity. Without routine hygiene, the repository root, `Downloads/`, and `C:\tmp` become unnavigable. This protocol defines a safe, repeatable, evidence-grounded cleanup procedure that preserves canonical files, protects secrets, and categorizes incoming documents.

---

## Trigger Conditions

Run this protocol when any of the following are true:

1. `Downloads/` contains more than 20 NEXUS-related files.
2. `C:\tmp` contains more than 5 NEXUS-related directories or artifacts older than 7 days.
3. NEXUS root contains untracked `.md`, `.txt`, `.zip`, or `.py` files not listed in the "Canonical Root Files" table below.
4. A research sprint or dataset-creation cycle has concluded.
5. An external agent session has dumped logs or handoff artifacts.

---

## Pre-Flight Safety Checklist

| Step | Command / Action | Gate |
|---|---|---|
| 1 | `git status --short --branch` | Worktree is clean or only expected modifications are present. |
| 2 | `python -m pytest tests/ -v --tb=short -p no:cacheprovider` | Full suite passes (current baseline: 670). |
| 3 | Create rollback branch: `git branch codex/specimba/rollback-pre-tidiness-$(Get-Date -Format 'yyyyMMdd-HHmmss')` | Branch exists at current HEAD. |
| 4 | Create rollback tag: `git tag rollback/pre-tidiness-$(Get-Date -Format 'yyyyMMdd-HHmmss')` | Tag exists at current HEAD. |
| 5 | Push rollback ref to `alpha` remote: `git push alpha <branch> && git push alpha <tag>` | Remote has rollback point. |
| 6 | Read this protocol and the latest `CLASSIFICATION_MANIFEST.md` | Agent understands categories and MIXED rules. |

**HALT if:** Any test fails, uncommitted tracked changes exist beyond the expected doc/script set, or rollback creation fails.

---

## Category Definitions

| Category | Destination Path | What Goes Here | What Does NOT |
|---|---|---|---|
| **research/incoming/** | `research/incoming/` | Research notes, model evaluations, red-team findings, scientific reports, bibliographies. | Raw datasets over 50MB (use `datasets/`), executable binaries. |
| **research/images/** | `research/images/` | Diagrams, workflow charts, screenshots, generated research images. | Personal photos, unrelated media. |
| **research/Papers/** | `research/Papers/` | PDF academic papers. | Already tracked by `.gitignore`; never commit PDFs to Git. |
| **docs/archive/downloads-logs/** | `docs/archive/downloads-logs/` | Agent session logs, build logs, error logs, diagnostic outputs. | Live service logs, secrets. |
| **docs/archive/downloads-plans/** | `docs/archive/downloads-plans/` | Requirements docs, plans, reports, proposals, configuration exports. | Drafts that should become canonical (those go to `docs/handoff/`). |
| **docs/archive/backups/** | `docs/archive/backups/` | Pre-fix configuration snapshots, env backups, migration artifacts. | Active `.env` files. |
| **docs/archive/diagnostics/** | `docs/archive/diagnostics/` | CDB dumps, proxy logs, verification outputs. | Core diagnostics infrastructure. |
| **docs/archive/pr-artifacts/** | `docs/archive/pr-artifacts/` | PR comments, patches, environment definitions related to PRs. | Source code under active development. |
| **docs/archive/sessions/** | `docs/archive/sessions/` | PI session HTML logs, markdown session exports. | Active agent sessions. |
| **scripts/archive/downloads-code/** | `scripts/archive/downloads-code/` | One-off Python scripts, JS snippets, helper tools from downloads. | Core repo scripts (those stay in `scripts/`). |
| **benchmarks/archive/downloads/** | `benchmarks/archive/downloads/` | Archived benchmark packs, weekly snapshots, zip deliverables, dataset packs. | Active benchmark code. |
| **datasets/archive/tmp/** | `datasets/archive/tmp/` | Temporary parquet files, compression tests, transient data. | Active training datasets. |
| **MIXED/** | `MIXED/` | Anything ambiguous, multi-category, or unknown. User reviews and reclassifies. | Nothing definitive. |

---

## Canonical Root Files (DO NOT MOVE)

These files and directories are intentionally at the NEXUS root and must not be moved by this protocol:

- `01_PROJECT_STATE.md` — canonical project state (AGENTS.md rule)
- `knowledge.md` — canonical knowledge base (AGENTS.md rule)
- `AGENTS.md` — agent operating protocol
- `README.md` — repository README
- `pyproject.toml`, `package.json` — package manifests
- `nexusctl/` — CLI entrypoint package
- `nexus_os/` — root compatibility package
- `src/` — canonical source package
- `tests/` — test suite
- `benchmarks/` — active benchmarks
- `docs/` — docs directory
- `tasks/` — task queue
- `scripts/` — active scripts
- `.env`, `.env.local` — active environment
- `nexus.db`, `nexus_api.db` — active databases
- Infrastructure files: `Caddyfile`, `start.sh`, `run-dev.sh`, `Modelfile`, etc.
- Config files: `.gitignore`, `tsconfig.json`, `eslint.config.mjs`, etc.

---

## Quarantine Rules (DO NOT MOVE TO NEXUS)

These item types must never be moved into the NEXUS repo:

| Type | Examples | Action |
|---|---|---|
| **Secrets / Credentials** | `env.txt`, `*password*.txt`, `sshkey.pem`, `*emergency-kit*.pdf` | DELETE or move to encrypted vault outside repo. |
| **Installers** | `*.exe`, `winsdksetup.exe`, `Codex Installer.exe` | DELETE. Re-download from official source if needed. |
| **Personal / Unrelated** | Photos of pets, receipts, tickets, clothing images | DELETE or leave in Downloads. |
| **Large media unrelated to research** | Music, movies, personal videos | DELETE. |
| **Live service logs** | Docker daemon logs, system Event Logs | DELETE after review. |

---

## Execution Procedure

### Step 1: Inventory
Run the inventory script (or equivalent) to capture:
- `C:\tmp` contents
- `Downloads` contents
- NEXUS root untracked files
- Git status before changes

Store inventories in `docs/handoff/nexus-tidiness/<timestamp>/`.

### Step 2: Classification
Using the Category Definitions table above, classify every item into:
- A specific category destination
- `MIXED/` if ambiguous
- `QUARANTINE` if sensitive or unrelated

Write the classification to `CLASSIFICATION_MANIFEST.md` in the same run folder.

### Step 3: Preview
Run the move script in preview mode:
```powershell
.\scripts\nexus-tidiness-move.ps1 -WhatIf
```
Review every `[move]`, `[delete]`, and `[skip]` line.

### Step 4: Execute
After preview approval, execute:
```powershell
.\scripts\nexus-tidiness-move.ps1 -Force
```

### Step 5: Verify
1. `git status --short` — confirm no unexpected tracked file changes.
2. `python -m pytest tests/ -v --tb=short -p no:cacheprovider` — confirm 670 passed.
3. `python -m nexusctl doctor version --report-only` — confirm status ok.
4. `python -m nexusctl doctor memory --report-only` — confirm status ok.

### Step 6: Document
Update this protocol if new category patterns emerged. Append a run entry to the Run Log below.

---

## Run Log

| Date | Timestamp | Agent | Files Moved | Files Deleted | MIXED Items | Tests Passed |
|---|---|---|---|---|---|---|
| 2026-05-21 | 001353 | rollback agent | 0 (inventory only) | 0 | 0 | 670 |
| | | | | | | |

---

## Related Commands

```powershell
# Quick inventory of Downloads
Get-ChildItem -LiteralPath "C:\Users\speci.000\Downloads" -Force |
    Select-Object Name, Length, LastWriteTime |
    Sort-Object LastWriteTime -Descending

# Quick inventory of C:\tmp
Get-ChildItem -LiteralPath "C:\tmp" -Force |
    Select-Object Name, Length, LastWriteTime |
    Sort-Object LastWriteTime -Descending

# Quick inventory of NEXUS root (show untracked only)
git status --short --untracked-files=all

# Rollback creation (run before every tidiness session)
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$branch = "codex/specimba/rollback-pre-tidiness-$stamp"
$tag = "rollback/pre-tidiness-$stamp"
git branch $branch
git tag $tag
git push alpha $branch
git push alpha $tag
```

---

## Invariants

1. **No secret ever enters Git.** If a file might contain a credential, assume it does.
2. **No destructive action without preview.** `-WhatIf` is mandatory before `-Force`.
3. **No broad `git add .`.** Stage explicit reviewed paths only after tidiness.
4. **Canonical root files stay put.** The list of root-protected files changes only by AGENTS.md amendment.
5. **MIXED is a feature, not a failure.** When in doubt, put it in MIXED. Better to review later than misclassify now.
