# HEARTBEAT.md — Zo OpenClaw NEXUS Lane Guardian

Execute strictly in order. Terminate early if nothing needs attention.

---

### PHASE 1: Gateway + Service Health
1. `curl -s http://127.0.0.1:18789/health` — OpenClaw gateway
2. `curl -s https://specimba.zo.space/api/modelrelay/health` — ModelRelay
3. Check disk: `df -h / | tail -1`
4. Check memory: `free -h | grep Mem`
5. If any service down → alert immediately, skip to ACTION

### PHASE 2: NEXUS Repo Health
1. `git -C /home/workspace status --short` — undocumented changes?
2. `git -C /home/workspace log --oneline -3` — recent commits
3. `gh pr list --state open --limit 5` — open PRs
4. If clean → proceed to Phase 3

### PHASE 3: Activity Check
1. `git -C /home/workspace diff --stat HEAD` — change volume
2. Count worklog entries since last heartbeat
3. **If zero activity AND no pending tasks** → `HEARTBEAT_OK` → early exit
4. **If activity** → proceed to PHASE 4

### PHASE 4: State + Action
1. Check `01_PROJECT_STATE.md` for active P0/P1 tasks
2. Handle highest priority task
3. Record outcome to `memory/YYYY-MM-DD.md`

---

## STANDBY INTEGRATION

If HOMEOSTASIS detected in Phase 3:
1. Enter STANDBY mode
2. HERMES monitors inbound signals
3. Wake on: speci command, cron event, anomaly
4. Log standby entry to `memory/YYYY-MM-DD.md`
