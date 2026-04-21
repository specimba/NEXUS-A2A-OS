# Contributing To Nexus OS

This repository is governed infrastructure. Contributions must preserve the core invariant: changes are evidence-grounded, bounded, test-gated, and auditable.

## Read First

Before opening an issue, branch, or pull request, read:

- `01_PROJECT_STATE.md`
- `AGENTS.md`
- `04_GOVERNANCE.md`
- `02_ARCHITECTURE.md`

If those files conflict with chat history or external reports, tracked repository files win.

## Contribution Scope

Accepted contribution areas:

- Tests for existing behavior.
- Documentation that clarifies verified repository state.
- Bug fixes with focused diffs and test evidence.
- API/interface work that preserves the Python governance backend as canonical.
- Mock or wrapper work that does not expose private models, raw DoppelGround exports, or TWAVE internals.

Not accepted in Phase 0 without explicit approval:

- TWAVE algorithm changes.
- Model deletion, promotion, fine-tuning, or uncensoring work.
- Automatic provenance commits or automatic governance approvals.
- Raw research dumps, model weights, `.env` files, secrets, or generated caches.
- Claims of cryptographic VAP, full A2A maturity, OWASP ASI coverage, SkillFortify, or production ASBOM maturity unless locally verified.

## Git Workflow

- Do not use `git add .`.
- Stage explicit reviewed paths only.
- Keep unrelated work in separate commits.
- Do not include sandbox files, mock credentials, generated caches, local databases, or downloaded archives unless explicitly approved.
- Commit messages must state the behavior changed and the verification result.

Recommended commit format:

```text
type(scope): concise behavior change

Explain what changed, why it is safe, and the verification command/result.
```

Examples:

```text
fix(engine): correct dependency cycle traversal

Follow dependency edges downstream during cycle detection.
Verified with tests/engine/test_router.py and full suite: 617 passed.
```

```text
docs(state): add canonical Nexus project state

Capture current local HEAD, verification gate, blockers, and P0 sequence.
No runtime code changed.
```

## Governance Requirements

All implementation work must satisfy the relevant gate:

- Core code changes require focused tests.
- DB, router, governor, bridge, vault, GMR, or monitoring changes require the full test suite unless explicitly blocked.
- Security-sensitive defaults must fail closed.
- Development escape hatches must be explicit in configuration.
- Retrospective provenance tools must start as dry-run/report-only.

## External Team Boundaries

TWAVE wrapper work:

- Allowed: wrapper API, health checks, artifact handling, VRAM pre-checks, structured error responses.
- Not allowed: TWAVE math, quantization algorithm changes, ABI/runtime redesign, private internals.
- Canonical port: `7353` under `/twave/*`.

GeniusTurtle UI work:

- Allowed: UI surfaces, mock API integration, operator workflows.
- Not allowed: model weights, direct Ollama exposure, embedded governance decisions, secrets.

Nexus governance work:

- Python/FastAPI is the canonical governance control plane.
- Dashboard, Bun, Next.js, and relay layers are proxies or clients only.
- Canonical port: `7352`.

## Attribution And License Position

Until a final `LICENSE` is committed, contributors must not assume public/commercial terms beyond what is explicitly tracked in this repository.

Every external contribution must include attribution when it uses or adapts external sources:

- Paper, repository, dataset, or article references.
- Prior implementation source.
- Generated code source when relevant to licensing or provenance.

Recommended attribution footer for non-trivial files:

```text
Attribution:
- Author: <name or handle>
- Source: <paper/repo/link if applicable>
- Notes: <short provenance note>
```

By submitting a contribution, you confirm that you have the right to contribute it and that it may be incorporated into Nexus OS under the repository's final tracked license terms.

## Pull Request Checklist

- Read `01_PROJECT_STATE.md`.
- Diff is bounded to one coherent task.
- No secrets, raw dumps, model weights, `.env` files, generated caches, or local databases.
- Tests or verification evidence included.
- Documentation updated when behavior or boundaries change.
- Public/private boundaries preserved.
- Any appendix asset promoted from Downloads is clearly reconciled against canonical repository files.

