# NEXUS OS - Canonical Project State

Date: 2026-05-18
Current local HEAD: 6c729e7
Branch: canonical-617
Status: Safety consolidation merged from Codex github/main. 634 tests passing. ModelRelay + MCP server integrated.

## Verification Gate

Latest local verification:

```text
python3 -m pytest tests/ -q --tb=short
634 passed in 15.13s
```

The older report reference to commit `34c700b` is a historical/alternate-worktree marker. The current local repository HEAD is `8f928bd` after these follow-up commits:

- `6fe8cf4 fix(core): harden db encryption and task dependencies`
- `18cba07 fix(engine): correct dependency cycle traversal`
- `8f928bd docs(agent): separate Nexus protocol from Codex hygiene`

## Core Thesis

Nexus OS turns local models, research evidence, and external teams into a governed, audited, low-VRAM execution system where every action is proposal-bound, test-gated, and provenance-tracked.

- DoppelGround prepares evidence.
- Nexus governs, routes, audits, and approves.
- TWAVE executes within VRAM limits.
- GeniusTurtle makes the system usable.
- Model Arena reports what actually works on local hardware.

## System Boundaries

| Layer | Canonical Role | Current Rule |
|---|---|---|
| GeniusTurtle | Operator UX layer | UI/API integration only; no model weights, secrets, or governance internals. |
| Nexus OS | Governance and orchestration layer | Python/FastAPI governance is the canonical brain. |
| DoppelGround | Evidence preparation layer | USE MODE; outputs must be sanitized before handoff. |
| TWAVE | Low-VRAM execution layer | HOLD; wrapper/API work only, no algorithm changes. |
| Model Arena | Evidence/evaluation layer | Report-only; no automatic model deletion, fine-tuning, or promotion. |

## Core Architecture Map

| Pillar | Purpose | Canonical Areas |
|---|---|---|
| Bridge | Protocol boundary, API ingress, SDK/MCP adapters | `src/nexus_os/bridge/`, `src/nexus_os/relay/` |
| Governor | KAIJU, policy, compliance, trust gates | `src/nexus_os/governor/` |
| Vault | Durable storage, 5-track memory, encryption policy | `src/nexus_os/vault/`, `src/nexus_os/db/` |
| Engine/GMR | DAG routing, Hermes/GMR decisions, execution flow | `src/nexus_os/engine/`, `src/nexus_os/gmr/` |
| Monitoring | TokenGuard, VAP/audit, telemetry | `src/nexus_os/monitoring/`, `src/nexus_os/observability/` |

## What Is Verified In This Repo

- Full test suite passes locally: `634 passed` (17 new from safety merge).
- DB encryption policy hard-fails by default and allows plaintext fallback only when `allow_unencrypted=True`.
- Engine task dependency cycle detection is present and verified.
- Project-level `AGENTS.md` now describes Nexus operating rules.
- Codex connector hygiene is isolated to `.codex/plugin_hygiene_policy.md`.

## Safety Consolidation (merged 2026-05-18)

From Codex `github/main` — adapted to `src/nexus_os/` layout:

| Module | File | Purpose |
|---|---|---|
| Security Sanitizer | `src/nexus_os/security/sanitizer.py` | Prompt injection + ANSI escape filtering on terminal output |
| Token Policy | `src/nexus_os/monitoring/token_policy.py` | Rate limiting, budget enforcement per agent/lane |
| Token Guard | `src/nexus_os/monitoring/token_guard.py` | Runtime token consumption tracking + hard stops |
| Memory Adapter | `src/nexus_os/vault/memory_adapter.py` | Trust-scored memory storage/retrieval with layer promotion |
| Trust Kernel v2 | `src/nexus_os/governor/trust_kernel.py` | CDR-stage trust decisions, lane isolation |
| Trust Engine v2 | `src/nexus_os/governor/trust_engine_v2.py` | CDR stage machine (Contain→Detect→Respond) |
| Proof Chain | `src/nexus_os/governor/proof_chain.py` | VAP chain creation/verification, tamper detection |
| Compliance | `src/nexus_os/governor/compliance.py` | Policy enforcement engine |
| Kaiju Auth | `src/nexus_os/governor/kaiju_auth.py` | Impact/intent-based authorization with hold queue |
| MCP Server | `src/nexus_os/mcp/server.py` | NexusGovernanceMCP server |
| FunctionGemma Router | `src/nexus_os/mcp/functiongemma_router.py` | Intent classifier + routing for function calling |

