# NEXUS OS - Canonical Project State

Date: 2026-05-17
Current local HEAD: main (post-governance-endpoints)
Status: Phase 0 hardened baseline; governance REST wrappers on port 7352 are focused-test verified against an isolated SQLite path; Cloudflare bypass code is present but disabled-by-default and research-only.

## Verification Gate

Latest local verification:

```text
636 passed in 27.32s
Command: python -m pytest tests -q --ignore=tests\integration\test_heartbeat.py -p no:cacheprovider
Heartbeat file separately collected 10 infra-dependent tests.
```

All `pytest.mark.skip` removed. Hermes, GMR, VaultManager, Coordinator, TokenGuard migrated to V3.
Vault uses the canonical 5-track schema (`store_track` / `retrieve_track`).
**2026-05-15: Integrity reconciliation pass** — ModelRelay hard-fails when no healthy Ollama model is available; Bridge mock execution and stub Vault behavior are now labeled in responses; CVA is labeled non-enforcing until real trait scoring lands.

## Core Thesis

Nexus OS turns local models, research evidence, and external teams into a governed, audited, low-VRAM execution system where every action is proposal-bound, test-gated, and provenance-tracked.

- **DoppelGround** prepares evidence.
- **Nexus** governs, routes, audits, and approves.
- **TWAVE** executes within VRAM limits.
- **GeniusTurtle** makes it usable.
- **Model Arena** proves what actually works on local hardware.

## System Boundaries

| Layer | Canonical Role | Current Rule |
|-------|---------------|--------------|
| GeniusTurtle | Operator UX layer | UI/API integration only; no model weights, secrets, or governance internals. |
| Nexus OS | Governance and orchestration layer | Python/FastAPI governance is the canonical brain. |
| DoppelGround | Evidence preparation layer | USE MODE; outputs must be sanitized before handoff. |
| TWAVE | Low-VRAM execution layer | Router/tracker library integrated; live wrapper/API service still requires validation. |
| Model Arena | Evidence/evaluation layer | Report-only; no automatic model deletion, fine-tuning, or promotion. |

## Core Architecture Map

| Pillar | Purpose | Canonical Areas |
|--------|---------|-----------------|
| Bridge | Protocol boundary, API ingress, SDK/MCP adapters | `nexus_os/bridge/`, `nexus_os/relay/` |
| Governor | KAIJU, policy, compliance, trust gates, TrustEngine v2.2 | `nexus_os/governor/` |
| Vault | Durable storage, 5-track memory, encryption policy | `nexus_os/vault/`, `nexus_os/db/` |
| Engine/GMR | DAG routing, Hermes/GMR decisions, execution flow | `nexus_os/engine/`, `nexus_os/gmr/` |
| Swarm | Worker orchestration, foreman coordination | `nexus_os/swarm/` |
| Monitoring | TokenGuard, VAP/audit, telemetry | `nexus_os/monitoring/`, `nexus_os/observability/` |

## What Is Verified

- Non-heartbeat test suite passes locally: **636 passed**.
- DB encryption policy hard-fails by default and allows plaintext fallback only when `allow_unencrypted=True`.
- Engine task dependency cycle detection is present and verified.
- TrustEngine v2.2 implements HARDWALL defenses: logistic scaling, adaptive decay, non-compensatory CRITICAL, 6-stage CDR.
- Vault uses canonical 5-track schema (`store_track` / `retrieve_track`).
- Bridge secrets management with per-provider health logging.

## Cloud Dashboard (Next.js)

Port 3000 — Full 8-pillar command center:
- Overview, StressLab, GMR Router, Governor, Vault, Research, Swarm, Token Budget
- AI Assistant (z-ai-web-dev-sdk LLM)
- Command Palette (Ctrl+K), System Logs (Ctrl+L)
- Interactive features: test runner, trust threshold adjustment, model toggle
- Prisma ORM + SQLite for data persistence

## Accepted Principles

