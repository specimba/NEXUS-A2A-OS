# Recovery Intake Manifest — 2026-06-17

**Purpose:** Catalog missing root files after NEXUS repo truncation incident, their recovery status, and proposed action.

## Incident Summary
- Date: ~2026-06-05 (see RECOVERY_VERIFICATION_FROM_ARCHIVIST_AND_LOGS_2026-06-05.md)
- Root cause: Agent-triggered disk cleanup collided with robocopy/Junction migration, displacing working tree under PNPM store
- Current state: Repo fully restored from recovery copy (189 root entries, valid git tree with 168 commits in reflog)

## Team role map

| Role | Agent | Notes |
|------|-------|-------|
| Primary code agent | OpenCode CLI | |
| Current agent | Kilo CLI | |
| CLI agent | Mimo CLI | |
| CLI agent | Cline CLI | |
| Sandbox agent | Hermes | via Docker sandbox |
| Model relay | NEXUS Model Relay | Python relay on port 7355 |

## Gaps

| # | File | Size / Date | Source Evidence | Action |
|---|------|-------------|----------------|--------|
| 1 | CONTRIBUTING.md | 4424 bytes, 2026-04-21 8:57:13 PM (124 lines in ARCHIVIST copies) | NEXUSv4planningCODEXlog-06.txt line 26853 confirms size/date; ARCHIVIST copies at DERDDRE/v4/CONTRIBUTING.md and DERDDRE/BOOT/CONTRIBUTING.md verified; archivist_audit_jsonTEXT.txt line 561 flagged duplicates across DERDDRE paths; NEXUSmainbackendCODEXlogRECOVERY-02.txt line 180 lists as KEEP canonical root | **DONE** — restored to root from ARCHIVIST/DERDDRE/v4 |
| 2 | CLAUDE.md | 601 bytes, 2026-04-24 11:57:49 PM | NEXUSv4planningCODEXlog-06.txt line 26847 confirms size/date; NEXUSv4planningCODEXlog-04 line 790 and NEXUSlocalworkspaceHERMESwindowslogs-01 line 180 include CLAUDE.md in canonical root doc list; NEXUSmainbackendCODEXlogRECOVERY-02.txt line 728 lists as KEEP canonical root; devinKIMIworklog.txt line 1643 documents as "Claude context"; NEXUSopencodeMAINbackendCODEkimi26log-09 line 1473 references as "Karpathy-style CLAUDE.md" behavior protocol; content not preserved in any archive | **DONE** — stub created at root |
| 3 | pm2_nexus.json | Unknown / not found | No reference found in any NEXUSlogs or ARCHIVIST file; current process runner confirmed as nexus-daemon.sh / nexus-supervisor.sh in live filesystem | **SKIP** — no evidence it ever existed in repo; likely never committed |
| 4 | SECURITY.md | Content replaced post-incident | NEXUSv4planningCODEXlog-06.txt line 5734 ("A SECURITY.md is added") and line 5738 ("Add LICENSE, CONTRIBUTING.md, SECURITY.md to the repo root") confirm it was part of public-repo prep; NEXUSmainbackendCODEXlogRECOVERY-02.txt line 1207 includes SECURITY.md in canonical root list; NEXUSmainbackendCODEXlogRECOVERY-02.txt line 61121 notes original placeholder was replaced with terminal sanitizer/security layer; currently absent from root | **SKIP** — security content now embedded in `nexus_os/security/*` and tests; placeholder no longer appropriate |

## Verification

- **Git integrity:** Valid tree on branch `nexus-local-push-` (HEAD: 5e7046bf). 168 reflog entries across 10+ branches.
- **Recent commits:** Last commit "Refine governance and security workflows" (2026-06-15). Pre-incident work queue included Guard Plane v1.3, MetaAttackDetector v4, NEXUSCLAW v1 Hardening, NEXUS-Bench 5-Track, Phase 1-2 Critical, Phase 6 MCP bridge.
- **Test suite:** 2,146+ tests pass per 01_PROJECT_STATE.md (2026-06-15). Main Python modules (nexus_os/governor/, nexus_os/vault/, nexus_os/monitoring/) all present.
- **Recovery backup:** D:\NEXUS_RECOVERY\NEXUS_20260605_140529 (full stable tree for fallback)

## Proposed Actions

1. Restore CONTRIBUTING.md → root of repo from ARCHIVIST/DERDDRE/v4/CONTRIBUTING.md (verified path, secret-scanned CLEAN)
2. Deploy CLAUDE.md → root of repo as handoff stub (references AGENTS.md; content unrecoverable from archives)
3. Confirm pm2_nexus.json never existed (no evidence); do not restore
4. Confirm SECURITY.md placeholder is not appropriate (content now in `nexus_os/security/*`); do not restore
5. Update 01_PROJECT_STATE.md to reference corrected team roster (OpenCode CLI, Kilo CLI, Mimo CLI, Cline CLI, Hermes via Docker sandbox, grounded on NEXUS Model Relay on port 7355)
