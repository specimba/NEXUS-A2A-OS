---
id: NODE-MIG-AUTOMATION_AUDIT_2026_05_23
authority_scope: experimental
origin_sha256: f84395949a7d6a6d35a4d0a6f102c26046f555d63a2fa8bd8f678d6e571a512f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B47822
---
# NEXUS Automation Hygiene Audit - 2026-05-23

<!-- CANARY: 3193110954fb638c4c9432ae8d5ac334 -->
Scope: Codex/Zo/NEXUS scheduled automations visible from `C:\Users\speci.000\.codex\automations` and repo-local handoff evidence.

## Summary

The automations are mostly following their prompts, but several are now low-value repeaters. They are not generally mutating the repo, but they create frequent conversation/history entries and repeatedly spend tokens restating unchanged state.

## Active Automations Reviewed

| ID | Current behavior | Verdict | Action |
|---|---|---|---|
| `zo-nexus-heartbeat` | Hourly, 4-6 minute runs, repeats stale digest/queue/dirty/cycle-check state | Token burner | Pause until delta-cache/silent-no-change mode exists |
| `zo-nexus-pr-watcher` | Every 2 hours, repeats no open PRs and old closed PR failures | Token burner while no PR exists | Pause until active PR or silent-no-change mode exists |
| `zo-nexus-morning-brief` | Daily concise state brief; catches stale digest and baseline drift | Keep | Keep as the main routine summary |
| `nexus-health-check` | Daily read-only health scan, but overlaps morning brief and has stale `--json doctor` prompt text | Useful but too frequent | Downshift to weekly and update prompt later |
| `nexus-queue-runner` | Daily no-op when `tasks/pending` is empty; strict and safe but still creates runs | Useful only when tasks exist | Downshift to weekly or manual unless pending tasks return |
| `nexus-whea-restart-monitor` | Six-hour WHEA monitor; original prompt says pause after 2026-05-20 if no new events | Stale monitor | Pause until a fresh instability window opens |

## Inactive Duplicates

The AoA automations are already inactive but duplicated:

- `aoa-daily-watch-2`
- `aoa-daily-watch-3`
- `aoa-daily-watch-4`
- `aoa-research-sync-2`
- `aoa-research-sync-3`
- `aoa-research-sync-4`

They should stay inactive. If AoA monitoring is needed later, recreate one clean automation instead of reactivating duplicates.

## Evidence

- `zo-nexus-heartbeat` memory shows repeated unchanged branch, queue, stale digest, cycle-check halt, and dirty-state reports across hourly runs.
- `zo-nexus-pr-watcher` memory shows repeated unchanged closed PR #34/#35 and red check status across every two-hour runs.
- `nexus-queue-runner` memory shows strict no-op behavior when `tasks/pending=0`; safe, but low value as a daily job.
- `nexus-health-check` memory shows useful drift reporting, but overlaps with the morning brief and still documents stale doctor command assumptions.
- `nexus-whea-restart-monitor` has no memory file and its original prompt already included a pause recommendation after 2026-05-20 if no fresh restart evidence appeared.

## Recommended Operating Model

Keep only one routine daily thread:

- `zo-nexus-morning-brief`: daily, concise, delta-focused.

Use lower-frequency or manual jobs:

- `nexus-health-check`: weekly.
- `nexus-queue-runner`: weekly or manual until `tasks/pending` has official `.task.md` files.
- `zo-nexus-heartbeat`: paused; incident-only.
- `zo-nexus-pr-watcher`: paused; reactivate only during open PR windows.
- `nexus-whea-restart-monitor`: paused; reactivate only during hardware instability.

## Conversation-History Policy

If the automation platform creates one conversation per scheduled run, reduce scheduled runs rather than trying to archive after the fact. Archive old run threads only after the main agent has reviewed their memory files or summary output.

Future automation prompts should include:

- silent success on no-change runs,
- no broad history scans,
- no repeated old PR/check summaries,
- no screenshots or public-chat scraping unless explicitly requested,
- write one compact memory line only when a delta exists,
- stop after one-page output.

## 2026-05-24 Follow-Up

Checked local automation state at 2026-05-24 16:39 +03:00.

- `zo-nexus-morning-brief` remains active and produced the visible daily memory entry at 08:25/08:34.
- `zo-nexus-heartbeat` remains paused.
- `zo-nexus-pr-watcher` remains paused.
- `nexus-health-check` remains weekly Monday 06:08.
- `nexus-queue-runner` remains weekly Monday 06:12.
- No `.codex\automations` file changed in the last six-hour window checked.

Conclusion: the recent optimization appears to have stopped the hourly/two-hour repeater churn locally. Continue with one daily brief plus weekly local health/queue jobs unless a real incident or active PR window opens.

## 2026-05-25 Prompt Optimization

Reviewed the 2026-05-25 `nexus-health-check` and `nexus-queue-runner` outputs. Both behaved safely, but spent avoidable tokens by printing full canonical files, full `git status` output, and duplicated summaries.

Updated local automation definitions:

- `nexus-health-check`: weekly, active, low reasoning, current doctor surface only (`doctor memory` / `doctor version`), no full-file or full-status dumps, final output capped at 180 words.
- `nexus-queue-runner`: weekly, active, low reasoning, fast empty-queue path, no doctor/tests/broad scans when `tasks/pending/*.task.md` is empty, empty-run output capped at 90 words.
- `zo-nexus-morning-brief`: daily, active, low reasoning, delta-only with max 8 bullets and 220-word cap.
- `zo-nexus-heartbeat`: remains paused; if reactivated, no-delta output must be exactly one line.
- `zo-nexus-pr-watcher`: remains paused; if reactivated, no open PR/check delta must be exactly one line.

Operational rule added: automations may verify canonical files, but must not print full file contents. They should report counts, deltas, and blockers only.
