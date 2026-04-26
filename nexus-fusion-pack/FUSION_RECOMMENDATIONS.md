# GLM5.1 Fusion Pack — FUSION_RECOMMENDATIONS.md

## Pieces That Should Be Taken Into the Demo NOW

### Slice 1: Governor + Trust Engine (MUST HAVE)
**Take:** The complete Governor tab with Trust Engine integration
**Reason:** This is the strongest differentiator. No other prototype visualizes trust scoring mechanics this deeply. The interactive threshold adjustment with agent warnings, trust velocity sparklines, and hardwall configuration make governance tangible.
**Public-safe:** ⚠️ Partially — trust velocity and hardwall config are real NEXUS concepts, but the data source is local DB, not 7352. Label as "operational tooling" not "governance truth source."

### Slice 2: VAP Proof Chain (MUST HAVE)
**Take:** The Vault tab's VAP Proof Chain visualization with hash verification
**Reason:** Immutable audit trail is a core NEXUS concept. The chain verification POST and visual timeline make the concept concrete. No other prototype shows this.
**Public-safe:** ✅ Yes — vault entries are operational data, not sensitive. The hash verification demonstrates the concept without exposing internals.

### Slice 3: GMR Pool Management + Routing (SHOULD HAVE)
**Take:** The GMR Router tab's pool cards, model toggle, and AI Bridge routing simulator
**Reason:** Model routing is a core NEXUS capability. The pool-guard (preventing last-model deactivation) and routing simulation show real operational logic.
**Public-safe:** ⚠️ Partially — model names and health data are public knowledge. The routing simulation should be labeled as "simulation" not "production routing."

### Slice 4: Command Palette + Terminal (SHOULD HAVE)
**Take:** Ctrl+K command palette and system terminal with API integration
**Reason:** These are professional operator tools that elevate the dashboard beyond a monitor. The terminal's real API integration (agents, vault, gmr, tokens commands) shows the system is live.
**Public-safe:** ✅ Yes — all terminal commands query public operational data.

### Slice 5: Token Budget Heatmap (NICE TO HAVE)
**Take:** The token usage heatmap with per-agent × per-hour tooltips
**Reason:** Resource consumption patterns are visually compelling and operationally useful.
**Public-safe:** ✅ Yes — token counts are operational metrics, not sensitive.

### Slice 6: 8-Pillar Health Grid (NICE TO HAVE)
**Take:** The overview's 8-pillar health grid with pulse animation
**Reason:** Gives the NEXUS thesis visual form at a glance. Each pillar is clickable for details.
**Public-safe:** ⚠️ Only if data is clearly labeled as simulated/representational.

---

## Pieces That Should Stay Experimental

| Component | Reason to Keep Experimental |
|-----------|----------------------------|
| System Logs Panel | Entirely simulated — would be misleading if presented as real |
| Notification Center | No real event source — notifications are fabricated |
| System Configuration Dialog | No persistence — settings changes are cosmetic only |
| StressLab Test Execution | Test "runs" are simulated with progress bars — not real benchmarking |
| Live Decision Feed | Rotates through static items — not connected to 7352 governance flow |
| Research Daily Practice | Static template — not connected to any research workflow |

---

## What Should Be Fused Later for the Permanent Dashboard

### Priority 1: Wire Governor to 7352 Governance Plane
- Replace local decision DB with `GET /governance/proposals`
- Wire approval flow to `POST /governance/approve/{id}`
- Connect task governance to `POST /tasks/heartbeat` and `POST /tasks/result`
- This is the single highest-value fusion because governance truth must come from 7352

### Priority 2: Replace Simulated Feeds with WebSocket
- Live Activity Feed → WebSocket from 7352 event stream
- Live Decision Feed → WebSocket from governance proposal updates
- System Logs → WebSocket from 7352 runtime logs
- Worker Status → WebSocket from task heartbeat stream

### Priority 3: Add Skills Proposal Flow
- Connect Research tab to `POST /skills/propose` and `GET /skills/status/{id}`
- This bridges the research pipeline into the governance approval flow

### Priority 4: System Health from 7352
- Replace simulated pillar health with `GET /health` and `GET /dashboard/stats`
- This makes the overview reflect real system state, not client-side fiction

---

## Known Risks If GLM5.1 Design Is Adopted

### Risk 1: Data Source Confusion
**Risk:** The dashboard shows a mix of real DB data and simulated data without clear visual distinction. An operator could mistake simulated pillar health for real system state.
**Mitigation:** Add a visible "SIMULATED" badge on any widget that isn't backed by real telemetry. Use a consistent visual pattern (e.g., dashed borders for simulated, solid for real).

### Risk 2: API Assumption Mismatch
**Risk:** 12 of 14 dashboard API endpoints have no 7352 equivalent. If the dashboard is presented as the governance interface, it implies a local DB is the governance truth source.
**Mitigation:** Clearly separate "operational tooling" (GMR, StressLab, Tokens, Rate Limits) from "governance truth" (Governor, Vault). Only governance truth should consume from 7352.

### Risk 3: No Authentication
**Risk:** All API routes are open. No scope enforcement (SELF/PROJECT/CROSS/CRIT) exists in the dashboard.
**Mitigation:** Before any public demo, add at minimum a read-only mode that doesn't expose write operations (threshold adjust, model toggle, task reassign).

### Risk 4: Claude Proxy Instability
**Risk:** The AI Assistant tries `/api/claude` first, which returns 500 errors frequently (SSE parsing issue). It falls back to z-ai-web-dev-sdk, but the error causes a 18-47 second delay.
**Mitigation:** Reverse the order — try z-ai-web-dev-sdk first, use Claude proxy as fallback only.

### Risk 5: Mobile Experience
**Risk:** The sidebar uses a Sheet component on mobile, but several tab panels (especially GMR, Governor) have dense layouts that don't adapt well to small screens.
**Mitigation:** Add responsive breakpoints for tab content grids. Some tabs need horizontal scroll on mobile.

---

## Two or Three Pieces That Should Survive Into the Final Fusion

1. **Governor + Trust Engine visualization** — The trust scoring mechanics (velocity, hardwall, CDR thresholds, interactive adjustment) represent core NEXUS concepts that must be visible in any permanent dashboard.

2. **VAP Proof Chain** — The immutable audit trail concept is essential to NEXUS governance. The visual timeline with hash verification should be preserved regardless of which dashboard wins.

3. **Command Palette + Terminal** — Professional operator tools that elevate any dashboard from a monitor to a workstation. The terminal's API integration pattern should be the reference for all future dashboard-command interactions.
