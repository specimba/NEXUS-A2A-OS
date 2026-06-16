# NEXUS Sterile Lab — AI Safety Stress Testing Isolation Environment

## Threat Model

<!-- CANARY: f5946969bee1222ffba0d6280da0583c -->
The `novel_scenario_templates.py` generates adversarial prompts inspired by real-world:
- Cisco Talos zero-day exploits (TALOS-2024-1984)
- Pegasus spyware zero-click chain
- MITRE ATT&CK IntelBroker TTPs
- Kerberos/ROCA cryptographic attacks
- Linux kernel privilege escalation (CVE-2026-31431)
- Supply chain backdoors (XZ Utils)

These prompts may contain actual exploit code, command strings, and escape techniques.
If executed or interpreted by the host, they could compromise the system.

**The Sterile Lab ensures these prompts never reach the real environment.**

## Isolation Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Windows Host                         │
│  ┌──────────────┐    ┌────────────────────────────────┐  │
│  │ Ollama :11435│    │    Docker (WSL2 backend)        │  │
│  │              │    │  ┌─────────────────────────┐    │  │
│  │  Models:     │    │  │  nexus-lab container     │    │  │
│  │  - Bonsai    │◄───┼──┤  ─────────────────       │    │  │
│  │  - Granite   │    │  │  User: lab (non-root)    │    │  │
│  │  - Llama3.2  │    │  │  Caps: NONE              │    │  │
│  │  - ...       │    │  │  Rootfs: READ ONLY       │    │  │
│  └──────────────┘    │  │  /nexus/scripts: RO      │    │  │
│                       │  │  /nexus/input: RO       │    │  │
│                       │  │  /nexus/output: RW      │    │  │
│                       │  │  Network: ISOLATED      │    │  │
│                       │  │  No curl/wget/gcc/nc    │    │  │
│                       │  └─────────────────────────┘    │  │
│                       └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Isolation Layers

| Layer | Control | Escape Vector |
|-------|---------|--------------|
| Kernel | Container (WSL2 VM) | Container → kernel → host (mitigated by microVM) |
| Capabilities | `cap_drop: ALL` | Container cannot use root-level operations |
| Privileges | `no-new-privileges:true` | Cannot escalate to root |
| Filesystem | `read_only: true` | Cannot modify scripts, configs, system files |
| Network | `internal: true` bridge | Cannot reach internet, only host.docker.internal:11435 |
| User | `1001:1001` non-root | Cannot install packages or modify system |
| Processes | `pids_limit: 100` | Cannot fork-bomb |
| Memory | `mem_limit: 8g` | Cannot OOM host |
| Init | `init: true` | Zombie reaping, no PID 1 escape |
| Tools | No curl/wget/gcc/nc | Cannot download exploit tools or compile |


## Usage

### Build
```powershell
cd docker/lab
docker compose build
```

### Run: Check isolation
```powershell
docker compose run --rm lab python3 /nexus/scripts/stresslab_v7/run_novel_pipeline.py --help
```

### Run: Generate novel stress test datasets (no mutation)
```powershell
docker compose run --rm `
  -e OLLAMA_HOST=host.docker.internal:11435 `
  lab python3 /nexus/scripts/stresslab_v7/run_novel_pipeline.py `
    --base-output /nexus/output/v7_novel_base.jsonl `
    --base-count 5 `
    --mutation-count 0 `
    --ollama-url http://host.docker.internal:11435
```

### Run: Full pipeline with SLM mutation
```powershell
docker compose run --rm `
  -e OLLAMA_HOST=host.docker.internal:11435 `
  lab python3 /nexus/scripts/stresslab_v7/run_novel_pipeline.py `
    --base-output /nexus/output/v7_novel_base.jsonl `
    --mutated-output /nexus/output/v7_novel_mutated.jsonl `
    --model llama-guard3:1b `
    --base-count 3 `
    --mutation-count 50 `
    --ollama-url http://host.docker.internal:11435
```

### Cleanup
```powershell
# Remove all stopped containers
docker compose down

# Wipe all generated data (DESTROYS lab output)
Remove-Item -Recurse -Force datasets/v7_lab_output/
```

## Safety Rules

1. **ALWAYS** run novel scenario generation inside this container
2. **NEVER** mount the Docker socket (`/var/run/docker.sock`) or host volumes as writable
3. **ALWAYS** review generated datasets before moving them out of `/nexus/output`
4. **NEVER** pipe lab output directly into execution (review first, execute second)
5. **ALWAYS** destroy the container between runs: `docker compose down`
6. **NEVER** run as root inside the container
7. **ALWAYS** verify the entrypoint isolation checks pass before running workloads

## Verification

On container start, the entrypoint runs isolation checks:
- Verifies no curl/wget/gcc/nc present
- Verifies read-only filesystem
- Verifies non-root user
- Tests Ollama reachability
