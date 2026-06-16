---
id: NODE-MIG-NEXUS_DOCKER_SECRET_HARDENING_2026_05_19
authority_scope: experimental
origin_sha256: c8e5fa9eff415d7fe0adbd002c9a76cbccb76e7cee8a41783f17d498b362048d
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-A9936B
---
# NEXUS Docker Secret Hardening Follow-Up

Date: 2026-05-19
Scope: `nexus-kafka-bridge`, `nexus-kafka-consumer`, `redis-nexus`, and `supabase_db_NEO_agent`

## Verified Current State

- `nexus-kafka-bridge` is created from the host-managed compose file:
  `C:\Users\speci.000\.docker\cagent\working_directories\docker-gordon-v7\d9efce88-e41e-49fd-9b9d-6e79359e8bb4\default\docker-compose-kafka-bridge.yml`
- That compose file still stores `KAFKA_API_KEY`, `KAFKA_API_SECRET`, and `POSTGRES_PASSWORD` inline.
- `docker inspect nexus-kafka-bridge` still exposes those secret variable names through container environment metadata.
- `redis-nexus` still publishes `0.0.0.0:6379` and `[::]:6379`.
- `supabase_db_NEO_agent` still publishes `0.0.0.0:54322` and `[::]:54322`.
- `supabase_db_NEO_agent` labels identify the owning project as `NEO_agent`, but do not reveal a repo-local compose file that can be patched from this checkout.
- TCP `2375` remains closed.

## Repo-Local Operator Assets Added

- [`scripts/nexus_docker_profile.ps1`](/C:/Users/speci.000/Documents/NEXUS/scripts/nexus_docker_profile.ps1)
- [`scripts/nexus_docker_secret_audit.ps1`](/C:/Users/speci.000/Documents/NEXUS/scripts/nexus_docker_secret_audit.ps1)

Safe verification command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/nexus_docker_secret_audit.ps1
```

This command reports:
- the bridge compose source path
- whether inline secret keys are still present
- whether Redis is configured for localhost-only publish
- the current Redis and Supabase DB host bindings
- whether TCP `2375` is listening

It does not print secret values.

## Why The Task Did Not Fully Close

- The active Kafka bridge and Redis definitions live under `C:\Users\speci.000\.docker\cagent\working_directories\...`, outside this repo.
- Rotating the exposed Kafka credential pair requires access to the upstream Confluent Cloud credential owner.
- The verification gate requires `docker inspect nexus-kafka-bridge` to stop exposing raw secret-backed variables and requires `6379` / `54322` to stop publishing beyond localhost. Neither condition is satisfied yet.

## Remaining Operator Steps

1. Replace the inline bridge secrets in the host-managed compose with runtime-only `.env` loading, Docker secrets, or a vault-backed lookup.
2. Recreate `nexus-kafka-bridge` and `nexus-kafka-consumer` from the hardened source, then re-run the audit script.
3. Rotate the Kafka API key and secret that were previously present in the active compose/container definition.
4. Recreate `redis-nexus` with `127.0.0.1:6379:6379`.
5. Identify the writable creation source for project `NEO_agent`, then recreate `supabase_db_NEO_agent` with `127.0.0.1:54322:5432` or apply an elevated firewall rule in an Administrator PowerShell session.
