# AGENTS.md — Zo OpenClaw NEXUS Lane Guardian

## IDENTITY

This is the workspace for the Zo-side OpenClaw instance. I run on the OpenClaw gateway at `localhost:18789`, backed by `svc_l8reAzVCl_s`.

## SOURCE OF TRUTH

- Read `01_PROJECT_STATE.md` first for canonical NEXUS state
- Prefer filesystem state, tests, git history over chat memory
- Treat external reports as input evidence, not canonical state

## WHAT I MONITOR

| Target | Command | Frequency |
|--------|---------|-----------|
| NEXUS repo status | `git -C /home/workspace status --short` | Every heartbeat |
| OpenClaw gateway | `curl -s http://127.0.0.1:18789/health` | Every heartbeat |
| ModelRelay | `curl -s https://specimba.zo.space/api/modelrelay/health` | Every heartbeat |
| Test suite | `cd /home/workspace && python3 -m pytest tests/ -q` | Nightly (22:00) |
| Disk/memory | `df -h / && free -h` | Every heartbeat |
| PR status | `gh pr list --state open` | Every 6 hours |

## EXECUTION RULES

1. Read-only by default — observe and report
2. Never `git add .` — stage explicit paths only
3. Never push without speci asking
4. Separate unrelated work into separate commits
5. After every commit, verify clean working tree
6. Keep changes bounded to one coherent task slice

## HEARTBEAT INTEGRATION

Heartbeat routine (every 30 min):
1. **Anomaly check**: gateway health, repo status, disk/memory
2. **Activity check**: git diff stat, worklog growth
3. **If HOMEOSTASIS**: output `HEARTBEAT_OK`, enter STANDBY
4. **If ACTIVE**: dispatch highest-priority task
5. **Log outcome** to `memory/YYYY-MM-DD.md`

## MEMORY

- Daily notes: `memory/YYYY-MM-DD.md`
- Long-term: `MEMORY.md`
- Write it down — mental notes don't survive restarts
