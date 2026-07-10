# NEXUSLOGS Hard Rule — Grok Build 4.5 / Ubuntu Grok sessions

| Field | Value |
|-------|-------|
| **Policy ID** | NEXUSLOGS-GB-001 |
| **Status** | ADOPTED 2026-07-09 (clarified: full content, no tiny parts) |
| **Vault** | `C:\Users\speci.000\Downloads\NEXUSlogs` (WSL: `/mnt/c/Users/speci.000/Downloads/NEXUSlogs`) |
| **Applies to** | Grok Build (this agent), any session that claims development on NEXUS from Grok Build TUI / Ubuntu bridge |

## Naming

```
NEXUSbuildubuntuGROK45logs-NN.txt
```

- `NN` is a zero-padded sequence: `01`, `02`, `03`, …
- Prefer **appending** into the latest part until the hard line max. Only allocate the next index when the current part is near the rotation ceiling (or when reinstalling a full `/export` into a known index).
- Optional sibling notes: `NEXUSbuildubuntuGROK45logs-NN_INDEX.md` (short TOC only).
- Optional operator guide: `NEXUSbuildubuntuGROK45logs_README.txt` in the vault.

## Line budget (context integrity)

| Soft max | Hard max | Rule |
|----------|----------|------|
| **1500 lines** | **3000 lines** | These are **rotation ceilings only**. Fill each part with the **full** conversation (every user message, assistant reply, commands, code, evidence). Do **not** keep parts artificially tiny (~100–300 lines). Do **not** summarize away dialogue. Do **not** open a new file every ~100 lines. When approaching soft max (~1500), finish the current section cleanly; at hard max (3000), open `-NN+1`. **Never** cut mid-sentence or mid-code block. |

### Full-content requirement

- Prefer Grok TUI **`/export <name>`** as the source of truth for dialogue.
- **Where `/export` writes:** relative to the TUI **session cwd** (often WSL `/home/speci/<name>`). It does **not** automatically land in `Downloads\NEXUSlogs`.
- Immediately **install** the export into the vault:

```bash
# WSL
python3 /mnt/c/Users/speci.000/Documents/NEXUS/scripts/append_grok45_nexuslog.py \
  --install-export /home/speci/GROK45logs01 --force-index 1 --overwrite
```

```powershell
# PowerShell (from repo)
python scripts\append_grok45_nexuslog.py --install-export C:\path\to\export --force-index 1 --overwrite
```

- After export, **append** any newer turns into the same vault part if under hard max, else next index.
- Thin "status summaries" are **policy violations**. If one is written by mistake, rename it `*.thin_summary_bak` and replace with full content.

When rotating mid-session:

1. Close current file with a footer: `=== END PART NN — CONTINUE IN PART NN+1 ===`
2. Open next index with: `=== CONTINUATION of NEXUSbuildubuntuGROK45logs-NN ===`
3. Copy the last 15 lines of previous part as bridge context (not full re-dump).

## Required content (every part)

1. **Header** — date, session id if known, branch, operator, agent model (`grok-build-0.1` etc.)
2. **Full dialogue** when available via `/export` or hand-transcribed turns (user + assistant + important tool evidence)
3. **Paths touched** (repo + Downloads vaults)
4. **Commands run** (with evidence: exit codes, key snippets — redact secrets)
5. **Code / config changes** — file paths + behavioral intent
6. **Commits** — hash + subject
7. **Open blockers / next**
8. **Pointer to related docs** under `Documents\NEXUS\docs\` and ARCHIVIST

## Export recovery

If the Grok UI says "Conversation exported to GROK45logs01" but the vault is empty:

1. Check **session cwd** first: `/home/speci/GROK45logs01` (or the name you passed to `/export`).
2. Also search Downloads, Desktop, Documents, browser download folder.
3. Prefer reconstructing from:
   - `~/.grok/sessions/.../chat_history.jsonl` (session-local; may be post-compaction only)
   - `~/.grok/sessions/.../compaction/segment_*.md` (verbose historical turns)
   - git log / docs/reviews written during the session
4. Write the reconstructed log under the **canonical vault name** above.

## Agent review contract

Other agents (Hermes, Codex, OpenCode, Fable5, antiGRAV, Kilo) treat these files as **evidence inputs**, not canonical state, until reconciled into:

- `01_PROJECT_STATE.md` (proposal-gated)
- `docs/reviews/*`
- grounded commits

## Rotation / install helper

```powershell
cd C:\Users\speci.000\Documents\NEXUS
python scripts\append_grok45_nexuslog.py --status
python scripts\append_grok45_nexuslog.py --install-export path\to\export
python scripts\append_grok45_nexuslog.py --append path\to\more.txt
```

```bash
# WSL
python3 /mnt/c/Users/speci.000/Documents/NEXUS/scripts/append_grok45_nexuslog.py --status
python3 /mnt/c/Users/speci.000/Documents/NEXUS/scripts/append_grok45_nexuslog.py --append /path/to/more.txt
```
