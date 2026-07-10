# GND-001: Mandatory 24-Hour Deep Grounding Protocol

| Field | Value |
|-------|-------|
| **Policy ID** | GND-001 |
| **Status** | ADOPTED |
| **Effective** | 2026-07-08 |
| **Owner** | NEXUS Governance Layer |
| **Scope** | All NEXUS agents (Kilo, Fable 5, Hermes, Antigravity, Codex, ARCHIVIST) |

## Purpose

Ensure that any agent operating in NEXUS achieves genuine situational awareness before making claims, taking actions, or producing reports. Surface sweeps produce false confidence. Full-coverage reads produce real grounding.

## When This Applies

- Resuming work after context loss or session boundary
- Operating in autonomous/AFK mode
- Producing status reports or project state claims
- Before making governance decisions or taking actions with side effects

## Requirements

### 1. File Coverage Mandate

- **ALL files** modified or created within the grounding window (24 hours default) MUST be read in full.
- "Full" means: every line of every file, using multi-chunk reads as needed.
- Partial reads (first N lines, grep-only, summary-only) are **prohibited** for grounding purposes.
- Exception: Binary files, model weights, generated caches — these are skipped with explicit notation.

### 2. Read Order

1. `01_PROJECT_STATE.md` — canonical state
2. `knowledge.md` — project overview
3. Most recently modified files in `NEXUSlogs/` — sorted by modification time, newest first
4. Most recently modified files in `ARCHIVIST/` — sorted by modification time, newest first
5. `docs/plans/` and `docs/roadmaps/` — if modified within window
6. `config/models.registry.json` — if modified within window

### 3. Synthesis Requirements

After completing all reads, the agent MUST produce:

- **Active Blockers List** — ordered by severity, with source file and line numbers
- **Critical Security Findings** — with fix status (FIXED/UNFIXED/IN_PROGRESS)
- **Model Intelligence Summary** — current status of all known models
- **Infrastructure State** — port map, service health, provider status
- **Execution State** — what's done, what's in progress, what's blocked
- **Action Items** — prioritized P0/P1/P2 with owners

### 4. Evidence Standards

- Every claim MUST cite source file and line number
- "DONE" claims require test output, commit hash, or file diff
- "BLOCKED" claims require error message or verification command
- "UNFIXED" claims require the specific vulnerability or bug description

### 5. Anti-Patterns (Prohibited)

- ❌ Surface sweeping (grep-only, first-100-lines-only)
- ❌ Summary-of-summary (reading someone else's summary instead of the source)
- ❌ Parallel NIM reads that trigger 429 exhaustion
- ❌ Claiming "all done" without evidence
- ❌ Ignoring files because they're "too long"
- ❌ Reading project state files instead of the actual log files

### 6. Cadence

- **Minimum**: Once per session start
- **Recommended**: Every 4 hours during continuous operation
- **Mandatory**: Before any governance decision, commit, or autonomous action with side effects

## Verification

- Grounding sweep output must include file count, total lines read, and coverage percentage
- Any file skipped must be explicitly listed with reason
- The `nexusctl grounding doctor --json` command should be run before and after the sweep to detect evidence drift

## Enforcement

- KAIJU gate should verify grounding completeness before approving actions with side effects
- Autonomous mode (SAFETY-4) requires grounding sweep completion as prerequisite
- Handoff packages (via `nexusctl handoff`) must include grounding sweep metadata

## History

| Date | Event |
|------|-------|
| 2026-07-08 | Policy drafted after 41,021-line grounding sweep across 12 files |
| 2026-07-08 | Adopted by operator approval |
