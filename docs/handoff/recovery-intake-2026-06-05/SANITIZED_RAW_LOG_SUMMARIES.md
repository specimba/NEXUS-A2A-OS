# Sanitized Raw Log Summaries - 2026-06-05

Scope: secret-free extraction from `Downloads\NEXUSlogs`. Raw logs are not copied here because several contain provider/key/token terms. Claims below are separated into verified-on-disk and log-only.

## OpenCode / NexusClaw

Sources:
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-03.txt`
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-04.txt`

Recovered findings:
- The logs identify NexusClaw as a governed convergence layer over NEXUS OS plus CLAW ecosystem components, not a replacement autonomous model loop.
- The design anchor is NEXUS local governance: TrustEngine v2.2, KAIJU gates, Vault 5-track memory, MCP gateway, ModelRelay/TWAVE, and VAP-style auditability.
- The security anchor is explicit: no remote stdio, MCP transport allowlisting, gateway URL validation, sandboxed execution, provenance checks, OWASP ASI class mapping, and CVE-2026-26015 mitigation.
- The logs claim `docs\research\NEXUSCLAW_DESIGN.md` was written. Verified on disk: `docs\research\NEXUSCLAW_DESIGN.md` exists, last write `2026-06-04 14:38:51`, length `20837`.
- The logs claim `bridge/transport_validator.py`, `tests/mcp/test_red_team_lab.py`, and `tests/bridge/test_transport_validator.py` were implemented. Not verified on disk: exact filename search in the restored repo, `D:\NEXUS_RECOVERY`, displaced D snapshot, and `Downloads\ARCHIVIST` found no matching files.
- The logs claim large passing test counts. Treat these as untrusted until rerun in the restored repo.

Disposition:
- `NEXUSCLAW_DESIGN.md` is recovered.
- MCP transport validator and red-team tests are missing or were never materialized in recoverable storage.
- Next implementation should recreate these from current repo structure, not from unverified log claims.

## MetaSpark / Lead Archivist

Source:
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSlocalworkspaceMETASPARKarchivistlogs-01.txt`

Recovered findings:
- The log records a Lead Archivist node boot sequence and an external ARCHIVIST ingestion workflow.
- A Google Drive ARCHIVIST folder was seen and indexed at a high level, but automated fetch/download was blocked in that sandbox.
- Direct-upload batching worked for a first batch and included `NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md`.
- The safe rescue artifacts from this path are now staged under `docs\handoff\recovery-intake-2026-06-05\curated`.

Disposition:
- Treat the log as ingestion process evidence, not canonical architecture.
- Preserve the curated docs; do not copy the raw log.

## Benchmark / ModelRelay / Guard Behavior

Source:
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSbenchmarkMODELresearchlog-02.txt`

Recovered findings:
- The log repeats the NexusClaw/MCP/Trust verification claims, but those need local rerun.
- It also captures a concrete guard behavior improvement: when all guard models error, the guard should fail closed and mark the request unsafe rather than silently allowing it.
- It distinguishes non-error votes from errored stages when computing majority logic.

Disposition:
- Keep the fail-closed guard lesson.
- Do not accept the reported test totals until rerun locally.

## Hermes

Sources:
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSubuntuHERMESlog-01.txt`
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSlocalworkspaceHERMESwindowslogs-01.txt`

Recovered findings:
- WSL Hermes state: Hermes Agent v0.15.1, upstream `fa3b06b0`, reported `109 commits behind`.
- Provider state: one configured free Deepseek route failed with HTTP 404 and was non-retryable; the Grok OAuth route later responded with model `grok-4.3`.
- Skill state: Hermes can load skill-authoring workflows and can act as a planner/delegator surface.
- Windows Hermes sandbox issue: Docker `-w` must use a Linux container path such as `/workspace`, not a Windows host path. A fresh `hermes chat` process could run a sandbox command, while the existing interactive session stayed broken due cached environment state.
- Windows Hermes also hit `UnicodeDecodeError` while reading mixed workspace text.
- A later Hermes summary described the trust/memory model as TrustEngine v2.2 with logistic-scaled trust, adaptive decay, non-compensatory critical block, 6-stage CDR, and Vault 5-track schema.

Disposition:
- Hermes is useful as planner/delegator.
- It is not stable enough as the default router until provider errors, update lag, Docker working-directory behavior, and decoding issues are fixed.

## Immediate Gaps

- Recreate or implement the missing MCP transport validator and tests if NexusClaw Core V0 remains active priority.
- Rerun local tests instead of trusting log-reported pass counts.
- Keep raw Downloads logs outside canonical docs unless summarized and secret-scanned.
