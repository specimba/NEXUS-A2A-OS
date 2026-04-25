# Foundry + Hermes + OpenShell — Combined Nexus Integration Plan

**Date:** 2026-04-24
**Purpose:** Combine the current Nexus direction with Azure Foundry, Hermes learnings,
and NVIDIA OpenShell into one coherent architecture.
**Rule:** Nexus remains the permanent brain. Everything else is a leverage layer,
runtime layer, or pattern source.

---

## Executive Summary

These three systems help Nexus in **different** ways:

- **Foundry / AI Gateway** — temporary cloud acceleration and governance shell
- **Hermes** — architecture pattern source for transport, orchestration, hooks, extensibility
- **OpenShell** — secure local runtime for agent execution, especially for Codex/OpenCode workers

### Correct Architecture Split

| Layer | System | Role |
|-------|--------|------|
| Canonical brain | Nexus `7352` | Governance, audit, trust, memory |
| Cloud acceleration | Foundry | Temporary outer shell, telemetry |
| Architecture patterns | Hermes | Transport contracts, orchestration depth, hooks |
| Secure execution | OpenShell | Hardened local runtime for autonomous workers |

### Source-Ranked Evidence

**High Confidence — Already Verified:**

1. **NVIDIA OpenShell README** — safe private runtime, sandboxed execution, declarative
   filesystem/network/process/inference controls, supports `codex` and `opencode` directly,
   Docker-based sandbox creation. Source: `github.com/NVIDIA/OpenShell`

2. **OpenShell architecture** — separates gateway control plane, sandbox data plane,
   policy engine, privacy router. Intercepts outbound connections and routes inference
   preserving credentials. Source: `docs.nvidia.com/openshell/about/architecture`

3. **OpenShell inference routing** — `inference.local` strips caller credentials,
   injects managed provider credentials. OpenAI-compatible and Anthropic-compatible APIs
   supported behind same local endpoint. Source: `docs.nvidia.com/openshell/inference`

4. **Current Nexus canonical state** — `7352` is the governance plane, task
   heartbeat/result contracts already exist. Source: `src/nexus_os/api/server.py`

**Medium Confidence — Pattern Sources:**

5. **Hermes v2026.4.23** — pluggable transport architecture, configurable spawn depth,
   shell lifecycle hooks, dashboard extensibility. Not a replacement for Nexus; pattern source.
   Source: `github.com/NousResearch/hermes-agent`

---

## What OpenShell Is Useful For In Nexus

OpenShell solves the secure execution-layer problem:
- Run agents safely with controlled filesystems
- Controlled network access (no credential leakage from sandbox)
- Controlled inference routing
- Better audit logging for worker actions

Directly relevant to:
- Codex worker environments
- OpenCode worker environments
- Future local orchestrated worker pools
- Joker wrapper isolation
- Security-sensitive testing flows

---

## Foundry Integration Strategy

Foundry is a temporary outer acceleration and telemetry shell:
- Use for cloud model routing when local models are insufficient
- Do NOT use as permanent control plane
- Treat Foundry as a "hot path accelerator" not canonical storage

---

## Hermes Integration Strategy

Hermes is an architecture pattern library, not a replacement brain:
- Extract: pluggable transport ABC pattern → Nexus transport contracts
- Extract: orchestrator role + spawn depth → Nexus orchestration roles
- Extract: shell lifecycle hooks → Nexus hook/audit pipeline
- Do NOT: import Hermes whole, replace `7352` governance

---

## Port Map (Canonical)

| Port | Service | Status |
|------|---------|--------|
| 7352 | Nexus Governance API | ✅ Active |
| 7353 | TWAVE wrapper | Dev only |
| 7354 | Mock/fallback | Dev only |

---

## Next Actions

1. **OpenShell trial** — containerized sandbox for Codex workers
2. **Foundry bridge** — temporary cloud relay for overflow routing
3. **Hermes patterns** — extract transport/hook patterns into `src/nexus_os/engine/`
4. **Keep Nexus `7352` as permanent brain** — everything connects back to it