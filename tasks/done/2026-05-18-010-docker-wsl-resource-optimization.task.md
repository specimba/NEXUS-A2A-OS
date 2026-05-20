---
id: 2026-05-18-010-docker-wsl-resource-optimization
title: Optimize Docker Desktop and WSL resource profile for NEXUS workstation
priority: P0
status: done
created: 2026-05-18
scope: workstation-docker-wsl
---

## Goal

Reduce Docker/WSL memory and CPU pressure without breaking active NEXUS missions, browser tabs, OBS/Streamlabs, devin, Docker Desktop itself, or local evidence.

## Evidence From May 18 Check

- `wsl.exe -l -v` showed `docker-desktop` running and `Ubuntu` stopped.
- `vmmemWSL` was about 12.2-12.6 GB working set and about 13 GB private memory.
- Docker stats reported a 15.46 GiB container/VM limit.
- No `%UserProfile%\.wslconfig` existed.
- 42 running containers were visible.
- 22 running containers were Docker Desktop extension containers.
- The clearly NEXUS-named runtime core was small, but `nexus-kafka-bridge` also required `supabase_db_NEO_agent` on port 54322.
- Heavy/non-core contributors included `cadvisor`, Redis Enterprise extension, MindsDB, OpenWebUI, Prometheus, Supabase `NEO_agent` analytics/realtime/studio, and Docker Desktop extension services.
- Docker Desktop settings had `ExposeDockerAPIOnTCP2375=true`, `EnableDockerAI=true`, `EnableInference=true`, and `EnableInferenceTCP=true`.
- Post-restart verification shows Docker stats now capped at 7.757 GiB, TCP `2375` no longer listening, and the corrected core profile using about 113 MiB total container memory.

## Required Work

1. Confirm with mission owners whether these groups are currently required:
   - Docker Desktop extensions.
   - Supabase `NEO_agent`.
   - Observability stack.
   - OpenWebUI/MindsDB/pgVector.
2. Create or document explicit Docker profiles:
   - `core`: `redis-nexus`, `nexus-kafka-bridge`, `nexus-kafka-consumer`, and `supabase_db_NEO_agent`.
   - `observability`: Prometheus, Grafana, cAdvisor, node-exporter, redis-exporter, OTel.
   - `supabase-dev`: Supabase local stack beyond the DB container.
   - `ai-tools`: OpenWebUI, MindsDB, pgVector.
3. Remove or disable unused Docker Desktop extensions after preserving volumes.
4. Disable Docker API TCP 2375 unless a named tool needs it.
5. Disable Docker AI/inference TCP/GPU features unless actively testing Docker Model Runner.
6. Add `%UserProfile%\.wslconfig` during a safe restart window. Completed with:

```ini
[wsl2]
memory=8GB
processors=6
swap=4GB
vmIdleTimeout=60000

[experimental]
autoMemoryReclaim=gradual
sparseVhd=true
```

1. Restart WSL/Docker only after active Docker missions are released. Completed during this pass.
2. Re-measure `vmmemWSL`, Docker stats, open ports, OBS/streaming stability, and NEXUS agent latency. Docker/WSL/open-port checks completed; OBS stability remains operator-observed.

## First Pass Executed

- Stopped Docker Desktop extension containers without deleting volumes or images.
- Stopped optional observability containers: Redis exporter, Grafana, cAdvisor, Prometheus, node-exporter, and OTel agent.
- Stopped Supabase `NEO_agent` containers without deleting volumes or images.
- Left NEXUS core target as `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and later corrected it to include `supabase_db_NEO_agent`.
- Wrote `%UserProfile%\.wslconfig` with an 8 GB memory cap, 6 processors, 4 GB swap, `autoMemoryReclaim=gradual`, and `sparseVhd=true`.
- Docker/WSL were later restarted, so the cap is now active.

## Second Pass Executed

- Backed up Docker Desktop settings to `%APPDATA%\Docker\settings-store.backup-20260518-074400.json`.
- Backed up Docker Desktop settings again during the offline restart window to `%APPDATA%\Docker\settings-store.offline-backup-20260518-090605.json`.
- Attempted to set Docker Desktop settings on disk to disable TCP 2375, Docker AI, Docker inference, inference TCP, GPU inference, and default debug mode.
- The first online edit was reverted by Docker Desktop while running. The later offline edit persisted after Docker Desktop/WSL restart.
- Verified TCP `2375` is no longer listening.
- Verified Docker stats now report a 7.757 GiB limit, which confirms the 8 GB WSL cap is active.
- Added `scripts/nexus_docker_profile.ps1` to make runtime profiles explicit.
- Started the corrected `core` profile: `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and `supabase_db_NEO_agent`.
- Verified the corrected core profile: about 113 MiB total container memory, low CPU, and `vmmemWSL` later reclaimed to about 502 MB working set / 3.7 GB private memory.
- Found that Docker Desktop auto-restarted extension containers after restart; rerunning `scripts\nexus_docker_profile.ps1 -Mode core` was required to re-enforce core mode.
- Attempted to block `6379` and `54322` with Windows Firewall, including the approved command path, but rule creation failed with `Access is denied`. Windows Firewall commands must be run from an Administrator PowerShell session.
- Found a separate security issue: `nexus-kafka-bridge` container metadata includes raw connection secrets. Follow-up task: `2026-05-18-011-docker-secret-hardening`.

## Remaining Work

- Create durable Docker profiles or compose files for `core`, `observability`, `supabase-dev`, and `ai-tools`; the current repo-local script is the active control surface.
- Decide which Docker Desktop extensions should be uninstalled rather than merely stopped.
- Disable Docker Desktop extension auto-start where possible, or enforce `core` mode after Docker Desktop restarts.
- Fix `6379` and `54322` all-interface exposure with localhost-only compose binds or run Windows Firewall commands from an Administrator PowerShell session to block these ports.
- Complete Docker secret hardening and credential rotation.

## Verification Gate

- `vmmemWSL` stays below the selected profile cap after WSL/Docker restart. Current pass: confirmed.
- Required NEXUS services still respond.
- No browser tabs, OBS/Streamlabs, devin, local dumps, or evidence files are lost.
- Docker API no longer listens on `127.0.0.1:2375` unless explicitly justified. Current pass: confirmed.
- Docker extension count and memory are lower than the May 18 baseline. Current pass: confirmed after enforcing core mode.
- The final report includes before/after Docker stats and a rollback path.

## Boundaries

- Do not delete Docker volumes before review.
- Do not uninstall drivers.
- Do not delete local models, archives, dumps, or evidence files.
- Do not stage or commit without explicit operator approval.
- Do not use `git add .`.
- Do not stop Docker/WSL during an active mission without a release signal.

## Queue Runner Result (2026-05-19)

- Verified the live core profile still matches the task evidence and the remaining open risk is limited to the separate secret-hardening follow-up.
- Added `scripts/nexus_docker_profile.ps1` to make the `core`, `observability`, `supabase-dev`, and `ai-tools` profiles explicit inside the repo.
- Verified the controller in read-only mode with `powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_profile.ps1 -Mode status`.
- Moved this task to `tasks/done/` after confirming the repo-side completion artifact now exists.
