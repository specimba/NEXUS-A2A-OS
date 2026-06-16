# Codex Setup Preservation Checklist

Date: 2026-06-06
Scope: preservation-first setup planning for `C:\Users\speci.000\Documents\NEXUS`

## Objective

Create or refine new Codex setup behavior without deleting or modifying existing TOML, config, `AGENTS.md`, or AGENTS-related files.

## Protected Inputs

Treat these as read-only during the first setup slice:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/plugin_hygiene_policy.md`
- `pyproject.toml`
- Any `*.toml`, `*.conf`, `*.config`, or nested `AGENTS.md` files discovered in repo-local worktrees or agent folders

## Current Evidence

- `01_PROJECT_STATE.md` is present and remains the canonical project-state doc.
- `knowledge.md` was requested by `AGENTS.md` but is not present at repo root.
- `git status --short` shows an already dirty workspace with modified, deleted, staged, and many untracked files.
- Existing repo rules prohibit broad `git add .`, duplicate canonical docs, and unreviewed deletion of local models or archives.
- Existing Codex plugin policy says local filesystem inspection should prefer local files, git state, Nexus skills, and tests over external plugins.

## Safe First Slice

1. Record the setup goal and constraints in a new artifact only.
2. Inventory protected files with read-only commands.
3. Identify the intended new setup surface before any code or config change.
4. Propose new-file-only changes for the first implementation pass.
5. Keep any migration or cleanup as a later explicit operator decision.

## Pre-Edit Gate

Before any future implementation edit, verify:

- `git status --short` has been reviewed.
- The target file is new, or the operator explicitly approved modifying it.
- No existing TOML, config, `AGENTS.md`, or AGENTS-related file is in the edit set.
- No generated caches, model files, research dumps, mock secrets, or sandbox files are staged.
- The change is bounded to one coherent setup slice.

## Verification Gate

Minimum evidence for claiming the setup slice is complete:

- File diff for the new setup artifact or new setup code.
- Focused test or dry-run command when code is introduced.
- Explicit list of protected files left untouched.
- Final `git status --short` summary.

## Later Optional Work

Only after explicit approval:

- Reconcile the missing `knowledge.md` reference.
- Add a new setup-specific policy file.
- Add tests for setup discovery or preservation checks.
- Update existing config files if the operator approves a concrete migration.
