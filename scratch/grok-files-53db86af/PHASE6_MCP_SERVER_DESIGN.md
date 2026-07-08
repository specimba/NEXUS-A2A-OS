# NEXUS A2A OS — Phase 6: Always-Online MCP Server Design
**Version:** 0.1 (Governed Draft)  
**Date:** 2026-05-20  
**Status:** Design Phase — Security Tests & Governance First  
**Prepared By:** governance-orchestrator (agentic)  
**TrustKernel Gate:** Pre-design consultation passed. All architectural decisions require post-implementation TrustSnapshot validation before any code merge or deployment.

<!-- CANARY: 5c1454fcfa857195958009da5fba57e5 -->
---

## 1. Executive Summary & Win Condition

**Goal:** Transform NEXUS A2A OS from **governed reasoning layer** (Phase 0-5) into a **governed + executable action layer** by building a reliable, always-online Model Context Protocol (MCP) server.

**Win Condition (Winner Mode aligned, governance-constrained):**
- External platforms (Telegram, Slack, Notion, future) can trigger governed NEXUS actions **only** through TrustKernel-evaluated paths.
- Skills remain the source of truth for policy, behavior, and playbooks.
- MCP server acts as the **secure execution bridge** — never the policy owner.
- Zero successful bypasses of governance or TrustKernel in security test suite.
- Production-ready on Docker (primary) with HF Spaces as on-demand sandbox fallback.

**Key Principle (Non-Negotiable):**  
**"Governance before execution. TrustKernel before mutation. Skills before raw tool power."**

---

