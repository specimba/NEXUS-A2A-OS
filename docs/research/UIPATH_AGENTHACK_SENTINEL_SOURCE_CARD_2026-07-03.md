---
id: SRC-UIPATH-AGENTHACK-SENTINEL-2026-07-03
status: reviewed
evidence_grade: E1
target_lane: sentinel_case_orchestration
source_type: operator-provided rejection notice
source_sha256: 8d9947f827fbae574e188617afc2c57896aa54653de30e4f4187d57cdcb9645f
reviewed_at: 2026-07-03
---
# UiPath AgentHack Sentinel Source Card

## Body-Derived Finding

The submission was excluded because the required UiPath Automation Cloud
process was not published and running. A live Render policy adapter did not
satisfy the platform-execution requirement.

## NEXUS Adoption

NEXUS Sentinel converts this failure into a general deliverable claim gate:

- required claims declare a minimum maturity and executable verifier;
- `DESIGNED`, `IMPLEMENTED`, `DEPLOYED`, and `LIVE_VERIFIED` remain distinct;
- required platform execution cannot be substituted by an unrelated live
  dependency;
- execution authorization remains with `NexusGovernor`, followed by signed
  bridge execution and independent verification.

## Implementation Evidence

- Canonical package: `nexus_os/sentinel/`
- Brain API: `/api/sentinel/*` on canonical port `7352`
- Execution transport: `a2a_execution_bridge` on `8000`
- Dashboard: live/degraded Sentinel case surface with no sample fallback
- Focused Sentinel verification: 25 passing tests
- Governor/bridge/port/SDK focused verification: 64 passing tests
- Relevant Governor/bridge/Vault regression gate: 528 passing tests
- Full supported suite: 3,703 passed and 61 skipped; the excluded Vault
  semantic-backend module is blocked by managed Windows temp ACLs
- Next.js webpack production build: 90 pages generated, including `/api/sentinel`

## Contradictions And Limits

- This card does not claim that the optional UiPath adapter is deployed.
- UiPath is disabled by default and operational only with deployment metadata
  plus a successful job evidence record.
- The public AgentHack repository remains historical evidence, not NEXUS
  runtime authority.

## Adoption Gate

Promotion evidence passed: the supported suite completed with 3,703 tests and
the Next.js webpack production build compiled all 90 pages, including
`/api/sentinel`. Canonical project-state files remain operator proposal-gated.
