---
id: NODE-MIG-GROK_UPLOAD_QUEUE_SECURITY_INCIDENT_2026_05_27
authority_scope: experimental
origin_sha256: 61f26d38a087c1eea05d30c20d80c95075b8855f055acafce4ad323e1fdd3ad7
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-29A0F4
---
# Grok Upload Queue Security Incident - 2026-05-27

<!-- CANARY: bd729e780bdc6acccdf97596a58f4eab -->
Scope: `codex/specimba/1805mainSpeci`

## Executive Finding

Treat this as a serious local-data exposure incident.

During Grok Build beta testing, `grok.exe` generated a `13.178 GiB` upload queue in `C:\Users\speci.000\.grok\upload_queue` during a 12-minute window while Task Manager showed `grok.exe` PID `1796` sustaining `12.2 Mbps` network usage. The queued data includes large JSON/text blobs, binary-like blobs, session state artifacts, NEXUS path references, `.env` references, and high-confidence secret/key pattern hits.

Follow-up GROSS WSL testing did not reproduce a 13 GiB real-workspace upload. It did prove the upload-queue mechanism with synthetic canaries, but that isolated run must not be used as proof that real personal identity documents or raw operator credentials left the host.

No raw secrets are reproduced in this report.

## Evidence Artifacts

- Screenshot: `C:\Users\speci.000\Downloads\grokNETWORKusage.png`
- Queue root: `C:\Users\speci.000\.grok\upload_queue`
- Grok home: `C:\Users\speci.000\.grok`
- Forensic bundle: `logs/forensics/grok-upload-queue/20260527_081707/`
- Inventory: `logs/forensics/grok-upload-queue/20260527_081707/queue_inventory.csv`
- Dedup groups: `logs/forensics/grok-upload-queue/20260527_081707/dedup_groups.csv`
- Top-file signatures: `logs/forensics/grok-upload-queue/20260527_081707/top_files.csv`
- Leak-pattern counts: `logs/forensics/grok-upload-queue/20260527_081707/leak_pattern_counts.csv`
- Binary indicators: `logs/forensics/grok-upload-queue/20260527_081707/binary_indicators.txt`

## Source-Ranked Evidence Matrix

| Rank | Source | Strength | Finding |
|---|---|---:|---|
| 1 | `C:\Users\speci.000\.grok\upload_queue` metadata | High | `1086` direct files, `14,149,435,226` bytes, first write `2026-05-27 07:31:13+03:00`, last write `2026-05-27 07:43:16+03:00`. |
| 2 | `C:\Users\speci.000\Downloads\grokNETWORKusage.png` | High | Task Manager shows `grok.exe` PID `1796`, `321.2 MB` RAM, `12.2 Mbps` network usage. |
| 3 | `logs/forensics/grok-upload-queue/20260527_081707/top_files.csv` | High | Top queued files include large JSON/text blobs up to `247.65 MiB` and binary-like blobs up to `479.03 MiB`. |
| 4 | `logs/forensics/grok-upload-queue/20260527_081707/leak_pattern_counts.csv` | High | Filename-only secret-pattern scan found `OPENAI_API_KEY` in 42 queued files, `GITHUB_TOKEN` in 33, `sk-...` token-shaped strings in 35, and private-key headers in 9. |
| 5 | `C:\Users\speci.000\.grok\logs\unified.jsonl` | Medium | PID `1796` created session `019e67b1-980c-75a1-9545-646d4b34133a`, cwd `C:\Users\speci.000\Documents\NEXUS`, `mcp_server_count: 2`, `tool_count: 26`. |
| 6 | `C:\Users\speci.000\.grok\README.md` | Medium | Documents `[telemetry] trace_upload = true`, telemetry destinations, codebase indexing, memory, and sandbox modes. |
| 7 | `C:\Users\speci.000\.grok\bin\grok.exe` string indicators | Medium | Contains `xai_data_collector`, `upload_queue`, `uploadId`, `partUrls`, `presign`, `multipart`, `bucket`, `artifact`, `s3`, `api.x.ai`, and `auth.x.ai`. |
| 8 | Current live TCP state | Low | `grok.exe` had exited before endpoint capture; no live remote endpoint was recoverable for PID `1796`. |

## What It Tried To Upload

Confirmed from queue filenames and signatures:

- Session state files: examples include `session_state` and `turn_messages` entries for session prefix `4b34133a`.
- Deduplicated artifacts: `1009` direct `dedup_*` files and `69` session-prefixed dedup files.
- Size attribution: `1078` dedup payloads account for `13.176 GiB` of the `13.178 GiB` queue; session-state and turn-message files account for only about `0.001 GiB`. The 13 GiB event is therefore dominated by deduplicated artifact/content payloads, not chat transcript text alone.
- Large JSON/text blobs: several top files have JSON/text signatures and first-block printable ratio near `1.0`.
- Binary-like blobs: several top files have repeated binary-like signature `FFFFFFFFB80100001000000000000A00` and first-block printable ratio around `0.89`.
- NEXUS-related content: `341` queued files contain `NEXUS`; `29` contain the absolute NEXUS path.
- Environment/config references: `224` queued files contain `.env`.
- High-confidence sensitive markers: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, token-shaped `sk-...`, and private-key header patterns exist in queued files.

The scan reported only matching filenames/counts, not raw matched values.

## Where It Tried To Upload

Confirmed:

