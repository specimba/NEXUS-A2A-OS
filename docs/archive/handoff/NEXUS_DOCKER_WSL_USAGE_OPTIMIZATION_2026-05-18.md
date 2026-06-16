---
id: NODE-MIG-NEXUS_DOCKER_WSL_USAGE_OPTIMIZATION_2026_05_18
authority_scope: experimental
origin_sha256: ed9a33d8c28803c6757bd314ab029d8c48abe76346e196a38c3930965584f7f4
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-60A510
---
# NEXUS Docker/WSL Usage And Optimization Handoff

Date: 2026-05-18
Host: SPECIMBAPC
Scope: Docker Desktop, WSL2, vmmemWSL, NEXUS local services, Supabase local stack, monitoring stack, and Docker Desktop extensions.

## Executive Verdict

The May 18 WSL memory pressure was Docker Desktop, not Ubuntu. The runtime optimization pass is now complete; the remaining open work is security hardening around exposed local ports and Docker-inspectable secrets.

Initial evidence:

- `wsl.exe -l -v` showed only `docker-desktop` running.
- `Ubuntu` was stopped.
- `vmmemWSL` was observed around 12.2-12.6 GB working set and about 13.0 GB private memory.
- Docker stats showed a Linux VM/container limit of 15.46 GiB.
- No `%UserProfile%\.wslconfig` file was present, so there was no explicit WSL memory cap or memory-reclaim policy owned by this operator profile.

Post-restart result:

