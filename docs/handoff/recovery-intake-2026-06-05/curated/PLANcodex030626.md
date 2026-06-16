# NexusClaw Core V0 Plan

**Summary**
- Build NexusClaw as a thin governed coordinator, not another autonomous model loop.
- Treat `NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md` and Antigravity logs as contaminated planning evidence: preserve useful ideas, reject unverified deletion/quantum/livestream claims.
- Use the repo’s Zo/NemoClaw plan as the real NexusClaw base: Tailscale, MCP, A2A, NemoClaw/OpenClaw runtime, with NEXUS owning KAIJU/VAP/Vault governance.
- Keep GROSS confidential and evidence-first. No Grok native run, deletion, CDN purge, token rotation, or “Grok self-remediation” without independent proof.

**Key Changes**
- Add a `NexusClawTaskEnvelope` interface with `task_id`, `source`, `lane`, `intent`, `risk_level`, `required_capabilities`, `resource_budget`, `egress_policy`, and `evidence_refs`.
- Add a `NexusClawResultEnvelope` with `task_id`, `status`, `executor`, `evidence`, `metrics`, `vap_record_id`, and `halt_reason`.
- Add coordinator commands or MCP tools: `nexusclaw.propose`, `nexusclaw.dispatch_dry_run`, `nexusclaw.status`, and `nexusclaw.halt`.
- Reserve `7352` for NEXUS governance, `7353` for TWAVE, `7354` for GROSS bridge if active, `7355` localhost-only for internal ModelRelay, and `11436` for the NexusClaw Ollama lane.
- Default config: no cloud fallback, no broad model health polling, no per-service ngrok tunnels, no remote `stdio`, no all-filesystem agent access.

**Implementation Plan**
- Phase 1: Create a verified evidence matrix from the listed Downloads files, marking each claim as `verified`, `reframed`, `suspect`, `rejected`, or `deferred`.
- Phase 2: Rebaseline GROSS read-only state: `.grok` config, upload queue count/bytes, Grok process state, newest `D:\GROSS` evidence, and pcap/Sysmon/firewall readiness.
- Phase 3: Implement NexusClaw Core V0 as one sandboxed orchestrator lane only, routed through KAIJU, TokenGuard, resource lease, VAP logging, and a dry-run executor.
- Phase 4: Add hardening gates from the research intake: MCP transport validator, OpenClaw WebSocket/origin/token checks, immutable approval/sandbox config, and model supply-chain quarantine rules.
- Phase 5: Expand only after V0 passes: add reviewer and researcher-ops agents, then A2A cards/load test, then optional Zo cloud/Tailscale integration.

**Runtime Rules**
- ModelRelay must be demand-driven only; discovery may list models but must not infer against them.
- Hermes is planner/delegator only until provider errors are fixed; 404/402/403 provider failures must fast-fail and mark degraded.
- Docker Gordon becomes profile manager only: `core`, `mcp-light`, `observability`, and `ai-tools`.
- GROSS native Grok testing requires pcap, filesystem audit, canary payload, outbound policy, and operator approval before launch.
- Raw research dumps and Downloads files remain evidence inputs, not canonical docs.

**Test Plan**
- Unit tests: envelope validation, port ownership, disabled cloud fallback, disabled background polling, and `RELAY_HEALTH_INTERVAL=0` default.
- Security tests: reject remote `stdio`, reject unsafe `gatewayUrl`, enforce WebSocket `Origin`, block approval/sandbox config patch without KAIJU/VAP.
- Model intake tests: block pickle/unsafe `torch.load`, block `trust_remote_code`, quarantine uncensored/red-team model labels.
- Integration dry run: `nexusclaw.propose` → KAIJU approval → sandbox dry-run → VAP record → result envelope.
- GROSS sentinel test: stale/no-process/small-queue state returns quiet `DONT_NOTIFY` without deep CSV/log reads.

**Assumptions**
- First implementation package is `NexusClaw Core`.
- No secrets are copied from Downloads into repo docs or commits.
- `D:\GROSS` remains confidential and read-only unless explicitly approved.
- Premium providers stay validation-gated; local Ollama remains the default production guard tier.
