# Nexus OS Onboarding

This guide gets a new agent or contributor oriented in five minutes. It is not a replacement for the canonical state file.

## Step 1: Read The State

Read these files in order:

1. `01_PROJECT_STATE.md`
2. `AGENTS.md`
3. `04_GOVERNANCE.md`
4. `02_ARCHITECTURE.md`
5. `README.md`

If chat history, downloaded reports, or external review notes disagree with tracked files, tracked files win.

## Step 2: Understand The Stack

| Layer | Role | Current Boundary |
|---|---|---|
| DoppelGround | Evidence preparation | USE MODE; sanitize before handoff. |
| Nexus OS | Governance and orchestration | Python/FastAPI governance is canonical. |
| TWAVE | Low-VRAM execution | HOLD; wrapper work only. |
| GeniusTurtle | Operator UI | UI/client only; no secrets or model internals. |
| Model Arena | Evaluation evidence | Report-only; no automatic model action. |

## Step 3: Know The Ports

- `7352`: Nexus governance/control API and dashboard stats.
- `7353`: TWAVE wrapper under `/twave/*`.
- `11434`: local Ollama, internal only.

Do not expose `11434` to external teams.

## Step 4: Check The Repo

Before editing:

```powershell
git status --short
git branch --show-current
.\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

Expected verified baseline from the current state file:

```text
617 passed
```

If tests fail before your changes, stop and report the failure before editing.

## Step 5: Choose The Right Work Lane

Safe Phase 0 work:

- Documentation that clarifies verified state.
- Focused bug fixes with tests.
- FastAPI governance API skeleton and contract tests.
- Dashboard proxy work that consumes governance API state.
- Dry-run provenance inventory.
- Report-only model arena scaffolding.

Blocked or approval-required work:

- TWAVE core algorithm changes.
- Model deletion or fine-tuning.
- Public repo flip.
- Auto-committing provenance.
- Auto-approving governance proposals.
- Committing sandbox env files or mock secrets.

## Common Pitfalls

- Do not treat Downloads files as canonical until reconciled.
- Do not use `git add .`.
- Do not combine docs, sandbox, generated artifacts, and core code in one commit.
- Do not claim external-team readiness until leak triage and governance API gates pass.
- Do not let UI or relay code become the governance brain.

## Current Priority

Phase 0 grounding remains active. The next highest-value work is:

1. DoppelGround leak triage.
2. Canonical integration ledger.
3. Python/FastAPI governance API.
4. Dashboard proxy to real governance state.
5. Dry-run provenance scanner.
6. Report-only mini model arena.

## Handoff Rule

When handing work to another agent or team, include:

- Task objective.
- Files allowed to edit.
- Files forbidden to edit.
- Required tests or verification command.
- Expected output artifact.
- Public/private boundary notes.

