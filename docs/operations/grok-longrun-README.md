---
id: NODE-MIG-GROK_LONGRUN_README
authority_scope: experimental
origin_sha256: fa4786613219b449b7cb2f0489bf492c03b2310ebf68486b600f196f3b3a5b12
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-1408BE
---
# Grok Long-Run Burst Harness

<!-- CANARY: bc3df7d6574891eb38d5850d4c57251e -->
Purpose: use Grok as a fast burst worker while NEXUS remains the durable controller and source of truth.

## Operating Rule

Grok does not mark work done. Grok submits proposals.

Acceptance belongs to the local NEXUS verifier, focused tests, and the operator.

## Folder Contract

```text
docs/handoff/grok-longrun/
  README.md
  state/
    feature_list.json
    progress.jsonl
    current_task.json
  inbox/
    grok-0001.md
  outbox/
    <task_id>.result.md
    <task_id>.evidence.json
  accepted/
  rejected/
```

## Burst Contract

Each Grok burst receives one task file from `inbox/`.

Required behavior:

- Read only the paths listed in the task.
- Produce one result artifact in `outbox/`.
- Produce one evidence JSON file in `outbox/`.
- Cite exact local paths or source URLs for every meaningful claim.
- State what was not verified.
- Do not ask for confirmation before producing the assigned artifact.

Forbidden behavior:

- No raw secrets.
- No shell execution.
- No deletion.
- No Git operations.
- No external sends.
- No arbitrary writes outside `outbox/`.
- No "mission complete" language unless NEXUS verifier accepts the artifact.

## Evidence JSON Schema

```json
{
  "task_id": "grok-0001",
  "status": "proposed",
  "artifacts": ["docs/handoff/grok-longrun/outbox/grok-0001.result.md"],
  "evidence": ["path or URL"],
  "self_check": ["verified item", "unverified item"],
  "next_recommended_task": "grok-0002"
}
```

## Verification

Run:

```powershell
py -3.13 scripts\verify_grok_outbox.py
```

The verifier checks schema, path boundaries, raw secret patterns, and artifact existence. Passing verifier output means "proposal is structurally acceptable", not "merged" or "approved".

