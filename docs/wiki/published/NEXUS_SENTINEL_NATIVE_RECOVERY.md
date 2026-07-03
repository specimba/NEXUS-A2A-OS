---
id: WIKI-DRAFT-NEXUS-SENTINEL-NATIVE
status: reviewed
authority_scope: evidence-only
source_card: SRC-UIPATH-AGENTHACK-SENTINEL-2026-07-03
review_required: true
---
# NEXUS Sentinel Native Recovery

NEXUS Sentinel is a governed case-orchestration subsystem for evidence-bound
release recovery. It exists to prevent promotion claims from outrunning their
executable proof.

## Lifecycle

`INTAKE -> INVESTIGATION -> HUMAN_DECISION -> REMEDIATION_PROPOSED ->
AUTHORIZED_EXECUTION -> VERIFICATION -> CLOSURE`

Exceptional routes hold incomplete or mismatched evidence, escalate unsafe
requests, and return failed verification to investigation. Three failed
verification attempts escalate the case.

## Authority Boundaries

- Sentinel policy emits findings.
- `NexusGovernor.check_access()` provides the authoritative execution verdict.
- Signed execution uses the A2A bridge on port `8000`.
- Brain API remains the only Sentinel API owner on port `7352`.
- The GROSS/Grok MCP bridge on `7354` remains read-only.
- UiPath support is optional and disabled by default.

## Evidence Model

Cases, evidence, approvals, verification attempts, idempotency records, and a
hash-chained event timeline persist in SQLite. Raw prompts and credentials are
not stored. Lifecycle records route to EPISODIC and TASK memory; health and
retry state route to META. SEMANTIC promotion remains review-gated.

## Current Status

The native implementation passed 25 focused Sentinel tests, a 528-test related
regression gate, and the 3,703-test supported suite. The webpack production
build generated all 90 pages. This does not claim the optional UiPath adapter
is deployed or operational.
