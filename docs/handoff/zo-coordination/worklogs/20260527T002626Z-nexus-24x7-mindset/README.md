# NEXUS 24/7 Mindset — Implementation Worklog

Created: 2026-05-27 00:26 UTC  
Trigger: operator request — "make OpenClaw work in background with NEXUS OS needs / research / progression / dataset ideas".

## Strategy decision

The operator asked for 24/7 NEXUS work. There were two candidate drivers:

1. **OpenClaw native agent** (`openclaw agent --local --model …`)
2. **Zo automations** calling ModelRelay (the path that already works)

**Picked (2). Documented why (1) is not ready below.**

## OpenClaw blocker (carried over from Phase C smoke)

Tested locally on 2026-05-27 00:24 UTC:

```text
$ openclaw agent --agent main --message "..." \
    --model "nvidia_nim/deepseek-ai/deepseek-v4-flash" --local --json
[diagnostic] lane task error: FailoverError: Unknown model: nvidia_nim/deepseek-ai/deepseek-v4-flash
[model-fallback/decision] reason=model_not_found next=none
```

`nvidia_nim` is registered with 12 models in `/root/.openclaw/agents/main/agent/models.json`, but the local agent runtime only resolves provider names from its built-in plugin set (openai, anthropic, openrouter, …). Custom providers in `models.json` are not loaded.

**Implication**: OpenClaw can't run NEXUS work autonomously today, even with valid NIM credentials. The fix requires either a custom-provider plugin or routing NIM through OpenClaw's `openrouter`-style adapter — neither is in this slice.

## What the operator wanted: 7 automations now live (3 new today, 3 carried, 1 PR watcher)

### NEW — added 2026-05-27 ~03:25 Istanbul

| Name | Cadence | Output | Slack on silence? |
|---|---|---|---|
| `Zo-NEXUS-Research-Scout` | every 6h | `docs/research/scout/YYYY-MM-DD-HH.md` | silent |
| `Zo-NEXUS-Progression-Tracker` | 06:00 + 18:00 | `docs/progression/YYYY-MM-DD-HH.md` | silent (only on new blocker or push failure) |
| `Zo-NEXUS-Dataset-Ideation` | Sun 10:00 | `docs/datasets/proposals/YYYY-Www.md` | 3-line summary on Slack |

### Already active — carried

- `Zo-NEXUS-Morning-Brief` (daily 08:30) — state digest
- `Zo-NEXUS-PR-Watcher` (every 6h) — PR status
- `Zo-NEXUS-Nightly-Audit` (daily 22:00) — anomaly scan

## Strategy: outputs are committed artifacts, not Slack chatter

Each new automation:

- Writes a **dated file** to a documented folder.
- **Commits and pushes** (fast-forward only).
- **Stays silent on Slack** unless there's real signal (≥3 research findings, a new blocker, weekly summary).

This means the 24/7 effort accumulates as a research / progression / dataset trail in the repo, reviewable later, not as channel noise.

## Hard boundaries baked into every instruction

- No `--force` push (regular fast-forward only).
- No edits outside the automation's designated folder.
- No secrets, tokens, or pairing IDs in any output.
- No service restarts, no `paired.json` edits, no `telegram-claw-gateway` re-enable.
- Dataset automation: no data acquisition, no HuggingFace login, no scraping behind auth — specs only.

## Open items for next slice (not done here)

1. **OpenClaw provider plugin**: write/install a custom-provider plugin so `nvidia_nim/<model>` resolves locally. This is the path that would let OpenClaw itself become a 24/7 driver instead of just Zo.
2. **First-run validation**: the new automations don't run until their next trigger. First validation pass scheduled:
   - Progression tracker: 2026-05-27 06:00 Istanbul
   - Research scout: 2026-05-27 ~09:25 Istanbul
   - Dataset ideation: 2026-05-31 10:00 Istanbul
3. **Push collision plan**: if Windows-side commits land between Zo automation pushes, the automation is instructed to STOP (no force-push) and report. The recovery path is operator-driven `git pull --rebase` on Zo side.

## Files added (this commit)

```
docs/research/scout/README.md
docs/progression/README.md
docs/datasets/proposals/README.md
docs/handoff/zo-coordination/worklogs/20260527T002626Z-nexus-24x7-mindset/README.md  ← this file
```

## Automations created (Zo platform, not in repo)

Three new automation IDs visible in `list_automations`. Operator can edit/disable via the Automations tab in the Zo UI.