- Governance Control Plane first: Python/FastAPI is canonical.
- Dashboard second: Bun/Next/relay layers must proxy governance state, not contain governance decisions.
- Retroactive provenance starts dry-run/report-only.
- Mini Model Arena starts in Phase 0 as a bounded evidence tool.
- GVAW is mandatory for externalized work: proposal-linked branches, VAP/trust trailers, reviewed merges.
- Public/private split is required before launch.
- Cloud/local OpenClaw coordination uses Git as the bus; cloud writes tasks/specs, local runs GPU/model/TWAVE work.

## Rejected Or Parked

- Bun relay calling Python classes directly.
- Auto-committing retroactive provenance.
- Broad `git add .` without review.
- Deleting model packs without inventory, backup, and rollback path.
- Heretic/uncensoring or fine-tuning in P0.
- External handoff before DoppelGround leak status is resolved.
- Claims of cryptographic VAP, full A2A, OWASP ASI, SkillFortify, or production ASBOM maturity unless locally verified.

## Critical Blockers

1. DoppelGround leak status must be resolved before external handoff or public repo flip.
2. Dashboard/relay still needs live governance API wiring proof in the running dashboard. Port 7352 REST wrappers exist and pass focused in-process tests, but that is not the same as end-to-end dashboard verification.
3. GSPP reference assets need reconciliation before they become canonical.
4. Public launch files still need security/legal review before staging.
5. Sandbox/mock env files must not be committed without an explicit policy decision.

## Canonical P0 Sequence

1. Reverify the test baseline before core commits.
2. Keep Git clean with explicit-path staging only.
3. Triage DoppelGround gitleaks report to real secret vs false positive.
4. Add or update a canonical integration ledger for repos, ports, APIs, and protected files.
5. Python/FastAPI governance REST wrappers now exist for `/skills/propose`, `/skills/status/{id}`, `/dashboard/stats`, `/governance/proposals`, `/governance/approve`, `/tasks/heartbeat`, and `/tasks/result`. Focused verification is in-process via `python -m pytest tests/bridge/test_governance_api.py -q -p no:cacheprovider`; public server binding was not part of this verification.
6. Update dashboard/relay to consume the Python governance API.
7. Add `nexus-scan.py` as dry-run provenance inventory only.
8. Add `model_arena/mini_arena.py` as report-only evidence collection.
9. Build `nexus_knowledge_base/` from sanitized DoppelGround exports with evidence hashes and quality labels.
10. Handoff to external teams only after security and governance API gates pass.
11. Keep Cloudflare bypass research isolated and disabled by default unless policy explicitly approves a local-only use case.

## Port Map

| Port | Service | Protocol | Key Endpoints |
|------|---------|----------|---------------|
| 3000 | Next.js Dashboard (Cloud) | HTTP | Overview, StressLab, GMR, Governor, Vault, Research, Swarm, Token Budget |
| 7352 | Nexus governance/control API | FastAPI | `/skills/propose`, `/skills/status/{id}`, `/dashboard/stats`, `/governance/proposals`, `/governance/approve`, `/tasks/heartbeat`, `/tasks/result`, `/tasks/submit`, `/tasks/status`, `/vault/read`, `/vault/write`, `/health` |
| 7353 | TWAVE wrapper (`/twave/*`) | HTTP | Low-VRAM execution, ChimeraRouterV2, QWAVE budget allocator |
| 11434 | Local Ollama (internal only) | HTTP | Model inference, embeddings, token-level entropy |

## New Modules (2026-05-17)

### Cloudflare Bypass Stack (`nexus_os/bridge/cloudflare_bypass.py`)
Research-only module for Cloudflare-protected API experiments. Current status:
- **Layer 1**: cloudscraper25 (enhanced fork) — JS challenges, v3 support
- **Layer 2**: curl_cffi — TLS fingerprint impersonation (Chrome/Safari/Edge)
- **Layer 3**: FlareSolverr — Docker-based headless browser for heavy protection
- **Layer 4**: nexCHA — Open-source Turnstile solver (from NopeCHALLC, forked at specimba/nopecha-extension)

