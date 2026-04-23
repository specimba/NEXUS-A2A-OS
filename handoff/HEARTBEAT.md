# HEARTBEAT.md — Cloud Orchestrator Active Initiative Protocol
**T+00: Boot & Sync**
Run `git pull origin main`.

**T+10: Deadlock Breaker & Task Generation**
Check `handoff/to_local/`. If it is empty, YOU MUST take initiative.
Generate the Phase 0 tasks and write them to the folder.

Create `handoff/to_local/task_001_run_nexus_scan.md` telling the Local Agent
to run `python scripts/nexus_scan.py` and output to `handoff/from_local/leak_report.json`.

Create `handoff/to_local/task_002_mini_arena.md` telling the Local Agent
to run 3 matches between local models and output to `handoff/from_local/arena_results.json`.

**T+20: Data Synthesis**
Read `handoff/from_local/`. If the Local Agent has posted JSON results
(leak reports, model arena data), read them and write a markdown summary
into the `docs/` folder (e.g., `docs/leak_triage_summary.md` or `docs/model_evaluations.md`).
Move the processed JSON files to an `archive/` folder so you don't process them twice.

**T+30: GVAW Handoff**
Run `git status`. If you created new tasks in `to_local/` or synthesized docs, run:
  git add handoff/ docs/
  git commit -m "orchestrator: deployed tasks and synthesized results"
  git push origin main

If absolutely no action was needed, log `[STANDBY]`.
Reply exactly with: HEARTBEAT_OK.