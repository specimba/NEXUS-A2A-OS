---
skill_id: skill-smith
name: SkillSmith Self-Improvement
version: 1.0
task_type: meta
pattern: "(improve|optimize|refine) (skill|prompt|workflow)"
recommended_model: osman-reasoning
---

# SkillSmith — Pattern Extraction & Workflow Refinement

## Extracted Patterns (from Nexus OS v3.0 P0 completion)

### 1. Budget-First Enforcement
TokenGuard pre-checks must precede execution paths. Never treat token tracking as passive telemetry.
- **Before**: Token tracking after execution.
- **After**: Pre-check → 429 deny if exceeded → track only after success.

### 2. Proof Split (FILE_CONFIRMED vs CODE_CONFIRMED)
Distinguish design claims backed by documentation from implementation claims backed by source code.
- **FILE_CONFIRMED**: `.pi/*.md`, `worklog.md`, specs.
- **CODE_CONFIRMED**: `src/nexus_os/**/*.py`, test results.

### 3. Trust Invariants (Non-Negotiable)
Any trust or routing design must preserve:
- Lane-scoped parameters
- Non-compensatory harm thresholds (`R > Rcrit → -1 or hold`)
- Hot/warm/cold execution boundaries

### 4. Named Evidence Counts
Verification reports must include explicit subsystem pass counts (e.g., `Trust: 17/17`, `Token Integration: 14/14`).

### 5. Queue-Driven Coordination
Use file-queue protocols (`pending/` → `done/` → `failed/`) with worker specialization and replay-safe task files.

### 6. Operator Visibility
Routing and telemetry designs must expose live endpoints, refresh cadence, and savings outputs.

## Integration Targets
- `AGENTS.md` (global and project-level)
- `CODEX_WORKFLOW.txt`
- All `SKILL.md` definitions
- Architecture review checklists