- `%UserProfile%\.wslconfig` is active with an 8 GB WSL cap.
- Docker stats now show a 7.757 GiB container limit.
- The corrected NEXUS core runs with four containers: `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and `supabase_db_NEO_agent`.
- The core-only container footprint is about 113 MiB. CPU stayed low in verification, with a later transient Redis sample at 2.79 percent.
- `vmmemWSL` initially settled around 4.0 GB working set and about 5.2 GB private memory after Docker restart and core-profile enforcement, then reclaimed further to about 502 MB working set and 3.7 GB private memory.

This should not be treated as an unavoidable NEXUS cost. NEXUS should run the smallest verified local core needed for governed agent work, then enable heavier profiles only when a mission requires them.

## Actions Executed In First Pass

The first pass intentionally used reversible runtime pauses. No images, volumes, local models, archives, dumps, evidence files, browser tabs, OBS/Streamlabs, devin, or Docker Desktop itself were removed or stopped.

Stopped Docker Desktop extension containers:

- `openwebui-extension-service`
- `mindsdb_service`
- `pgvector_service`
- `signalonefrontend`
- `signaloneagent`
- `virag_redis-enterprise-docker-extension-desktop-extension-setup-1`
- `virag_redis-enterprise-docker-extension-desktop-extension-service`
- `kong_konnect-docker-extension-desktop-extension-service`
- `coder_embedded_dd_vm`
- `mochoa_coder-docker-extension-desktop-extension-coder-docker-extension-1`
- `grafana-docker-desktop-extension-alloy`
- `grafana_docker-desktop-extension-desktop-extension-grafana-docker-desktop-extension-1`
- `tailscale_docker-extension-desktop-extension-service`
- `saniewski_mongo-express-docker-extension-desktop-extension-service`
- `drewsk_docker-sql-extension-desktop-extension-service`
- `pgadmin4_embedded_dd_vm`
- `mochoa_pgadmin4-docker-extension-desktop-extension-pgadmin4-docker-extension-1`
- `portainer_portainer-docker-extension-desktop-extension-service`
- `openwebui-extension-mcp-gateway`
- `rw4lll_openwebui-docker-extension-desktop-extension-service`
- `ngrok_ngrok-docker-extension-desktop-extension-service`
- `ambassador_telepresence-docker-extension-desktop-extension-service`

Stopped optional observability containers:

- `redis-exporter`
- `grafana-monitoring`
- `cadvisor`
- `prometheus`
- `node-exporter`
- `autoops-otel-agent`

Stopped Supabase `NEO_agent` containers:

- `supabase_studio_NEO_agent`
- `supabase_pg_meta_NEO_agent`
- `supabase_edge_runtime_NEO_agent`
- `supabase_storage_NEO_agent`
- `supabase_rest_NEO_agent`
- `supabase_realtime_NEO_agent`
- `supabase_inbucket_NEO_agent`
- `supabase_auth_NEO_agent`
- `supabase_kong_NEO_agent`
- `supabase_analytics_NEO_agent`
- `supabase_db_NEO_agent`

Wrote `%UserProfile%\.wslconfig` for the next WSL/Docker restart:

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

This file was written only after verifying no existing `.wslconfig` was present earlier in the session.

## After First-Pass State

Remaining running containers after the final correction:

- `nexus-kafka-bridge` - about 13.6 MiB.
- `nexus-kafka-consumer` - about 10-18 MiB.
- `redis-nexus` - about 5-7 MiB.
- `supabase_db_NEO_agent` - about 75 MiB.

Final measured running container load:

- 4 running containers.
- About 105 MiB total container memory.
- Low CPU overall; the final post-restart sample showed only transient Redis activity above 0.5 percent.

WSL/Docker process state after pauses:

- `vmmemWSL` working set dropped from the earlier 12.2-12.6 GB range to about 1.9 GB after the core correction.
- `vmmemWSL` private memory dropped from around 13.0 GB to about 3.5 GB.
- This was the pre-restart residual state. After Docker/WSL restart, the 8 GB `.wslconfig` cap applied and Docker stats now report a 7.757 GiB limit.

## Second-Pass Hardening

Docker Desktop settings were backed up to:

- `%APPDATA%\Docker\settings-store.backup-20260518-074400.json`
- `%APPDATA%\Docker\settings-store.offline-backup-20260518-090605.json`

Docker Desktop settings were edited once to disable:

- `ExposeDockerAPIOnTCP2375`: `false`
- `EnableDockerAI`: `false`
- `EnableInference`: `false`
- `EnableInferenceTCP`: `false`
- `EnableInferenceGPUVariant`: `false`
- `InferenceCanUseGPUVariant`: `false`
- `DockerDebugDefaultEnabled`: `false`

The first online edit was reverted by Docker Desktop while it was running. A later offline edit was applied while Docker Desktop was stopped, then Docker Desktop and WSL were restarted.

Verified post-restart hardening:

- Docker Desktop engine returned healthy: client/server `29.4.1`.
- TCP `2375` is no longer listening.
- Docker AI, inference, inference TCP, inference GPU, and debug default are disabled in the settings file.
- `InferenceCanUseGPUVariant` was rewritten to `true`, but inference itself remains disabled. Treat that flag as inert unless Docker inference is re-enabled.

Remaining security gap:

- `6379` and `54322` are still published on all interfaces by Docker.
- Windows Firewall block attempts failed with `Access is denied`, including the approved command path, so this still needs an Administrator PowerShell session or container recreation with localhost-only binds.
- Docker Desktop restarted extension containers after restart; `scripts/nexus_docker_profile.ps1 -Mode core` was required to re-enforce core mode.

Added repo-local runtime controller:

- `scripts/nexus_docker_profile.ps1`

The corrected `core` profile is:

- `nexus-kafka-bridge`
- `nexus-kafka-consumer`
- `redis-nexus`
- `supabase_db_NEO_agent`

Reason: `nexus-kafka-bridge` depends on Postgres at `host.docker.internal:54322`; without `supabase_db_NEO_agent`, it restarts with a Postgres connection refusal.

Security follow-up:

- `nexus-kafka-bridge` container metadata contains raw connection secrets in environment variables.
- The Gordon/Cagent Compose source for the Kafka bridge path also contains raw credentials for bridge, consumer, and dashboard services.
- Do not paste those values into reports.
- Track remediation in `tasks/pending/2026-05-18-011-docker-secret-hardening.task.md`.

## Exact Live Usage Classes

### Required Or Likely NEXUS-Core While Local Queue/Bridge Work Is Active

These are clearly NEXUS-named and low cost:

- `nexus-kafka-bridge` - about 13.6 MiB.
- `nexus-kafka-consumer` - about 18.2 MiB.
- `redis-nexus` - about 7 MiB.

These are not the cause of the 12 GB WSL footprint.

### Optional NEXUS Observability

These are useful for observability, but costly enough to keep behind an explicit profile:

- `cadvisor` - observed between about 1.5 GiB memory and 7-30 percent CPU.
- `prometheus` - about 480 MiB; volume `default_prometheus-data` about 1.2 GB.
- `grafana-monitoring` - about 168-175 MiB.
- `node-exporter` - about 12 MiB.
- `redis-exporter` - about 12 MiB and currently unhealthy.
- `autoops-otel-agent` - about 88-97 MiB.

Recommendation: keep these off during streaming unless an active monitoring mission needs them.

### Supabase Local Project: `NEO_agent`

The Supabase stack is real and possibly useful, but should not run by default if the current mission is not testing Supabase flows:

- `supabase_db_NEO_agent`
- `supabase_studio_NEO_agent`
- `supabase_pg_meta_NEO_agent`
- `supabase_edge_runtime_NEO_agent`
- `supabase_storage_NEO_agent`
- `supabase_rest_NEO_agent`
- `supabase_realtime_NEO_agent`
- `supabase_inbucket_NEO_agent`
- `supabase_auth_NEO_agent`
- `supabase_kong_NEO_agent`
- `supabase_analytics_NEO_agent`

Observed memory concentration:

- Analytics around 592 MiB.
- Realtime around 297-299 MiB.
- Studio around 252 MiB.
- Storage around 163 MiB.
- DB around 160 MiB.

Recommendation: treat this as a `supabase-dev` profile, not baseline NEXUS.

### Docker Desktop Extensions And Tool Containers

These are the largest source of questionable background cost. They start with Docker and are mostly not tied to the tracked NEXUS repo:

- OpenWebUI extension: `openwebui-extension-service`, about 692 MiB, image virtual size about 6.7 GB, data volume about 1.1 GB.
- MindsDB extension: `mindsdb_service`, about 772 MiB, 168 PIDs.
- Redis Enterprise extension: about 1.16 GiB, around 9 percent CPU, more than 500 PIDs.
- pgAdmin extension: `pgadmin4_embedded_dd_vm`, about 279 MiB.
- Grafana Docker Desktop extension and Alloy sidecar.
- Coder Docker extension.
- Portainer extension.
- Tailscale extension.
- Mongo Express extension.
- SQL extension.
- SignalOne extension.
- Ngrok extension.
- Telepresence extension.
- Kong Konnect extension is in a restart loop.

Recommendation: remove or disable unused Docker Desktop extensions first. This is the cleanest reduction because it does not touch NEXUS source, browser tabs, OBS, devin, Docker Desktop itself, or drivers.

## Repo Dependency Check

Tracked Docker files in this checkout:

- `nexus_os/networking/tailscale/Dockerfile.tailscale`
- `nexus_os/networking/tailscale/docker-compose.tailscale.yml`

Untracked Docker compose found:

- `nexus-os-v2/docker-compose.yml`

That untracked compose defines `nexus-ollama`, `nexus-os`, and `nexus-trackio`, but none of those containers were running in the live Docker snapshot. Current running Docker cost is therefore not from the untracked `nexus-os-v2` compose.

## Docker Desktop Settings Findings

Current read-only settings snapshot from `%APPDATA%\Docker\settings-store.json` after offline hardening:

- `AutoStart`: false.
- `AutoPauseTimeoutSeconds`: 60.
- `KubernetesEnabled`: false.
- `ExposeDockerAPIOnTCP2375`: false.
- `EnableDockerAI`: false.
- `EnableInference`: false.
- `EnableInferenceTCP`: false.
- `EnableInferenceGPUVariant`: false.
- `InferenceCanUseGPUVariant`: true.
- `DockerDebugDefaultEnabled`: false.

Risk notes:

- Docker API on TCP 2375 is unnecessary unless a legacy tool explicitly requires it. It is now disabled and should stay closed after Docker Desktop restarts.
- Docker AI/inference TCP/GPU features are now disabled unless actively testing Docker Model Runner or Docker AI flows.
- Resource Saver is not enough on Windows/WSL because Docker's own docs say it reduces CPU on WSL but does not reduce Docker memory; WSL memory reclaim or a WSL cap is needed.

## Proposed WSL Profiles

Do not apply these while active Docker missions depend on current containers. Applying `.wslconfig` needs WSL/Docker restart.

### Streaming-Safe Profile

Use when OBS/Streamlabs, Chrome tabs, local agents, and Docker must coexist:

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

Prerequisite: stop optional Docker extensions, Supabase, and observability first. Current all-on workload is too close to 8 GB container memory plus overhead.

### NEXUS-Dev Profile

Use when Supabase and monitoring must run but streaming is also active:

```ini
[wsl2]
memory=10GB
processors=8
swap=4GB
vmIdleTimeout=60000

