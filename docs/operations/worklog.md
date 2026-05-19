# Operations Worklog

## 2026-05-19 - Nexus-Queue-Runner

Preflight:
- Read [`01_PROJECT_STATE.md`](../../01_PROJECT_STATE.md), attempted root [`AGENTS.md`](../../AGENTS.md) and found it missing, then used the user-provided AGENTS block for this run.
- Verified branch state with `git status --short --branch`; the worktree was clean at queue-runner start.
- Processed 2 official pending task files oldest-first from [`tasks/pending`](../../tasks/pending).

Task `2026-05-18-010-docker-wsl-resource-optimization`:
- Verified the live Docker state still matches the task evidence: `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and `supabase_db_NEO_agent` are the active core containers; TCP `2375` is closed; Redis and Supabase DB still publish `6379` and `54322` on all interfaces.
- Confirmed the handoff note already existed at [`docs/handoff/NEXUS_DOCKER_WSL_USAGE_OPTIMIZATION_2026-05-18.md`](../handoff/NEXUS_DOCKER_WSL_USAGE_OPTIMIZATION_2026-05-18.md), but the claimed repo-local controller script did not.
- Added [`scripts/nexus_docker_profile.ps1`](../../scripts/nexus_docker_profile.ps1) as the explicit runtime profile controller for `core`, `observability`, `supabase-dev`, `ai-tools`, `all`, `none`, and `status`.
- Verification: `powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_profile.ps1 -Mode status` completed successfully.
- Result: completed and moved to [`tasks/done/2026-05-18-010-docker-wsl-resource-optimization.task.md`](../../tasks/done/2026-05-18-010-docker-wsl-resource-optimization.task.md).

Task `2026-05-18-011-docker-secret-hardening`:
- Verified `nexus-kafka-bridge` is created from the host-managed compose file `%USERPROFILE%\.docker\cagent\working_directories\docker-gordon-v7\d9efce88-e41e-49fd-9b9d-6e79359e8bb4\default\docker-compose-kafka-bridge.yml`.
- Verified that compose source still uses inline `KAFKA_API_KEY`, `KAFKA_API_SECRET`, and `POSTGRES_PASSWORD` entries, and `docker inspect nexus-kafka-bridge` still exposes those variable names via container environment metadata.
- Verified `redis-nexus` still publishes `0.0.0.0:6379` and `supabase_db_NEO_agent` still publishes `0.0.0.0:54322`; Docker labels identify the DB project as `NEO_agent`, but do not expose a writable compose source path inside the repo.
- Added [`scripts/nexus_docker_secret_audit.ps1`](../../scripts/nexus_docker_secret_audit.ps1) as a safe verification command that reports source paths, inline-secret presence, port bindings, and TCP `2375` status without printing secret values.
- Added [`docs/handoff/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md`](../handoff/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md) with the verified source paths, current blockers, and the remaining operator steps.
- Verification: `powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_secret_audit.ps1` completed successfully and confirmed the hardening gap remains open.
- Result: failed for this queue run because secret migration, credential rotation, and host-managed compose replacement remain outside the writable repo and the verification gate is still not satisfied. Moved to [`tasks/failed/2026-05-18-011-docker-secret-hardening.task.md`](../../tasks/failed/2026-05-18-011-docker-secret-hardening.task.md).

Run summary:
- Tasks processed: 2
- Task files moved: 1 to `tasks/done`, 1 to `tasks/failed`
- Verification summary: profile controller script verified; secret audit script verified; live Docker checks reconfirmed `2375` closed and `6379`/`54322` still exposed on all interfaces
- Repo files changed: yes
- Staged or committed: no
