# AGENTS.md - Nexus OS Agent Operating Protocol

## Mission
Nexus OS is a governed, local-first agent operating system. Every agent working in this repository must preserve the core invariant: actions are evidence-grounded, proposal-bound where appropriate, test-gated, and auditable.

## System Boundaries
- Nexus OS is the governance and orchestration layer.
- DoppelGround is the evidence preparation layer.
- TWAVE is the low-VRAM execution layer and remains wrapper-only unless its HOLD state is explicitly lifted.
- GeniusTurtle is the operator UI layer and must not embed model weights, secrets, or governance internals.
- Model Arena is an evidence tool; it reports model performance and must not delete, fine-tune, or promote models automatically.

## Source Of Truth
- Read `01_PROJECT_STATE.md` first for the current canonical state.
- Prefer filesystem state, tests, git history, and canonical docs over chat memory.
- Read current files before making claims or edits.
- Treat downloaded reports and external team notes as input evidence, not canonical state, until reconciled into tracked docs.
- Do not create duplicate canonical files with conflicting content. Merge toward one clear source of truth.

## Core Architecture Map
- Bridge: external protocol boundary, API ingress, SDK/MCP adapters, secrets lookup.
- Governor: KAIJU gates, policy checks, trust scoring, compliance, approval/denial decisions.
- Vault: 5-track memory, durable records, encryption policy, trust persistence.
- Engine/GMR: task routing, Hermes decisions, circuit breakers, model selection, execution flow.
- Monitoring: TokenGuard, VAP/audit logs, telemetry, stress/weight-room evidence.

## Execution Rules
- Keep changes bounded to one coherent task slice.
- Do not run broad refactors without reporting the planned refactor first.
- Do not stage or commit sandbox files, mock secrets, raw research dumps, model weights, generated caches, or unreviewed downloads.
- Do not use `git add .` in this repository. Stage explicit reviewed paths only.
- Do not delete local models or archives without an inventory, backup, and rollback path.
- Do not expose Ollama, private weights, DoppelGround raw sessions, or core TWAVE internals to external teams.

## Governance Gates
- No "done" claim without verifiable evidence: test output, diff, file path, or explicit reviewed artifact.
- Core code changes require focused tests; DB, router, governor, bridge, vault, or GMR changes require the full suite unless explicitly blocked.
- Security-sensitive changes require hard-fail defaults and development-only escape hatches that are explicit in config.
- Retroactive provenance tools must start in dry-run/report-only mode. They may not auto-commit, auto-approve, or auto-create governance records until reviewed.

## Git Discipline
- Check `git status --short` before staging.
- Separate unrelated work into separate commits.
- Leave unknown or unrelated user/agent changes unstaged unless the user explicitly asks to include them.
- Commit messages should state the behavioral change and verification result.
- GVAW target: proposal-linked branches, VAP/trust trailers, reviewed merges, and no direct unreviewed mainline changes.

## External Team Rules
- TWAVE wrapper team gets API contracts and mocks only, with port `7353` under `/twave/*`.
- GeniusTurtle UI team gets UI contracts and mock APIs only.
- Nexus governance API remains the canonical backend on port `7352`.
- Public-facing repos must pass leak scanning and must not contain private research, secrets, model weights, or raw evidence dumps.

## Codex-Specific Connector Policy
Codex plugin/tool hygiene is not a Nexus architecture rule. Keep it in `.codex/plugin_hygiene_policy.md` and apply it only to Codex workflow behavior.
