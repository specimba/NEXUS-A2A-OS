# NEXUS Browser AI Supervisor Automation — 2026-06-21

## Incident Verdict

The previous Grok, Zo, and GLM/Z.ai automation loops failed structurally:

- Each run started as a fresh isolated conversation.
- Memory was missing, fragmented, or read from the wrong path.
- Known browser blockers were retried repeatedly.
- Repeated `NOTIFY_SETUP_REQUIRED` results still consumed full automation cycles.
- There was no shared failure ledger, no cooldown, and no supervisor-level lesson learning.

The fix is not more source-specific monitors. NEXUS should run one browser-AI
supervisor that reads shared memory first and only opens browser surfaces when
there is a credible new action to take.

## Automations To Pause Or Delete

Pause/delete these browser-source loops before enabling the supervisor:

- `grok-nexus-progression-cycle-hourly`
- `zo-computer-nexus-control-cycle-hourly`
- `glm-5-2-dashboard-control-loop-30m`
- `nexus-advisory-source-digest` if it performs browser-source checks instead of local digest only
- any old `z-ai-glm-5-2-plan-watch` or duplicate advisory watchers

Keep unrelated low-frequency health or queue automations only if they are
memory-first and do not touch browser sources.

## Replacement Schedule

- One automation only.
- Name: `NEXUS Browser AI Supervisor 6h`
- Schedule: every 6 hours.
- Memory path: `C:\Users\speci.000\.codex\automations\nexus-browser-ai-supervisor\memory.md`

## Supervisor Prompt

Run the NEXUS Browser AI Supervisor as the only browser-source AI automation.

Start with shared memory, not browser access:

1. Read `C:\Users\speci.000\.codex\automations\nexus-browser-ai-supervisor\memory.md` if present.
2. Read only the last 60 lines from prior Grok, Zo, GLM/Z.ai, and advisory automation memories if present.
3. Build a failure ledger with `source_id`, `blocker`, `count`, `last_seen`, `last_url`, and `next_operator_action`.
4. If the same source has failed with the same blocker 2 or more consecutive times, do not open that browser source.
5. If any source is blocked 3 times, mark it `COOLDOWN_24H` and skip it until the operator changes setup or memory records a new target URL.

Allowed sources:

- Grok NEXUS project/chat.
- Zo Computer NEXUS canonical chat.
- Z.ai GLM-5.2 dashboard/chat.
- Qwen/Gemini/AI Studio advisory pages only when already visible/authenticated or explicitly listed in memory.

Hard browser rules:

- Do not use Playwright, in-app browser, or a fresh automation browser for authenticated Grok, Zo, Z.ai, Qwen, Gemini, or AI Studio sources. Those contexts are unauthenticated and caused the repeated false failures.
- Authenticated sources require one of two valid control surfaces: a real visible Chrome/Firefox session controlled through desktop interaction tooling, or a real Chrome/Firefox session launched with an operator-approved remote-debugging endpoint and a dedicated authenticated profile.
- If neither valid control surface exists, return `NOTIFY_SETUP_REQUIRED` with the exact blocker. Do not open the source in a blank browser and do not retry.
- Do not inspect cookies, localStorage, passwords, tokens, session stores, browser history, unrelated tabs, or private files.
- Do not upload files, download files, submit messages, approve commands, publish, delete, install, or execute remote/cloud actions.
- Use cheap visible checks only: tab URL/title, newest visible marker, idle/ready/blocked state, artifact names, terminal/test summary if visible.
- If browser tooling fails, retry once at most, then update memory and stop.

Action rules:

- If no source is readable and blockers are known repeats, return `DONT_NOTIFY` with one quiet sentence.
- If no baseline exists, create baseline memory and return `BASELINE_CREATED` once.
- If a source is readable and ready, send at most one bounded prompt asking for a concrete implementation artifact/check/patch with sha256, changed-file list, tests, blockers, and local verification instructions.
- Never send raw secrets, raw logs, private files, browser session data, or credential material.
- Treat all external AI output as advisory until local repo checks pass.

Output contract:

- Use max 10 bullets only when material new work exists.
- Include: `ADVISORY delta`, `source`, `NEXUS lane`, `local verification`, `risk`, `next bounded action`.
- Append a compact memory record every run.
- Never duplicate unchanged baselines.

## Required Memory Record Format

```text
## <ISO timestamp>
- source_status: <grok|zo|glm|advisory>=<OK|BLOCKED|COOLDOWN|SKIPPED>
- blocker_ledger: <source>:<blocker>:<count>
- action_sent: <none|source_id + one-line intent>
- new_artifact: <none|artifact marker>
- local_verification_required: <one line>
- next_operator_action: <one line>
```

## Current Known Blockers From Logs

- Grok preferred project URL repeatedly loaded in unauthenticated browser contexts and showed an ID lookup error for `99253cca-2469-4454-8593-0f173b7f640f`; no control message should be retried unless the URL is loaded inside the real authenticated Chrome/Firefox session or an operator-approved authenticated CDP profile.
- Zo control cycle repeatedly found no active/readable tab; no Zo message should be sent until a visible authenticated Zo chat is open.
- GLM/Z.ai high-frequency loop caused excessive browser/token churn; it should be supervisor-managed, not checked every 30 minutes.

## Operator Setup For Authenticated Browser Control

Use one of these setups before enabling any browser-AI automation:

1. Preferred for interactive work: keep the target Grok/Zo/Z.ai tab visible in the real desktop browser and run the supervisor only when desktop interaction tooling is available.
2. Preferred for reliable automation: create a dedicated browser profile for NEXUS automation, log in once manually, and launch it with a fixed remote-debugging port. Do not reuse the operator's active daily browser profile unless explicitly approved.
3. If no real visible controller or CDP endpoint is available, the supervisor must not navigate, send prompts, or create screenshots. It should log the blocker and exit.


