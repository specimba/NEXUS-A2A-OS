---
id: NODE-MIG-GENIUSTURTLE_NEXUS_ADAPTER_CONTRACT_2026_05_26
authority_scope: experimental
origin_sha256: 5e78a0812006074db9b3b3b30c58d15bd8286be88dae3060ddfd90bb1f03b31b
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-433293
---
# GeniusTurtle NEXUS Adapter Contract - 2026-05-26

## Scope

<!-- CANARY: a8f786a86052e1d7455d05b5873d4752 -->
GeniusTurtle is a visible operator layer for NEXUS. It may display health,
model availability, ReviewGround wiki status, TWAVE diagnostics, and model-lab
job cards. It must not become a second governor, model registry, or canonical
state writer.

## Contract Boundary

| Surface | Method | Source of truth | Write behavior |
|---|---|---|---|
| `/status` | read | NEXUS health, Guard Plane health, OpenClaw status, local model probes | none |
| `/models` | read | NEXUS provider/model inventory and smoke tests | none |
| `/reviewground` | read | `docs/wiki/` plus `nexusctl wiki check` output | none |
| `/twave` | read | TWAVE v2 diagnostics and saved QWAVE artifact ledgers | none |
| `/lab/jobs` | read/create proposal | model-lab job-card validator | creates proposal artifacts only |
| `/lab/jobs/{id}/approve` | proposal handoff | NEXUS Governor | no direct approval; forwards to governor |

## Required Request Rules

- All state-changing requests must include an operator intent string.
- All lab jobs must validate against the model-lab job-card gate before they are accepted.
- UI actions may create proposal artifacts, not canonical state.
- No local training, merge, or fine-tune job may start from GeniusTurtle directly.
- No raw provider keys, local model paths, or DoppelGround raw captures may be returned to the browser.

## Response Envelope

```json
{
  "status": "ok",
  "surface": "geniusturtle",
  "mode": "read_only_or_proposal",
  "source": "nexus",
  "data": {},
  "evidence": []
}
```

## Model Lab Flow

```text
dataset card -> recipe card -> job card -> preflight validation
  -> governor proposal -> optional execution -> eval packet
  -> candidate registry entry -> rollback point
```

## Hard Stops

- Missing dataset hash.
- Missing recipe hash.
- Missing rollback rule.
- Missing guard evaluation rule.
- Registry action set to direct promotion.
- Protected workloads not acknowledged.
- Secret-shaped values in job-card fields.
- GPU-heavy execution requested while protected workloads are active.

## Initial Implementation Target

The first implementation target is a validator and example job card only. A
later API adapter can call the validator before any GeniusTurtle `/lab/jobs`
proposal is written.
