# NEXUS Recovery Intake - 2026-06-05

Purpose: preserve June 2026 NEXUS/NexusClaw/archivist work inside the canonical workspace without importing secret-tainted raw logs as doctrine.

Source roots:
- `C:\Users\speci.000\Downloads\NEXUSlogs`
- `C:\Users\speci.000\Downloads\ARCHIVIST`
- `C:\Users\speci.000\Documents\NEXUS\docs\handoff`

## Current Finding

The restored `docs\handoff` tree is present, but most canonical handoff filenames are May 2026 artifacts. The June 3-5 NexusClaw, MetaSpark, archivist, model-routing, Hermes, and OpenCode evidence lives mainly in Downloads and ARCHIVIST. This intake records the safe subset imported today and the tainted sources that must remain external until summarized or sanitized.

## Curated Files Staged

Copied into `docs\handoff\recovery-intake-2026-06-05\curated`:

| File | Source | Rescue value | Status |
|---|---|---|---|
| `NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md` | `Downloads\ARCHIVIST` | Secret-free NexusClaw V0 evidence disposition matrix. | staged |
| `PLANcodex030626.md` | `Downloads\ARCHIVIST` | NexusClaw Core V0 implementation plan and runtime rules. | staged |
| `nexus_os_architecture_upgrades_synthesis.md` | `Downloads\ARCHIVIST` | Research-to-architecture synthesis for security, local execution, benchmarks, and governance. | staged |
| `implementation_plan16.md` | `Downloads\ARCHIVIST` | Latest MetaSpark/archivist implementation plan. | staged |
| `implementation_plan15.md` | `Downloads\ARCHIVIST` | Related June 4 implementation plan. | staged |
| `Release_Notes_MetaSpark_Integration.md` | `Downloads\ARCHIVIST` | MetaSpark integration release notes. | staged |
| `walkthrough08.md` | `Downloads\ARCHIVIST` | Latest walkthrough paired with implementation plan 16. | staged |
| `test_archivist_integrity-metaPYtext.txt` | `Downloads\ARCHIVIST` | Archivist integrity test source text. | staged |
| `supervisorJStext.txt` | `Downloads\ARCHIVIST` | Supervisor JS source text for archivist/MetaSpark path. | staged |

## Evidence Sources Not Copied Raw

These files are high-value, but they must be treated as evidence inputs rather than canonical docs until sanitized. They either contain provider/key/token terms, raw conversation logs, contaminated claims, or explicit secret-like patterns.

| File | Source | Reason not copied raw | How to use |
|---|---|---|---|
| `NEXUS-CLAW-01.txt` | `Downloads\ARCHIVIST` | Raw agent transcript with provider/key/token pattern hits. | Summarize WSL/NemoClaw collision findings only. |
| `NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md` | `Downloads\ARCHIVIST` | Strategic but contaminated by unverified GROSS deletion/remediation claims and secret/token terms. | Reframe architecture ideas; reject proof claims without disk/network evidence. |
| `NEXUS_SWARM_ENTANGLEMENT_PLAN_v2.md` | `Downloads\ARCHIVIST` | Stronger secret-like pattern hits, including private-key text pattern. | Do not import until sanitized. |
| `archivist_audit_jsonTEXT.txt` | `Downloads\ARCHIVIST` and `Downloads\NEXUSlogs` | Useful index, but high token/provider/secret pattern count. | Use as lookup index only; never paste raw into repo docs. |
| `NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-03.txt` | `Downloads\NEXUSlogs` | Raw execution log. | Summarize verified NexusClaw/OpenCode outcomes only. |
| `NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-04.txt` | `Downloads\NEXUSlogs` | Raw execution log with token/provider pattern hits. | Summarize verified deltas only. |
| `NEXUSlocalworkspaceMETASPARKarchivistlogs-01.txt` | `Downloads\NEXUSlogs` | Raw local workspace log with token/provider pattern hits. | Summarize MetaSpark/archivist outcomes only. |
| `NEXUSbenchmarkMODELresearchlog-02.txt` | `Downloads\NEXUSlogs` | Large raw benchmark/model log. | Extract only the no-background-polling lesson and verified model behavior. |
| `NEXUSubuntuHERMESlog-01.txt` | `Downloads\NEXUSlogs` | Large raw Hermes/provider log. | Extract Hermes readiness/degraded-provider facts only. |

## Trust And Memory Source Recovery State

The archive copy contains concrete non-linear trust and memory implementation sources:

- `Downloads\ARCHIVIST\governor\trust_engine_v2.py`
- `Downloads\ARCHIVIST\governor\trust_scoring.py`
- `Downloads\ARCHIVIST\vault\memory_adapter.py`
- `Downloads\ARCHIVIST\vault\memory_tracks.py`
- `Downloads\ARCHIVIST\vault\trust.py`
- `Downloads\ARCHIVIST\vault\trust_store.py`

The restored repo already contains corresponding recovered files:

- `nexus_os\governor\trust_engine_v2.py`
- `nexus_os\governor\trust_scoring.py`
- `src\nexus_os\governor\trust_scoring.py`
- `nexus_os\vault\memory_adapter.py`
- `nexus_os\vault\memory_tracks.py`
- `nexus_os\vault\trust.py`
- `nexus_os\vault\trust_store.py`
- `tests\governor\test_trust_scoring.py`
- `tests\vault\test_memory_adapter.py`
- `tests\vault\test_memory_tracks.py`
- `tests\vault\test_trust.py`

Verification result:

- `trust_scoring.py` and `trust_store.py` are exact SHA-256 matches between `Downloads\ARCHIVIST` and the restored repo.
- `trust_engine_v2.py`, `memory_adapter.py`, `memory_tracks.py`, and `trust.py` differ only by line-ending normalization. Normalized text matches line-for-line.
- Do not replace repo code blindly; the non-linear trust and S-P-E-W/mem0 memory source layer is already recovered in the repo.

## Rescue Rules

- Do not import raw logs that mention API keys, tokens, JWTs, private keys, provider credentials, or live endpoints.
- Do not canonize GROSS claims without independent disk, pcap, Sysmon, firewall, and operator evidence.
- Prefer secret-free summaries over raw transcript copies.
- Preserve Downloads and ARCHIVIST as evidence roots; do not delete or mutate them during recovery.
- For NexusClaw, trust/memory, and ModelRelay, current repo source plus curated June handoff docs outrank older May backup names.

## Next Operator Actions

1. Produce sanitized summaries for raw logs `NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-03/04`, `NEXUSlocalworkspaceMETASPARKarchivistlogs-01`, `NEXUSbenchmarkMODELresearchlog-02`, and `NEXUSubuntuHERMESlog-01`.
2. Run targeted tests only after the restored repo state is stable: `tests\governor` and `tests\vault` first.
3. Promote only reviewed/sanitized claims from `recovery-intake-2026-06-05\curated` into canonical architecture docs.