## 2. Architecture Overview (Hybrid MCP + Skills)

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXUS A2A OS (Agentic)                    │
├─────────────────────────────────────────────────────────────┤
│  Skills Layer (Policy / Playbooks)                          │
│  - nexus-memory, governance-orchestrator, drift-monitor     │
│  - connector-hub, telegram-connector, etc.                  │
│  - All high-level decision logic & thermodynamic rules      │
├─────────────────────────────────────────────────────────────┤
│  MCP Server Layer (Execution Bridge)  ← Phase 6 Focus       │
│  - Always-online (Docker on zo computer)                    │
│  - Exposes governed tools only                              │
│  - Every call → governance-orchestrator → TrustKernel       │
│  - Read-heavy in parallel, write/mutation serial + gated    │
├─────────────────────────────────────────────────────────────┤
│  TrustKernel + Security Layer                               │
│  - Canonical trust_kernel.py (already wired in core)        │
│  - Evaluates every significant action / memory write        │
│  - Produces TrustSnapshot + Decision                        │
├─────────────────────────────────────────────────────────────┤
│  External Connectors                                        │
│  - Telegram, Slack, Notion (via governed skills)            │
│  - Future: Linear, GitHub, custom agents                    │
└─────────────────────────────────────────────────────────────┘
```

**Design Rules:**
- Skills define **what** and **why** (governed behavior).
- MCP defines **how** to execute safely (tool exposure + gating).
- No direct external action without passing through governance-orchestrator.
- Memory mutations via MCP are **always** routed through memory_adapter.py + TrustKernel.

---

## 3. Core Components to Build

### 3.1 MCP Server (Dockerized)
- **Base:** FastMCP or official MCP Python SDK (or minimal custom if needed for full governance control).
- **Hosting:** Docker on primary "zo computer" for reliability and data sovereignty.
- **HF Spaces:** Only for heavy, bursty, or GPU sandboxes (ZeroGPU / paid). Never primary for connectors or memory.
- **Features:**
  - Tool registration with metadata (governance level, requires_trustkernel, side_effects)
  - Automatic pre-invocation governance check
  - Structured logging of every tool call + TrustDecision
  - Health endpoint + thermodynamic posture exposure (read-only)

### 3.2 Initial Governed Tools (Phase 6.1 — Minimal Viable)
Must pass full security test suite before "live".

| Tool Name                        | Category          | Governance Level | TrustKernel Required | Notes |
|----------------------------------|-------------------|------------------|----------------------|-------|
| `connector_hub.register_platform` | Connectivity     | High             | Yes                  | Only via governance-orchestrator |
| `telegram.send_message`          | Connector        | High             | Yes                  | Scope-limited, audit logged |
| `slack.send_message`             | Connector        | High             | Yes                  | Webhook + governed path |
| `notion.create_page` / `update`  | Connector        | High             | Yes                  | Write serial, gated |
| `nexus_memory.create_checkpoint` | Memory           | Critical         | Mandatory            | Requires explicit rationale |
| `drift_monitor.run_sweep`        | Protection       | Medium           | Recommended          | Self-initiated friendly |
| `governance.get_status`          | Observability    | Low              | No (read-only)       | Safe status exposure |
| `routine_governor.trigger_check` | Automation       | Medium           | Recommended          | Prepares for scheduled later |

**Rule:** Any new tool must include:
- Clear governance level
- Declared side effects
- Test cases in security suite

### 3.3 Governance Integration Points
- Every MCP tool invocation triggers:
  1. `governance-orchestrator.assess_intent()`
  2. `TrustKernel.evaluate(action, context, TrustSnapshot)`
  3. If approved → execute + log
  4. If denied or high-risk → return structured denial + suggested safer path
- All connector writes go through serial path + memory recording.

---

## 4. Security Test Protocol (Mandatory — Non-Negotiable)

Phase 6 will not be considered complete until the following test categories pass with documented evidence.

### Category 1: TrustKernel Gating Tests
- Test 1.1: Attempt memory mutation without TrustKernel → **MUST DENY**
- Test 1.2: High-impact connector action with low trust score → **MUST DENY or require escalation**
- Test 1.3: Replay attack on TrustDecision → **MUST REJECT**
- Test 1.4: Verify every approved action produces immutable audit entry

### Category 2: Connector Scope & Auth Tests
- Test 2.1: Telegram send without proper registration → **BLOCKED**
- Test 2.2: Attempt to escalate privileges via crafted message → **BLOCKED**
- Test 2.3: Parallel read + serial write enforcement test
- Test 2.4: Token/credential leakage prevention

### Category 3: Memory & Drift Protection via MCP
- Test 3.1: Bulk memory update attempt → rate limited + bias sweep triggered
- Test 3.2: Injection of contradictory data → drift-monitor auto-flags + checkpoint
- Test 3.3: Recovery of missing layers through MCP path → transparent + logged

### Category 4: Governance Orchestration Flow Tests
- Test 4.1: End-to-end: External trigger → governance-orchestrator → TrustKernel → skill execution → memory update
- Test 4.2: Failure mode: TrustKernel denial → graceful user/agent notification with alternatives
- Test 4.3: Multi-agent coordination under load (simulated)

### Category 5: Isolation & Fallback Tests
- Test 5.1: Docker MCP server restart resilience (state recovery via nexus-memory)
- Test 5.2: HF Spaces sandbox isolation (no persistent credentials, no memory write bypass)
- Test 5.3: Network partition handling (queue + later reconciliation with governance)

**Test Execution Requirement:**  
All tests must be runnable via `pytest` or equivalent in the MCP repo. Results logged to **Checkpoints** layer + VAP-style proof chain (future).

---

## 5. Implementation Roadmap (Governed, Incremental)

**Phase 6.1 — Foundation (Current)**
- [ ] Create Dockerized MCP server skeleton with governance hook
- [ ] Implement 3-4 lowest-risk tools (status + drift_monitor)
- [ ] Build automated security test suite (Categories 1 & 4 first)
- [ ] Update `connector-hub` to support MCP registration mode

**Phase 6.2 — Connector Activation**
- [ ] Wire Telegram, Slack, Notion through MCP tools
- [ ] Full Category 2 & 3 tests
- [ ] Live governance-orchestrator routing for external events

**Phase 6.3 — Memory & Automation Exposure**
- [ ] Expose safe nexus-memory queries + checkpoint creation
- [ ] Integrate `routine-governor` for self-triggered checks
- [ ] Drift-monitor MCP exposure

**Phase 6.4 — Hardening & Production**
- [ ] Full test suite passing + evidence in memory
- [ ] Documentation + runbooks
- [ ] Deployment guide for "zo computer" Docker
- [ ] Monitoring + alerting for TrustKernel denials / drift events

---

## 6. Risk Register & Mitigations (Governed View)

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| TrustKernel bypass in MCP | Low | Critical | Mandatory pre-invocation gate + tests + audit | governance-orchestrator |
| Connector credential leak | Medium | High | Scope-limited tokens, never store in MCP, use governed skills | connector-hub |
| Drift via external triggers | Medium | Medium | Every external action triggers drift-monitor sweep | drift-monitor |
| MCP downtime breaks agents | Low | High | Docker healthchecks + nexus-memory as source of truth + graceful degradation | routine-governor |
| Over-exposure of memory | Low | High | Read-only by default, mutations always gated | nexus-memory |

---

## 7. Next Immediate Actions (Self-Initiated by governance-orchestrator)

1. **Create repository skeleton** for MCP server (or monorepo integration decision).
2. **Implement minimal MCP server** with one safe tool (`governance.get_status`) + full TrustKernel hook.
3. **Write first security tests** (Category 1) and run them.
4. **Update PHASES_SUMMARY.md** and create checkpoint.
5. **Run full drift-monitor + skill-diagnostics** after design approval.

**Action Items Table**

| # | Action Item | Owner | Due | Priority | Status | Notes |
|---|-------------|-------|-----|----------|--------|-------|
| P6-001 | Approve this design doc via TrustKernel-aware review | governance-orchestrator + human | 2026-05-20 | High | New | Foundational for all execution |
| P6-002 | Create Docker MCP skeleton with governance hook | Agent (governed) | 2026-05-21 | High | New | Start with FastMCP or custom minimal |
| P6-003 | Implement Category 1 TrustKernel tests | Agent | 2026-05-22 | High | New | Blocking for any further tools |
| P6-004 | Update connector-hub to detect MCP mode | Agent | 2026-05-23 | Medium | New | Prepare for hybrid |
| P6-005 | Record this design as Architectural Decision in nexus-memory | nexus-memory | Immediate | High | New | Include rationale + thermodynamic alignment |

---

## 8. Thermodynamic & Governance Alignment

This design reinforces core principles:
- **Drift resistance**: External actions now trigger protection layers.
- **TrustKernel as canonical gate**: No exceptions.
- **Skills as policy owners**: MCP never decides policy.
- **Transparency & auditability**: Every decision logged with rationale.
- **Self-initiated governance**: routine-governor and drift-monitor ready for automation later.

**Checkpoint Rationale:** Phase 5→6 transition represents the shift from "reasoning about actions" to "securely executing actions". This checkpoint captures the architectural decision and security posture before any code is written.

---

**End of Phase 6 Design v0.1**  
**Status:** Ready for human + TrustKernel review. Awaiting approval to begin implementation.

**Recommended Next Command:**  
`governance-orchestrator, approve Phase 6 design and begin MCP skeleton with security tests`

---

*This document was generated under full A2A OS governance protocol with pre-action TrustKernel consultation and drift sweep.*