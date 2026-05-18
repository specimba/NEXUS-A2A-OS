# NEXUSCTL Guide

## Canonical command

Run cycle validation from the repo root:

```powershell
python -m nexusctl cycle-check
```

Additional tracked entrypoints now resolve from repo root:

```powershell
python -m nexusctl doctor --report-only
python -m nexusctl status
python -m nexusctl handoff --output handoff.json
```

## Current tracked behavior

- `cycle-check` reads `.nexus_pi/state/session_compact.json` when present and reports the latest recorded cycle snapshot.
- If `.nexus_pi/state/halt_report.json` exists, `cycle-check` reports a halted state and returns a nonzero exit code.
- If neither file exists, `cycle-check` returns an explicit `unavailable` result instead of failing with an import error.
- `doctor --report-only`, `status`, and `handoff` currently return intentional `unavailable` payloads instead of fake health counts or synthetic status claims.
- Protected workloads for workstation diagnostics remain off-limits by default: browser tabs, OBS/Streamlabs, devin, Docker, and active agent shells.

## Workflow decision

- `nexusctl doctor` remains report-only and does not absorb workstation emergency actions by default.
- Crash, WHEA, startup, and vendor-agent investigations stay on a separate workstation/emergency track until a dedicated command exists.
- If a diagnostic command cannot produce live evidence, it must emit the exact failure mode and direct-check evidence instead of stale counts.
- If `doctor --report-only` cannot run because of packaging drift, use direct evidence checks and label old doctor counts as fallback-only.
- Do not collapse repo-health, queue-runner, Docker/WSL, and crash investigations into one implied health claim. Each report must state its scope boundary.

## Doctor feature base

The current base is intentionally honest:

- `cycle-check` has a real report path through `.nexus_pi/state/session_compact.json` and `.nexus_pi/state/halt_report.json`.
- `doctor --report-only`, `status`, and `handoff` may return `unavailable` rather than synthetic success.
- Direct PowerShell evidence collection is an accepted fallback when `nexusctl` packaging is unavailable.
- Severe doctor findings should be reported as codes plus evidence, not normalized into a vague "system unhealthy" label.

When extending `nexusctl doctor`, keep these modes separate:

1. `repo`: canonical docs, git status, queue inventory, stale state, package/import sanity, focused tests.
2. `runtime`: Docker/WSL profile, exposed ports, container memory, local service health.
3. `workstation`: process pressure, protected workloads, startup/service inventory.
4. `emergency`: reboot, WHEA, dump, CrashControl, power plan, firmware/driver evidence.

Every mode should support `--report-only` first. Fix commands may be added later, but they must be explicit and reversible.

Minimum report fields:

- Timestamp, host, branch/HEAD when repo-scoped, and exact scope.
- Evidence folder or command transcript path.
- Freshness: fresh, fallback-only, blocked, or not checked.
- Finding counts by severity plus key codes.
- Protected surfaces preserved.
- Mutations performed, if any.
- Blocked checks with exact error text.
- Next gate and acceptance criteria.

Never report:

- Fresh doctor counts copied from older reports.
- Synthetic pass/fail status when the command could not inspect the target.
- Conversation-backlog coverage from a queue-only run.
- Secret values, local model inventories, or dump contents in tracked docs.

## Emergency restart diagnostics

Use this path when there is a sudden reboot, hard hang, Kernel-Power `41`, EventLog `6008`, WHEA, BSOD, or suspected driver/firmware instability.

Default evidence folder:

```powershell
.nexus_diagnostics\restart-investigation\<yyyyMMdd-HHmmss>
```

Use a repo-local fallback if `C:\tmp` is denied. Record that denial under `admin-blocked`.

Required first pass:

1. Export broad System and Application slices for the incident window.
2. Export focused slices around the suspected reboot window.
3. Export full XML for:
   - WHEA-Logger `17`, `19`, `2`
   - Kernel-Power `41`
   - EventLog `6008`
   - User32 `1074`
   - WindowsUpdateClient `19`
4. Save count tables for the last 10-21 days and a post-repair WHEA delta.
5. Record power state:
   - `powercfg /getactivescheme`
   - `powercfg /query SCHEME_CURRENT SUB_PCIEXPRESS ASPM`
   - `powercfg /a`
6. Record safe registry fallbacks:
   - `HKLM:\HARDWARE\DESCRIPTION\System\BIOS`
   - `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion`
   - `HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl`
   - `HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management`
7. Inventory dumps without copying or taking ownership:
   - `C:\Windows\Minidump`
   - `C:\Windows\MEMORY.DMP`
   - `C:\Windows\LiveKernelReports`
