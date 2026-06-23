# NEXUS Port Ownership Ruleset

Status: OBLIGATORY FOR ALL AGENTS
Updated: 2026-06-19

## Why Agents Collapsed On The Same Port

The root cause was stale mixed documentation. Older notes and some agent logs still treated `7352` as ModelRelay, while current runtime plans and code moved NEXUS Brain API / governance to `7352` and moved ModelRelay to `7350` and `7355`. Agents copied whichever snippet they saw first instead of verifying the live `PortRegistry`, `nexusctl dashboard --doctor`, and current startup scripts.

Hard conclusion: `7352` is no longer ambiguous. If a process on `7352` returns a static HTML app, ModelRelay response, proxy response, or `Cannot GET /health`, it is the wrong owner for that port.

## Reserved Local Ports

| Port | Owner | Role | Agent Rule |
|---:|---|---|---|
| `3001` | `next_dashboard` | Next.js dashboard UI | UI only; never backend or relay. |
| `7350` | `modelrelay_npm` | Node/npm ModelRelay primary | Primary `/v1/chat/completions` relay lane. |
| `7352` | `brain_api` | NEXUS Brain API / governance backend | Brain API only. Never ModelRelay, static dashboard, proxy, MCP, or experiment. |
| `7353` | `twave` | TWAVE wrapper | `/twave/*` only; wrapper remains bounded. |
| `7354` | `gross_bridge` | GROSS bridge | Read-only GROSS bridge surface only. |
| `7355` | `modelrelay_python` | Python ModelRelay fallback/internal | Fallback relay and internal health only. |
| `7356` | `static_dashboard` | Static HTML dashboard | Dashboard viewer only. |
| `7357` | `god_mode_proxy` | God Mode Proxy | Proxy lane only; never Brain API or ModelRelay. |
| `11434` | `ollama_default` | Local Ollama default | Default local Ollama only. |
| `11435` | `ollama_guard` | Guard-model Ollama lane | Guard models only. |
| `11436` | `nexusclaw_ollama_lane` | NexusClaw/NemoClaw Ollama lane | Claw lane only. |

## Non-Negotiable Rules

- Do not bind any new service to ports `7350` through `7357` unless it matches the table above.
- Do not use `7352` for ModelRelay, dashboards, static HTML, proxy experiments, MCP bridges, or browser sandboxes.
- Do not "temporarily" repurpose a reserved port. Use an ephemeral port above `20000` and document the owner if a throwaway test is required.
- Do not trust old logs, old markdown, or external AI chat claims for port ownership. Verify live code and `PortRegistry` first.
- If `7352` is occupied by the wrong owner, stop or relocate that process before starting Brain API. Do not adapt clients around the wrong owner.
- Agents must report port conflicts as blockers, not silently fall back to a stale port.

## Required Preflight Before Starting Services

Run at least one of these before service startup or dashboard routing changes:

```powershell
python -m pytest tests/bridge/test_port_registry.py -q
python -m nexus_os.cli.nexusctl dashboard --doctor --json
```

Expected ownership for the critical relay/backend split:

```text
7350 = modelrelay_npm
7352 = brain_api
7355 = modelrelay_python
```

## Startup Order

1. Start Node/npm ModelRelay primary on `7350`.
2. Start NEXUS Brain API on `7352` only after `7352` is free or already owned by Brain API.
3. Start static dashboard on `7356`.
4. Start Next.js dashboard on `3001` only when active development needs it.
5. Start optional proxy/bridge lanes (`7353`, `7354`, `7357`) only after their owners are confirmed.

## Adoption Gate

Any future agent plan, automation, or dashboard patch that mentions `7352 = ModelRelay` is stale and must be rejected before execution.