[experimental]
autoMemoryReclaim=gradual
sparseVhd=true
```

This is the safer first cap for the current machine state.

### Full-Lab Profile

Use only for heavy container experiments, builds, or local model service tests:

```ini
[wsl2]
memory=14GB
processors=12
swap=6GB
vmIdleTimeout=60000

[experimental]
autoMemoryReclaim=gradual
sparseVhd=true
```

This profile is not appropriate during full-load streaming.

## Recommended Action Order

1. Keep Docker running if a mission currently needs it, but do not accept all extensions as baseline.
2. After every Docker Desktop restart, run `scripts\nexus_docker_profile.ps1 -Mode core` unless the active mission needs another profile.
3. Split NEXUS Docker services into explicit profiles:
   - `core`: `redis-nexus`, `nexus-kafka-bridge`, `nexus-kafka-consumer`, `supabase_db_NEO_agent`.
   - `observability`: Prometheus, Grafana, cAdvisor, node-exporter, redis-exporter, OTel.
   - `supabase-dev`: all `NEO_agent` Supabase services.
   - `ai-tools`: OpenWebUI, MindsDB, pgVector.
4. Uninstall or disable unused Docker Desktop marketplace extensions if they keep auto-starting.
5. Fix `6379` and `54322` exposure with localhost-only bind configuration or elevated Windows Firewall rules.
6. Migrate `nexus-kafka-bridge` and `nexus-kafka-consumer` secrets out of inspectable Docker environment metadata and rotate exposed credentials.
7. Measure again after each profile change: `vmmemWSL`, Docker stats, WHEA deltas, OBS stability, and agent task latency.

## CLI Agent Task List

1. P0 secret migration and rotation:
   - Treat the Gordon/Cagent Kafka bridge Compose source as sensitive because it contains raw credentials in bridge, consumer, and dashboard service definitions.
   - Replace inline secrets with secret files or a NEXUS Vault lookup path that does not expose values through `docker inspect`.
   - Rotate the exposed cloud Kafka credential pair if it is still active.
   - Verify without printing values.
2. P0 port binding correction:
   - `redis-nexus` is created from `%USERPROFILE%\.docker\cagent\working_directories\docker-gordon-v7\...\default\docker-compose-redis.yml`; change Redis from all-interface `6379:6379` to localhost-only `127.0.0.1:6379:6379` when recreating that service.
   - `supabase_db_NEO_agent` currently publishes `54322:5432` with blank host IP and no Compose source label; identify its owning Supabase/Gordon creation source before recreating it, then bind to `127.0.0.1:54322:5432` or apply the firewall rule from an Administrator PowerShell session.
   - Verification target: no `0.0.0.0:6379`, `[::]:6379`, `0.0.0.0:54322`, or `[::]:54322` listeners.
3. P1 extension durability:
   - Docker Desktop marketplace extension containers auto-restarted after Desktop/WSL restart.
   - Until unused extensions are uninstalled or disabled, run `scripts\nexus_docker_profile.ps1 -Mode core` after Docker Desktop starts.
4. P1 diagnostic workflow update:
   - Keep `docs/handbook/03_NEXUSCTL_GUIDE.md` aligned with the Docker profile workflow, TCP `2375` check, Redis/Postgres binding checks, and report-only evidence rules.

## First-Pass Cuts That Should Be Safe After Mission Check

These do not appear required by tracked NEXUS source:

- Kong Konnect Docker extension, currently restarting.
- SignalOne Docker extension.
- Coder Docker extension.
- Mongo Express Docker extension.
- SQL Docker extension.
- Ngrok Docker extension.
- Telepresence Docker extension.
- Redis Enterprise Docker extension unless actively testing Redis Enterprise behavior.
- MindsDB Docker extension unless actively testing MindsDB.
- OpenWebUI Docker extension unless actively using OpenWebUI at port 8090 or MCP gateway at 8812.

Keep volumes until reviewed. Stop/remove containers before deleting volumes.

## Verification Commands For CLI Agents

```powershell
wsl.exe -l -v
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker stats --no-stream
docker system df -v
docker volume ls
Get-Process | Where-Object { $_.ProcessName -match 'vmmem|wsl|docker|com\.docker' }
netstat -ano
```

## Not Executed In This Pass

No Docker extension was uninstalled.
No Docker image or volume was deleted.
No elevated firewall rule was created; firewall attempts failed with `Access is denied`.
No secret rotation was performed.
No staging or commit was performed.

This file is the evidence-backed record for the controlled optimization pass and the remaining security hardening plan.
