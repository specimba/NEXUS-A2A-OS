# NEXUS OS - Phase 0 Implementation Package

Date: 2026-04-21
Status: Planning-to-implementation bridge
Authority: `01_PROJECT_STATE.md`

## Purpose

This package distills the useful parts of the review chain into a safe Phase 0 implementation plan. It does not claim that new code is already integrated. All implementation must preserve the current test gate and follow the repository boundaries in `01_PROJECT_STATE.md`.

## Non-Negotiable Rules

- Python/FastAPI is the canonical governance control plane.
- Dashboard, Bun, Next.js, and relay code must proxy governance state, not make governance decisions.
- Provenance scanning starts dry-run/report-only.
- No auto-commit, auto-approval, or automatic source mutation from scanners.
- TWAVE remains HOLD: wrapper/API work only, no algorithm changes.
- Model Arena is report-only: no model deletion, fine-tuning, or promotion.
- Do not commit sandbox env files, raw backups, zip archives, model weights, generated caches, or unreviewed Downloads content.
- Full suite must remain green after core code changes.

## Current Verified Baseline

Latest verified local test gate:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
617 passed in 16.99s
```

Current canonical state file:

- `01_PROJECT_STATE.md`

Current committed onboarding/contribution files:

- `CONTRIBUTING.md`
- `ONBOARDING.md`

## Implementation Priorities

### 1. DoppelGround Leak Triage

Goal: classify the reported DoppelGround leak findings into real secrets, false positives, and cleanup actions.

Deliverables:

- Dry-run scan report.
- Redacted triage report.
- Proposed `.gitleaks.toml` allowlist entries with evidence.
- No source deletion and no history rewrite until explicitly approved.

Target files:

- `scripts/nexus_scan.py` or `scripts/nexus-scan.py`
- `research/triage_gitleaks.md`

Acceptance:

- Scanner is read-only.
- Output is JSON or Markdown.
- Report includes file path, finding type, redacted sample, and recommendation.

### 2. FastAPI Governance API

Goal: replace mock/static dashboard governance data with a real Python API surface.

Required endpoints:

- `POST /skills/propose`
- `GET /skills/status/{id}`
- `GET /dashboard/stats`
- `GET /governance/proposals`
- `POST /governance/approve`

Target location:

- `src/nexus_os/api/`

Constraints:

- Must wrap existing Nexus governance code, not a duplicate mock governor.
- Must not import from Downloads paths.
- Must have tests before relay/dashboard wiring.
- CORS must be explicit, not `allow_origins=["*"]` for production paths.

Acceptance:

- Focused API tests pass.
- Full suite remains green.
- Dashboard stats reflect real governance state or clearly marked empty state.

### 3. TrustEngine v2.2 Reconciliation

Goal: decide whether TrustEngine v2.2 becomes a new module, an adapter, or a successor to existing trust scoring.

Current risk:

- Existing `src/nexus_os/governor/trust_scoring.py` already implements trust scoring behavior.
- Adding `trust_engine_v2.py` as a second source of truth may create drift.

Required first step:

- Write a reconciliation note comparing proposed TrustEngine v2.2 against existing `trust_scoring.py`.

Target:

- `research/trust_engine_v2_reconciliation.md`

Acceptance:

- No integration into Governor until reconciliation is reviewed.
- If implemented, tests must cover persistence, critical hard block, decay, plateau, and compatibility with existing trust-scoring expectations.

### 4. Dashboard Proxy Wiring

Goal: dashboard and relay consume the real governance API instead of static JSON.

Constraints:

- Relay/client code proxies or fetches from the Python API.
- Governance decisions remain server-side in Nexus.
- No direct access to local Ollama, Vault internals, or private paths.

Acceptance:

- Dashboard can render empty/real governance state from `/dashboard/stats`.
- Failure state is explicit when API is down.

### 5. Mini Model Arena

Goal: collect bounded local model evidence without changing the model inventory.

Deliverables:

- `model_arena/mini_arena.py`
- JSONL or Markdown result artifact.

Constraints:

- Report-only.
- No deletion, fine-tuning, or automatic ranking promotion.
- Local-only execution.

Acceptance:

- Three bounded matches maximum for first run.
- Results include prompt set, context size, latency, tokens/sec where available, and raw output references.

## Appendix Assets To Reconcile

These are useful inputs but not canonical until reviewed and promoted:

- Downloads `governor_skill_gate.py`
- Downloads `gspp_openapi.yaml`
- Downloads `wiki_pipeline.py`
- Downloads `PROJECT_HANDOFF_SPEC.md`
- Downloads fuller `dg_to_gspp.py`

Promotion rule:

- Compare against current repo files.
- Keep one canonical destination.
- Do not create duplicate files with overlapping responsibility.

## Explicitly Excluded From This Package

- Meta-team SOUL/HEARTBEAT files.
- Cloud-claw operational protocols.
- Auto-committing scanner output.
- Heretic/uncensoring/fine-tuning work.
- TWAVE algorithm work.
- Public repo launch.

## Current Git Hygiene Note

The following local items must stay uncommitted until separately reviewed:

- `GroundingCollectiveBackup/`
- `NEXUS.zip`
- `src.zip`
- `sandbox/`
- `test_integration.py`
- `research/triage_gitleaks.md`

## Recommended Next Commit Order

1. Commit this package and `CODEX_HANDOFF.md`.
2. Create dry-run `nexus-scan.py` and triage report.
3. Add API skeleton and tests.
4. Reconcile TrustEngine v2.2 before implementation.
5. Wire dashboard/relay after API tests pass.

