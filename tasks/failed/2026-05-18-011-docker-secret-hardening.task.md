---
id: 2026-05-18-011-docker-secret-hardening
title: Harden Docker container secrets and rotate exposed local Kafka credentials
priority: P0
status: failed
created: 2026-05-18
scope: docker-security
owner: Infrastructure Team Lead
secondary_approver: Security Lead
escalation: On-call security lead via Slack #security-incidents or PagerDuty security rotation
---

## Goal

Move NEXUS Docker runtime secrets out of inspectable container environment metadata and rotate credentials that were present in local Docker container configuration.

## Remediation Strategy

### Secret Migration

- Move secrets from inline environment variables in docker-compose files to a secrets management solution:
  - Option 1: Docker Secrets (requires swarm mode or compose v3.1+)
  - Option 2: External secrets store/vault (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
  - Option 3: Runtime-only `.env` files (excluded from version control, loaded at container start)
- Replace inline `KAFKA_API_KEY`, `KAFKA_API_SECRET`, and `POSTGRES_PASSWORD` with secret references
- Update docker-compose files to use `secrets:` blocks or `env_file:` with ignored `.env` files

### Network Exposure

- Redis (`redis-nexus`): Change port binding from `0.0.0.0:6379:6379` to `127.0.0.1:6379:6379`
- Postgres (`supabase_db_NEO_agent`): Change port binding from `0.0.0.0:54322:5432` to `127.0.0.1:54322:5432`
- Alternative: Apply Windows Firewall rules from Administrator PowerShell to block external access to ports 6379 and 54322

### Credential Rotation

1. Generate new Kafka API key/secret pair in Confluent Cloud
2. Update secrets store or `.env` with new credentials
3. Recreate `nexus-kafka-bridge` and `nexus-kafka-consumer` containers
4. Verify connectivity with new credentials
5. Revoke old Kafka API key/secret in Confluent Cloud
6. Generate new Postgres password for local Supabase instance
7. Update secrets store or `.env` with new password
8. Recreate `supabase_db_NEO_agent` container

### Access Controls

- Restrict Docker socket access to authorized users only
- Implement least-privilege IAM roles for secrets access
- Enable audit logging for secrets access
- Document who has access to production credentials

## Evidence From May 18 Check

- `nexus-kafka-bridge` failed when `supabase_db_NEO_agent` was stopped.
- Inspecting its container metadata showed raw Kafka and Postgres connection settings in Docker environment variables.
- The exact secret values are intentionally not copied into this task.
- Any operator or tool with Docker inspect access can read container environment variables.
- The Docker Compose source under `%USERPROFILE%\.docker\cagent\working_directories\docker-gordon-v7\<uuid>\default\docker-compose-kafka-bridge.yml` also contains raw Kafka credentials for the bridge/consumer/dashboard path. Do not copy those values into repo docs.
- Docker Desktop offline settings hardening removed the TCP `2375` listener after restart.
- Final netstat still showed remaining core ports `6379` and `54322` published on all interfaces by Docker.
- `redis-nexus` is created from `%USERPROFILE%\.docker\cagent\working_directories\docker-gordon-v7\<uuid>\default\docker-compose-redis.yml`, where Redis is published as all-interface `6379:6379`.
- `supabase_db_NEO_agent` has Docker `HostIp` blank for `54322:5432` and no Compose source labels in inspect output; identify its owning Supabase/Gordon creation source before recreating it.
- Attempting to add Windows Firewall block rules failed with `Access is denied`, including the approved command path, so port exposure still needs an Administrator PowerShell firewall rule or localhost-only container binding.

## Required Work

1. Identify where `nexus-kafka-bridge` and `nexus-kafka-consumer` are created.
2. Move the Gordon/Cagent Compose source out of raw inline secrets.
3. Replace raw environment secrets with one of:
   - Docker secrets.
   - Local ignored `.env` loaded only at runtime.
   - NEXUS Vault/secret lookup if available.
4. Rotate the Kafka API key/secret in Confluent Cloud if the exposed pair is still active.
5. Replace hardcoded local Postgres password assumptions with local-only config and documentation.
6. Change Redis from `6379:6379` to `127.0.0.1:6379:6379` and recreate `redis-nexus` only after confirming consumers use host-local access.
7. Identify the Supabase DB creation source, then change `54322:5432` to `127.0.0.1:54322:5432` or add a host firewall rule from an Administrator PowerShell session.
8. Scrub tracked docs, scripts, ignored local handoff files, and downloaded Gordon materials for copied credentials before any commit or handoff.
9. Add a safe verification command that confirms required variables are present without printing values.

## Verification Gate

**Current Status**: Not satisfied - secrets still exposed, ports still on 0.0.0.0, credentials not rotated

**Evidence Checklist**:
- [ ] `docker inspect nexus-kafka-bridge` no longer exposes raw production or cloud credentials
- [ ] `docker inspect nexus-kafka-consumer` no longer exposes raw production or cloud credentials
- [ ] Kafka bridge can still connect after secret migration
- [ ] Kafka consumer can still connect after secret migration
- [ ] No tracked file contains the old secret values
- [ ] Rotation evidence is recorded without revealing the new secret
- [ ] Old Kafka API key/secret has been revoked in Confluent Cloud
- [ ] `6379` is not exposed beyond localhost (verified with `netstat -an | findstr :6379`)
- [ ] `54322` is not exposed beyond localhost (verified with `netstat -an | findstr :54322`)
- [ ] Docker API TCP `2375` remains closed after future Docker Desktop restarts
- [ ] Secrets audit script passes all checks: `powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_secret_audit.ps1`

## Boundaries

- Do not paste secret values into reports, tasks, commits, or chat.
- Do not delete volumes or container images.
- Do not commit until leak scanning has passed.
- Do not use `git add .`.

## Queue Runner Result (2026-05-19)

- Verified the active bridge compose source is `%USERPROFILE%\.docker\cagent\working_directories\docker-gordon-v7\d9efce88-e41e-49fd-9b9d-6e79359e8bb4\default\docker-compose-kafka-bridge.yml`.
- Verified that file still contains inline `KAFKA_API_KEY`, `KAFKA_API_SECRET`, and `POSTGRES_PASSWORD` entries, and `docker inspect nexus-kafka-bridge` still exposes secret-backed environment keys.
- Verified `redis-nexus` still publishes `0.0.0.0:6379` and `supabase_db_NEO_agent` still publishes `0.0.0.0:54322`; the DB labels only identify project `NEO_agent`, not a writable repo-local creation source.
- Added `scripts/nexus_docker_secret_audit.ps1` and `docs/handoff/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` so the remaining hardening work can be rechecked without printing secret values.
- This queue run could not satisfy the verification gate because secret migration, credential rotation, and host-managed compose replacement remain outside the writable repo and were not completed here.
