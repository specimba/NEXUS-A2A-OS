# NEXUSLOGS Hard Rule — Grok Build 4.5 / Ubuntu Grok sessions

| Field | Value |
|-------|-------|
| **Policy ID** | NEXUSLOGS-GB-001 |
| **Status** | ADOPTED 2026-07-09 |
| **Vault** | `C:\Users\speci.000\Downloads\NEXUSlogs` (WSL: `/mnt/c/Users/speci.000/Downloads/NEXUSlogs`) |
| **Applies to** | Grok Build (this agent), any session that claims development on NEXUS from Grok Build TUI / Ubuntu bridge |

## Naming

```
NEXUSbuildubuntuGROK45logs-NN.txt
```

- `NN` is a zero-padded sequence: `01`, `02`, `03`, …
- **Never** overwrite an existing file. Always allocate the next free index.
- Optional sibling notes: `NEXUSbuildubuntuGROK45logs-NN_INDEX.md` (short TOC only).

## Line budget (context integrity)

| Soft max | Hard max | Rule |
|----------|----------|------|
| **1500 lines** | **3000 lines** | Prefer ≤1500 for reviewable chunks. **Never** cut mid-section past hard max — open `-NN+1` and continue with a **CONTINUATION** header. |

When rotating mid-session:

1. Close current file with a footer: `=== END PART NN — CONTINUE IN PART NN+1 ===`
2. Open next index with: `=== CONTINUATION of NEXUSbuildubuntuGROK45logs-NN ===`
3. Copy the last 15 lines of previous part as bridge context (not full re-dump).

## Required content (every part)

1. **Header** — date, session id if known, branch, operator, agent model (`grok-build-0.1` etc.)
2. **Goals** this slice
3. **Paths touched** (repo + Downloads vaults)
4. **Commands run** (with evidence: exit codes, key JSON snippets — redact secrets)
5. **Code / config changes** — file paths + behavioral intent (not entire 3k-line dumps of every file)
6. **Commits** — hash + subject
7. **Open blockers / next**
8. **Pointer to related docs** under `Documents\NEXUS\docs\` and ARCHIVIST

## Export recovery

If the Grok UI says "Conversation exported to GROK45logs01" but the file is missing:

1. Search Downloads, Desktop, Documents, browser download folder.
2. Prefer reconstructing from:
   - `~/.grok/sessions/.../chat_history.jsonl` (session-local)
   - git log / docs/reviews written during the session
3. Write the reconstructed log under the **canonical vault name** above (do not leave only a random download name).

## Agent review contract

Other agents (Hermes, Codex, OpenCode, Fable5, antiGRAV, Kilo) treat these files as **evidence inputs**, not canonical state, until reconciled into:

- `01_PROJECT_STATE.md` (proposal-gated)
- `docs/reviews/*`
- grounded commits

## Rotation helper

```powershell
cd C:\Users\speci.000\Documents\NEXUS
python scripts\append_grok45_nexuslog.py --status   # next index
python scripts\append_grok45_nexuslog.py --write path\to\draft.txt
```