All 82 new tests pass. No regressions on existing 552 tests.

## Appendix Assets Available But Not Yet Canonical

The following useful assets are present in `C:\Users\speci.000\Downloads` but are not yet integrated as canonical tracked Nexus files:

| Asset | Status |
|---|---|
| `governor_skill_gate.py` | Reference GSPP/Governor implementation; requires diff review before promotion. |
| `gspp_openapi.yaml` | Reference GSPP OpenAPI spec; not yet canonical in this repo. |
| `wiki_pipeline.py` | Reference DoppelGround wiki/proposal pipeline; not yet canonical in this repo. |
| `PROJECT_HANDOFF_SPEC.md` | External-team handoff reference; not yet canonical in this repo. |
| Downloads `dg_to_gspp.py` | Fuller converter than the current root file; requires reconciliation before replacement. |

Current root files with related functionality:

- `dg_to_gspp.py`
- `mock_api_server.py`
- `langfuse_tracker.py`
- `supabase_client.py`

Phase 0 guidance documents:

- `PHASE0_IMPLEMENTATION_PACKAGE.md`
- `CODEX_HANDOFF.md`

## Accepted Principles

- Governance Control Plane first: Python/FastAPI is canonical.
- Dashboard second: Bun/Next/relay layers must proxy governance state, not contain governance decisions.
- Retroactive provenance starts dry-run/report-only.
- Mini Model Arena starts in Phase 0 as a bounded evidence tool.
- GVAW is mandatory for externalized work: proposal-linked branches, VAP/trust trailers, reviewed merges.
- Public/private split is required before launch.
- Cloud/local OpenClaw coordination uses Git as the bus; cloud writes tasks/specs, local runs GPU/model/TWAVE work.

## Rejected Or Parked

- Bun relay calling Python classes directly.
- Auto-committing retroactive provenance.
- Broad `git add .` without review.
- Deleting model packs without inventory, backup, and rollback path.
- Heretic/uncensoring or fine-tuning in P0.
- External handoff before DoppelGround leak status is resolved.
- Claims of cryptographic VAP, full A2A, OWASP ASI, SkillFortify, or production ASBOM maturity unless locally verified.

## Critical Blockers

1. DoppelGround leak status must be resolved before external handoff or public repo flip.
2. Dashboard/relay still needs real governance API wiring.
3. GSPP reference assets from Downloads need reconciliation before they become canonical.
4. Public launch files still need security/legal review before public release.
5. Sandbox/mock env files must not be committed without an explicit policy decision.
6. Review-chain package claims must be grounded against tracked repo files before implementation.

## Canonical P0 Sequence

1. Reverify the test baseline before core commits.
2. Keep Git clean with explicit-path staging only.
3. Triage DoppelGround gitleaks report to real secret vs false positive.
4. Add or update a canonical integration ledger for repos, ports, APIs, and protected files.
5. Build Python/FastAPI governance endpoints: `/skills/propose`, `/skills/status/{id}`, `/dashboard/stats`, `/governance/proposals`, `/governance/approve`.
6. Update dashboard/relay to consume the Python governance API.
7. Add `nexus-scan.py` as dry-run provenance inventory only.
8. Add `model_arena/mini_arena.py` as report-only evidence collection.
9. Build `nexus_knowledge_base/` from sanitized DoppelGround exports with evidence hashes and quality labels.
10. Handoff to external teams only after security and governance API gates pass.

## Port Map

- `7352`: Nexus governance/control API and dashboard stats.
- `7353`: TWAVE wrapper under `/twave/*`.
- `11434`: local Ollama; internal only, not for external teams.

## Untracked Drafts Requiring Review

These files/directories are currently untracked and intentionally not committed yet:

- `nexus_knowledge_base/`
- `sandbox/`
- `test_integration.py`

Reason: they contain policy, onboarding, sandbox, or integration-test draft content that needs separate content/security review.

`CONTRIBUTING.md` and `ONBOARDING.md` have been promoted to canonical documentation once reviewed and committed.