- Local config uses `https://api.x.ai/v1` as the default API base URL.
- Grok logs use auth scope `https://auth.x.ai::b1a00492-073a-47ea-816f-4c329264a828`.
- The binary contains `xai_data_collector::s3endpoint`, `xai_data_collector::storage_client`, `xai_data_collector::queue`, `uploadId`, `partUrls`, `presign`, `multipart`, `bucket`, and AWS/GCS storage-client indicators.

Not yet captured:

- The exact remote presigned URLs or bucket hostnames used by PID `1796`, because the process exited before live TCP endpoint capture.

Best current model:

1. `grok.exe` talks to `auth.x.ai` / `api.x.ai`.
2. It prepares a local upload queue under `~\.grok\upload_queue`.
3. It requests upload metadata such as `uploadId` / `partUrls`.
4. It uploads queued artifacts through S3/GCS-style storage endpoints.

This model is supported by local binary indicators and queue behavior, but exact destination hostnames require live capture during recurrence.

## Root-Cause Hypothesis

The likely incident trigger was Grok Build running in `permission_mode = "always-approve"` inside the real `C:\Users\speci.000\Documents\NEXUS` workspace, combined with upload/trace/codebase-sync behavior that staged deduplicated artifacts into `~\.grok\upload_queue`.

Incident-time backup config:

```toml
[cli]
installer = "internal"

[ui]
max_thoughts_width = 120
fork_secondary_model = "grok-build"
yolo = false
compact_mode = false
permission_mode = "always-approve"
```

The incident-time config did not explicitly set:

- `[features] telemetry = false`
- `[features] feedback = false`
- `[features] codebase_indexing = false`
- `[telemetry] trace_upload = false`
- sandbox mode

Follow-up correction: the live config later added telemetry/codebase/trace-disable fields, but still contained `permission_mode = "always-approve"` when rechecked. Treat unattended/auto-approve containment as incomplete until that live file is patched and reverified.

## WSL Reproduction Boundary

The two-hour GROSS WSL run is useful, but it answers a different question from the original Windows incident:

- It used an isolated prop workspace and synthetic canaries, not the full real NEXUS tree.
- It produced `2614` queue snapshots, `255` canary-hit snapshots, and `37,859,495` bytes of captured transient queue payloads.
- Its final live queue was `0` files / `0` bytes after cleanup.
- Its largest captured queue snapshot was only `84,406` bytes / `3` files.

Conclusion: the WSL run proves that Grok can package secret-like file contents into upload-queue artifacts, but it does not reproduce the 13 GiB Windows event. The most plausible reason is environmental: the original Windows run had the full NEXUS workspace, real Grok home/session state, Windows Grok Build runtime behavior, and large local datasets available; the GROSS run deliberately constrained those inputs.

## Nexus Architecture Mapping

- Vault impact: likely leakage of memory/session artifacts and possible secrets from local files.
- Governor impact: no local policy gate blocked trace upload, codebase indexing, or secret-pattern queueing.
- Bridge impact: external API and storage-upload paths were reachable from the agent runtime.
- Engine impact: `always-approve` reduced friction for tool execution but did not protect against background telemetry/upload behavior.

Architecture decision:

- Any beta agent with trace upload, memory sync, or codebase indexing must run behind a local egress gate during OBS or sensitive repo work.
- "Always approve" must not be treated as safe just because the operator is watching Task Manager.
- Future agent admission should require a no-upload proof or a firewall profile before use in `C:\Users\speci.000\Documents\NEXUS`.

## Immediate Containment Options

Executed containment:

1. `C:\Users\speci.000\.grok\upload_queue` was renamed to `upload_queue.quarantine-20260527_083603`.
2. `C:\Users\speci.000\.grok\config.toml` was backed up to `config.toml.bak-20260527_083603`.
3. `C:\Users\speci.000\.grok\config.toml` was patched to explicitly set:
   - `[features] support_permission = true`
   - `[features] telemetry = false`
   - `[features] feedback = false`
   - `[features] codebase_indexing = false`
   - `[telemetry] trace_upload = false`
   - telemetry destination/token fields empty
   - `[session] load_envrc = false`

Open containment items:

1. No Windows Firewall outbound block has been added for `grok.exe` or `agent.exe`.
2. Exact remote upload endpoints remain uncaptured because PID `1796` exited before live TCP capture.
3. If Grok must be run again, run only under live TCP capture and the patched `scripts/local_resource_monitor.ps1`.

Additional containment:

- `config.toml` was backed up to `config.toml.bak-disable-unattended-20260527_083917`.
- Correction from follow-up verification: the live `C:\Users\speci.000\.grok\config.toml` still contains `permission_mode = "always-approve"`.
- The previous "no remaining uncommented always-approve" claim is stale/incorrect for the live host state.
- Verification still found `telemetry = false`, `feedback = false`, `codebase_indexing = false`, and `trace_upload = false` in the live config.

## Verification Notes

- `grok.exe` was not running at follow-up time, so no live remote endpoint was recoverable.
- No raw queued file contents or secret values were printed into this report.
- The queue should be treated as sensitive and should not be committed, uploaded, copied into public reports, or opened casually in UI tools.

## Actionable Insight For Architecture Agent

NEXUS should classify Grok Build as an untrusted external Bridge until it can prove local-only mode or pass an egress/telemetry gate; its default/runtime behavior can queue large codebase and secret-bearing artifacts for remote upload without an explicit per-artifact approval prompt.