The module now hard-fails closed unless `NEXUS_ENABLE_CLOUDFLARE_BYPASS=1` is set for approved local research, and the CLI output no longer prints cookie values.

Usage:
```python
from nexus_os.bridge.cloudflare_bypass import CloudflareBypassStack
os.environ["NEXUS_ENABLE_CLOUDFLARE_BYPASS"] = "1"
bypass = CloudflareBypassStack()
result = bypass.fetch("https://api.cloudflare-protected.com/v1")
```

### Governance API Runner (`run_governance_api.py`)
Single-command launcher for the canonical FastAPI governance server on port 7352.
All endpoints proxy to the `NexusGovernanceMCP` engine (same as stdio MCP server). Current proof is wrapper-level only, with isolated SQLite test coverage rather than a long-lived production durability claim.

## TrustEngine v2.2 Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Baseline Score | 25.0 | Starting trust for new agents |
| Max Score | 99.5 | Asymptotic plateau (never 100) |
| Success Delta | 4.0 x logistic(T) | Anti-gaming via logistic scaling |
| Failure Delta | -10.0 | Standard failure penalty |
| CRITICAL Delta | -20.0 | Non-compensatory hard block |
| Base Decay | 0.02 | Temporal decay rate |
| CDR Collapse | <15.0 | Minimum trust for collapse |
| CDR Escalation | <30.0 | Threshold for degraded reasoning |

---

## 2026-06-02 Audit Notes (opus-fabrication reconciliation)

Prior session logs (`GROSSantigravitygeminiopuslogs-05.txt`) claimed several changes. Verified by direct disk inspection:

**Real (verified):**
- Commit `0d8a708 fix(tests) capacity-aware thresholds` (2026-06-02, opusmanSEEKv4) added 268 lines to `tests/benchmarks/test_model_combinations.py`.
- `pyproject.toml` has `asyncio_mode = "auto"`.
- `.env` contains `ORACLESTECH_API_KEY`, `BASETEN_API_KEY`, `Zilliz Serverless-01`, `CLOUDFLARE_AI_TOKEN`.
- 214/214 security tests pass on focused `tests/security/` suite.
- Full pytest: 1341 passed / 14 failed (real bugs) / 7:42 runtime. 21 prior failures were missing `pytest-asyncio` plugin (now auto-loaded).
- **Ethicore/ORACLESTECH integration REAL** at `models/guards/guard_plane_service.py:465-510` — routes confidence 0.51-0.79 to `https://api.oraclestechnologies.com/v1/guardian/analyze` with mock fallback. Uses `ORACLESTECH_API_KEY`.
- **Baseten integration REAL** at `nexus_os/relay/model_relay.py:154-167` — uses `BASETEN_API_KEY` and `BASETEN_ENDPOINT` env vars.

**Fabricated (do not exist on disk):**
- V5/V6/V7 plan documents (no such files in `D:\GROSS\phase3\plans\` or elsewhere).
- `prod-grok-backend.json` (not found).

**Action:** V5/V6/V7 plan documents need to be written with grounded content. Item A (premium creds wiring) is **already done in production code**; remaining work is validating the live endpoints.

## 2026-06-02 Progress: D — Multi-turn detection (MT-AgentRisk)

`src/nexus_os/security/session_accumulator.py` now has 5th detection signal `_check_mt_agentrisk_patterns` covering:
- **Addition-Mapping** (3 patterns): read+disclose, recon+weaponize, teach+apply
- **Addition-Wrapping** (3 patterns): educational framing, hypothetical, fictional
- **Decomposition-Composition**: step1/step2/step3 kill chain
- **Sequential-Chaining**: ordered first/then/finally steps

All 8 manual tests pass (`C:\Users\speci.000\AppData\Local\Temp\test_mt_agentrisk.py`): Addition-Mapping 0.78, Addition-Wrapping 0.85, Decomposition-Compose 0.82, Sequential-Chain 0.65 (correctly below 0.7 escalation threshold but flagged as suspicious), benign multi-turn → 0.0.