8. Snapshot protected workload pressure without stopping anything:
   - browsers
   - OBS/Streamlabs
   - devin
   - Docker/vmmemWSL
   - Codex, ERNIE, zo, opencode, node workers

Successful method from the May 18 run:

- Rank suspects from evidence before proposing any fix.
- Treat WHEA 17 on `PCI\VEN_10DE&DEV_2860...` as NVIDIA/PCIe evidence, not proof by itself.
- Treat WHEA 19 CPU internal parity near a reboot as CPU/power/thermal evidence.
- Treat Devin/tool shell failures as workflow-hygiene evidence unless Windows logs tie them directly to the reboot.
- Treat OBS/Streamlabs memory pressure as a separate class unless it aligns with reboot time.
- Use `powercfg` to confirm PCIe ASPM state; ASPM Off was the bounded prior repair.
- Use CDB/WinDbg only as report-only dump analysis. If dump access is denied, record `Access is denied` and prepare an Administrator script; do not take ownership automatically.
- Create a WHEA delta monitor for 24-48 hours after the last repair or reboot.

Current artifact pattern:

```text
events/
  system-*.csv
  application-*.csv
  *fullxml.xml
  whea-counts-*.csv
system/
  powercfg-*.txt
  bios-registry.txt
  windows-version-registry.txt
  crashcontrol-registry.txt
  pagefile-registry.txt
  minidump-inventory.csv
  driverstore-*.csv
  protected-workload-process-snapshot.csv
admin-blocked/
  <exact blocked check>.txt
NEXUS_DEEP_RESTART_INVESTIGATION_REPORT.md
suspect-matrix.csv
admin_evidence_commands.ps1
monitor_whea_delta.ps1
```

Acceptance criteria for an emergency report:

- It separates proven facts, likely suspects, weak suspects, and blocked checks.
- It includes a timeline with absolute timestamps.
- It includes post-repair or post-reboot WHEA delta status.
- It includes driver/update evidence before recommending OEM changes.
- It names the next gate without performing driver, firmware, dump-permission, or process-killing changes.

## Docker and WSL diagnostics

Use this workflow when `vmmemWSL`, Docker Desktop, or Linux containers are suspected of consuming workstation resources:

1. Run `wsl.exe -l -v` first. Distinguish `docker-desktop` from real user Linux distributions.
2. Run `docker ps`, `docker stats --no-stream`, `docker system df -v`, and `docker volume ls` when Docker access is available.
3. Classify containers before stopping anything:
   - `core`: NEXUS runtime pieces such as Redis, Kafka bridge, or Kafka consumer.
   - `observability`: Prometheus, Grafana, cAdvisor, exporters, OTel.
   - `supabase-dev`: local Supabase stack.
   - `ai-tools`: OpenWebUI, MindsDB, pgVector, model gateway tools.
   - `docker-extensions`: Docker Desktop marketplace/helper extensions.
4. Check `%UserProfile%\.wslconfig`; if absent, record that WSL has no operator-owned memory cap.
5. Check `%APPDATA%\Docker\settings-store.json` for high-risk or high-cost settings such as TCP 2375, Docker AI, inference TCP, and GPU inference.
6. Prefer profile-based reduction over broad shutdown:
   - Keep `core` small and always explicit: `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and `supabase_db_NEO_agent`.
   - Run `observability`, `supabase-dev`, and `ai-tools` only when the current mission needs them.
   - Remove unused Docker Desktop extensions before blaming NEXUS core services.
7. Do not delete Docker volumes before review. Stop/remove containers first, preserve data, then prune only with a rollback plan.

Use `scripts/nexus_docker_profile.ps1` to switch local Docker runtime modes. Default to `-Mode status` first, then use `-Mode core`, `-Mode supabase-dev`, `-Mode observability`, `-Mode ai-tools`, or `-Mode lab` only when the mission requires that layer.

After Docker Desktop or WSL restarts, re-run `scripts\nexus_docker_profile.ps1 -Mode core` unless the active mission intentionally needs a heavier profile. Docker Desktop marketplace extensions may restart automatically and should not become baseline NEXUS runtime by accident.

For workstation security checks, verify TCP `2375`, Redis `6379`, and Postgres `54322` explicitly. TCP `2375` should stay closed. Redis and Postgres should be bound to localhost or protected by a reviewed firewall rule; if elevated firewall changes fail, record the exact failure and leave a follow-up task instead of silently accepting all-interface exposure.

## Verification

Focused smoke coverage:

```powershell
python -m pytest tests/cli/test_nexusctl_cycle_check.py -q -p no:cacheprovider
```
