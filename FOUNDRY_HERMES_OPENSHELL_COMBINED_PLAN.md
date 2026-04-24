# FOUNDRY / HERMES / OPENSHELL — Combined Integration Plan
**Canonical version — Zo workspace** | Updated: 2026-04-24

---

## Layer Architecture (locked)

```
OUTER (temporary leverage)
  Azure Foundry + AI Gateway
  - OSMANclaw4Kimi  → canonical ID: joker_opus
  - grok420osmanclaw → canonical ID: joker_grok
  - governance-security-orchestrator → canonical ID: governance_orchestrator
  - Purpose: telemetry, quota, rate limits, future MCP/A2A governance
  - Duration: while free tier useful; extract patterns, move capabilities back to Nexus

MIDDLE (permanent canonical brain)
  Nexus OS 7352
  - /tasks/heartbeat, /tasks/result, /tasks/status
  - /skills/propose, /skills/status/{id}
  - /audit/events, /dashboard/stats
  - Purpose: task ledger, VAP audit chain, trust scoring, GSPP proposal flow
  - Duration: permanent

FOUNDATION (secure local runtime)
  OpenShell (NVIDIA) + local Docker
  - Codex sandbox  → policy-banded execution
  - OpenCode sandbox → inference.local credential hiding
  - Purpose: bounded testing, credential isolation, structured logs
  - Duration: trial now, keep if proven

CORE ARCHITECTURE PATTERN (source)
  Hermes v2026.4.23 (NousResearch)
  - transport abstraction, spawn-depth policy, lifecycle hooks
  - Purpose: architecture reference only — do NOT import as runtime
```

---

## Phase 1: Stabilize Internal Truth (NOW)

- [x] 622 tests passing on `canonical-617`
- [x] 7352 task heartbeat/result contract deployed
- [x] `agent_registry.yaml` canonical IDs locked
- [x] Task ledger + FINALIZER_PROMPT v3.2 active
- [x] Pre-commit + PUBLIC_SHARE_ALLOWLIST governance

## Phase 2: OpenShell Trial (THIS WEEK)

```
Docker containers:
  - openshell-codex-sandbox    → policy-banded Codex execution
  - openshell-opencode-sandbox → inference.local route
  - openshell-test-lane        → bounded benchmark runner

Each container:
  - reports to Nexus 7352 via /tasks/heartbeat
  - emits VAP audit events
  - no credential exposure to worker runtime
```

## Phase 3: Foundry AI Gateway (AFTER OpenShell stable)

- Enable AI Gateway on `speci-mo47yezh-eastus2`
- Map existing Foundry agents → canonical IDs in `foundry_agent_inventory.md`
- Route Foundry model/tool traffic through gateway quotas
- Use Portal Traces/Monitor as secondary telemetry (not primary)

## Phase 4: Hermes Pattern Extraction

From `HERMES_V2026_4_23_NEXUS_ADAPTATION.md`:

```
Useful patterns to steal:
  - HermesTransportRegistry → NexusTransportRegistry (future)
  - spawn-depth policy → Swarm worker depth limits
  - lifecycle hooks → Vault + Governor lifecycle events
  - explicit orchestrator role → Foreman/Coordinator separation

NOT borrowed as runtime:
  - hermes-agent itself
  - mem0 integration
  - direct NousResearch dependencies
```

## Phase 5: GLM5 / GLM5.1 Fusion (Dashboard)

Per `GLM_FUSION_INTAKE_CHECKLIST.md`:

```
Keep both alive in parallel.
Force both against same 7352 contract.
Extract best pieces:
  - Overview/Tasks     ← whichever stronger
  - Governance/Trust  ← whichever stronger
  - Agent visibility  ← whichever stronger
  - Mobile/UX         ← whichever stronger
Fuse incrementally — no big-bang merge.
```

## Phase 6: Foundry → Nexus Capability Extraction

When Foundry free tier ends or pattern is成熟:

```
1. Document every governance/audit pattern used in Foundry
2. Translate to Nexus-native implementation
3. Migrate agent instruction templates to Nexus AGENT.md files
4. Keep Foundry as optional external node, not required dependency
```

---

## Shared State (source of truth)

| File | Purpose |
|------|---------|
| `agent_registry.yaml` | Canonical IDs for all agents |
| `foundry_agent_inventory.md` | Foundry portal ↔ Nexus ID mapping |
| `tasks/coordination_prompt.md` | Team coordination law |
| `docs/agents/AGENT_*.md` | Per-agent rules and boundaries |
| `src/nexus_os/` | 68-module canonical Python codebase |
| `skills/nexus-os/` | NEXUS OS v3.0 Zo skill package |
| `FOUNDRY_HERMES_OPENSHELL_COMBINED_PLAN.md` | This file |

---

## Rollback Protocol

```bash
# Full slice rollback
git revert <commit-sha>

# Task ledger restore
python task_reconciler.py --restore tasks/_reconcile_backups/<snapshot>.json

# Individual rollback
git reset --hard <known-good-commit>
```

Current canonical baseline: `canonical-617` (commit `ff1bb03`)
