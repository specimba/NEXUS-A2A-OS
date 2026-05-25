# HEARTBEAT.md — Zo NEXUS Lane Guardian

**Version**: 4.0.0  
**Date**: 2026-05-25

---

## HEARTBEAT ROUTINE

Execute strictly in order. Terminate early if nothing needs attention.

### PHASE 1: Anomaly Check
1. `git status --short` — capture change state
2. If undocumented changes → log to `governance/foreman-log.md` + alert
3. If clean → proceed

### PHASE 1.5: EGGROLL Cycle-Check
1. `git diff --stat HEAD` — capture change volume
2. Count entries in `worklog.md` since last heartbeat
3. **If zero activity AND no pending tasks** → `HEARTBEAT_OK` → **early exit**
4. **If activity detected** → proceed to Phase 2
5. Record EGGROLL signal scores to `trust_ledger.jsonl`

### PHASE 2: State Check
1. Check `01_PROJECT_STATE.md` for active P0/P1 tasks
2. **If NO active tasks** → `HEARTBEAT_OK`
3. **If YES active tasks** → prioritize and act

### PHASE 3: Action
1. Handle highest-priority task
2. Record outcome to `self_learning_log.jsonl`
3. Output token savings summary

---

## ZO LANE AUTOMATIONS

Heartbeat triggered by Zo automations:
- `Zo-NEXUS-Daily-7am` — 07:00 +03 daily
- `Zo-NEXUS-PR-Watch` — every 6h
- `Zo-NEXUS-Nightly` — 22:00 +03 daily

No manual cron needed — Zo manages the schedule.

---

## OPENCLAW GATEWAY HEALTH

Check gateway on every heartbeat:
```bash
curl -s http://127.0.0.1:18789/health
```
Expected: `{"ok":true,"status":"live"}`

If not live → restart via Zo service management.

---

## EGGROLL SIGNAL CHECK

| Signal | Command | Threshold |
|--------|---------|-----------|
| Code churn | `git diff --stat HEAD` | >5 files → active |
| Worklog growth | `wc -l worklog.md` delta | >0 new → active |
| Trust ledger | `trust_ledger.jsonl` recent | EGGROLL scores tracked |

EGGROLL Score: Safety 45%, Accuracy 30%, Compliance 25%.

---

## STANDBY / DREAM INTEGRATION

If **HOMEOSTASIS** detected:
1. Enter STANDBY — Zo-NEXUS idles, HERMES Curator monitors
2. HERMES Curator watches: SPECI commands, cron events, sub-agent completions, anomalies
3. Wake on: SPECI command → immediate | cron → run scheduled job | sub-agent → collect result | anomaly → triage
4. Log standby entry to `MEMORY.md` Dream Mode Log

---

**Status**: ACTIVE  
**Owner**: Zo-NEXUS (Zo Computer + OpenClaw Gateway)