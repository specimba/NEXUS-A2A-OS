---
id: NODE-MIG-FUSION_REALITY_CHECK
authority_scope: experimental
origin_sha256: 5ce1c67302de5f4951745adf55b63abab00660b0b14acfaad8a3b1e6460c273f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-15B2C2
---
# Fusion Reality Check — What We Have vs What Was Promised

**Date:** 2026-05-16  
**Source:** `nexus-glm5-fusion-pack/FUSION_RECOMMENDATIONS.md` (GLM5 outsourced agent report)  
**Status:** This document started as an aspirational contract. As of 2026-05-18, REST wrappers now exist for the core 7352 governance routes, but only focused in-process verification has been completed.

---

## The 6 "Missing" API Endpoints — The Truth

The earlier gap report was accurate when written. Current state is narrower than a full production claim: the routes now exist as FastAPI wrappers over `NexusGovernanceMCP`, and they pass focused `TestClient` checks against a temporary SQLite database.

| Endpoint | Priority | Reality | What We Actually Have |
|----------|----------|---------|----------------------|
| `GET /health` | HIGH | **BUILT, WRAPPER-LEVEL VERIFIED** | `nexus_os/bridge/server.py` returns health plus wrapper metadata |
| `POST /tasks/heartbeat` | HIGH | **BUILT, WRAPPER-LEVEL VERIFIED** | FastAPI wrapper over `NexusGovernanceMCP.heartbeat()` |
| `POST /tasks/result` | HIGH | **NOT BUILT** — exists nowhere | Nothing |
| `GET /tasks/status/{id}` | MED | **NOT BUILT** — exists nowhere | Nothing |
| `POST /skills/propose` | LOW | **BUILT, WRAPPER-LEVEL VERIFIED** | FastAPI wrapper over `NexusGovernanceMCP.propose_skill()` |
| `GET /skills/status/{id}` | LOW | **NOT BUILT** — exists nowhere | Nothing |

**Verdict:** We're building from scratch, not filling gaps. These never existed.

---

## What GLM5 Agent Actually Built (That Works)

From the fusion report's own "Must-Have / Should-Have" list, these ARE real in our dashboard:

| Feature | Status | Location |
|---------|--------|----------|
| Research Tab | ✅ Working | `src/components/nexus/tabs/research-tab.tsx` |
| Swarm Tab | ✅ Working | `src/components/nexus/tabs/swarm-tab.tsx` |
| Governor Tab | ✅ Working | `src/components/nexus/tabs/governor-tab.tsx` |
| Vault Tab | ✅ Working | `src/components/nexus/tabs/vault-tab.tsx` |
| StressLab Tab | ✅ Working | `src/components/nexus/tabs/stresslab-tab.tsx` |
| GMR Router Tab | ✅ Working | `src/components/nexus/tabs/gmr-tab.tsx` |
| Overview Tab | ✅ Working | `src/components/nexus/tabs/overview-tab.tsx` |
| Token Budget Tab | ✅ Working | `src/components/nexus/tabs/tokens-tab.tsx` |
| AI Assistant | ✅ Working | `src/components/nexus/ai-assistant.tsx` |
| Command Palette | ✅ Working | `src/components/nexus/command-palette.tsx` |

**These are Next.js frontend components that call mock/internal APIs.** They work visually but most call the dashboard's own API routes, not a real Python governance backend on 7352.

---

## What GLM5 Said Was "Experimental" (And Still Is)

| Feature | Problem |
|---------|---------|
| Live Activity Feed | Simulated — no WebSocket to real events |
| Health Timeline | Seeded random — no time-series storage |
| Rotation Analytics | Hardcoded — no event tracking DB |
| Cost Optimization | Hardcoded — no analysis engine |
| Practice Session Steps | Timed simulation — no pipeline |

---

## What We've Actually Built (Beyond the Fusion Report)

| Component | Status | Location |
|-----------|--------|----------|
| TWAVE v2.0 (EDT/LEAD/EPR/LED/CK-PLUG) | ✅ 25 tests | `nexus_os/twave/` + `twave/` |
| ChimeraRouterV2 | ✅ Working | `nexus_os/chimera_router_v2.py` |
| ARMED MCP Server (9 tools) | ✅ 12 tests | `nexus_os/mcp/server.py` |
| FunctionGemma Router | ✅ Working | `nexus_os/mcp/functiongemma_router.py` |
| ModelRelay v2.0 (real inference) | ✅ Replaced stub | `nexus_os/relay/model_relay.py` |
| LiveLatencyMonitor | ✅ 4 tests | `nexus_os/gmr/latency_monitor.py` |
| TWAVETrackerLive | ✅ 3 tests | `nexus_os/gmr/latency_monitor.py` |
| Temperature Sweep (162 runs) | ✅ Data collected | `sweep_report_nemotron.json` |
| Stress v6.1 Tool Taxonomy | 7,200 rows | `benchmarks/stres6_tool_taxonomy.py` |
| Stresstest Live (API runner) | ✅ Built | `benchmarks/stress_test_live.py` |
| ISC-Runner fix (batch download) | ✅ Fixed | `nexus_os/stresslab/isc_runner.py` |
| CVAVerifier (real enforcement) | ✅ Replaced stub | `nexus_os/governor/base.py` |
| AsyncBridgeExecutor (real HTTP) | ✅ Replaced stub | `nexus_os/engine/executor.py` |
| Worker.execute_task (hybrid) | ✅ Replaced stub | `nexus_os/swarm/worker.py` |
| TaskClassifier (+ FunctionGemma) | ✅ Replaced stub | `nexus_os/engine/hermes.py` |

---

## Next Moves

### Immediate (this session)
1. **Build the 6 API endpoints** — wire MCP engine logic to FastAPI routes on 7352. The MCP server already has `propose_skill`, `heartbeat`, `approve_proposal` — just need REST wrappers.
2. **Keep live stress calls explicitly gated** — `benchmarks/stress_test_live.py` is now dry-run by default and requires `--live` before any provider call.

### Short term
3. **nexCHA** — keep research-only unless policy changes; the tracked bypass module is disabled by default and should not be treated as production capability
4. **terminal-bench** integration — clone repo, run `tb run --agent terminus` against our models
5. **CTF-Dojo** integration — use 658 challenges as agent security benchmarks

### Architecture
6. **Port 7352** gets the 6 new REST endpoints + existing MCP server + ChimeraRouter
7. **Port 3000** dashboard stays as UI proxy, points to 7352 for real data
8. **FlareSolverr** Docker container for browser automation when needed
