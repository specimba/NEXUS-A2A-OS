# CODEX HANDOFF - Phase 0

Date: 2026-04-21
Authority: `01_PROJECT_STATE.md`

## Purpose

This handoff tells Codex what to build next without importing the full review-chain noise. It is intentionally narrower than the pasted reports.

## Read First

1. `01_PROJECT_STATE.md`
2. `AGENTS.md`
3. `CONTRIBUTING.md`
4. `ONBOARDING.md`
5. `PHASE0_IMPLEMENTATION_PACKAGE.md`

## Current Rule

Do not assume starter packs, cloud protocols, TrustEngine v2.2, or FastAPI governance code exist unless they are present in tracked repo files.

## Priority Order

### 1. Dry-Run Nexus Scanner

Build a read-only scanner for DoppelGround leak triage.

Required behavior:

- Accept explicit `--target` and `--output` paths.
- Never modify scanned files.
- Never run Git commands.
- Produce JSON with file path, SHA-256, finding type, redacted sample, and recommendation.
- Default target should not be `src/nexus_os`; it should be supplied explicitly.

Verification:

- Unit tests for redaction and finding classification.
- Manual dry run against a small fixture before scanning DoppelGround.

### 2. FastAPI Governance API

Build the canonical governance API under `src/nexus_os/api/`.

Required behavior:

- Use existing Nexus modules.
- Return explicit empty state if no proposals exist.
- Keep CORS configuration safe and visible.
- Include focused API tests.

Verification:

- Focused API tests pass.
- Full suite remains green.

### 3. TrustEngine v2.2 Reconciliation

Do not directly add a new trust engine as a second source of truth.

Required behavior:

- Compare proposed TrustEngine v2.2 design with existing `src/nexus_os/governor/trust_scoring.py`.
- Identify whether to extend, wrap, or replace existing behavior.
- Add tests before integration.

Verification:

- Reconciliation note exists.
- No Governor wiring until tests pass and design is accepted.

### 4. Dashboard Proxy

Only after the governance API exists and is tested, update dashboard/relay code to consume `/dashboard/stats`.

Required behavior:

- Proxy/fetch from Python API.
- Do not embed governance decisions in UI/relay.
- Handle API-down state.

## Forbidden Work

- `git add .`
- Committing `GroundingCollectiveBackup/`, `NEXUS.zip`, `src.zip`, sandbox env files, raw research dumps, local databases, or model weights.
- Auto-committing provenance output.
- Deleting models.
- TWAVE core changes.
- Meta-team operational protocol files.
- Cloud-claw heartbeat files unless the user explicitly asks for a cloud execution agent.

## Required Reporting Format

Every implementation report must include:

- Files changed.
- Tests run and exact result.
- What was intentionally not touched.
- Remaining blockers.
- Whether full suite still passes.

## Success Definition

Phase 0 implementation is healthy when:

- Leak triage is report-only and reviewed.
- Governance API is real and tested.
- Dashboard consumes real governance state.
- TrustEngine changes are reconciled with existing trust scoring.
- Full suite remains green.

