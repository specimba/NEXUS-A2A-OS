# CDP lane conversation styles (Grok vs Zo)

Same **composer keys** on both: **Shift+Enter** = newline, **Enter** = send (`cdp_compose_submit.mjs`).

## Grok (grok.com) — fast, iterative

- Model bias: **short, fast** answers; often stops early or offers **1-2-3 / A-B-C** choices.
- Hermes playbook:
  - Prefer **several short CDP messages** over one wall of text.
  - Nudge with: `continue`, `proceed`, `go on`, `2`, `B`, or pick the listed option explicitly.
  - Use `send_grok_cdp.ps1 -Nudge continue|proceed|goon|1|2|3|A|B|C` or `-PromptFile prompts/grok/...`
  - **Do not** wait minutes for Grok; probe and send next nudge in same session.
  - Long specs: split across 2–4 sends (football pass).

## Zo (zo.computer) — long-run, patient

- Model bias: **deep work**, long thinking, detailed analysis.
- Hermes playbook:
  - **One substantive handoff** per task slice; then **wait** (`wait_zo_idle_cdp.ps1`, default 10–15 min).
  - **No** rapid follow-ups while `visibleTail` contains `Zo is thinking`.
  - Use full prompts in `.md`; multiline OK (Shift+Enter between lines).
  - Reply only after Zo finishes or user pastes `[ZO-PLAN]` / output.

## Scripts

| Lane | Send | Wait |
|------|------|------|
| Grok | `send_grok_cdp.ps1`, `grok_zo_cdp_lane.ps1 -Action NudgeGrok` | optional short 5s |
| Zo | `send_zo_cdp.ps1` (waits idle by default) | `wait_zo_idle_cdp.ps1 -MaxWaitSec 900` |

## Code entrypoints

- Grok tab match: `--required grok.com`
- Zo tab match: `--required zo.computer`
- Both share: `grok_cdp_director.mjs`, `cdp_compose_submit.mjs`