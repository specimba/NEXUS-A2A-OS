---
id: NODE-MIG-IMPROVEMENT_FRAMEWORK_V2
authority_scope: experimental
origin_sha256: fcbf1698659afe2afe069b423971a4307936c687ddc50c5234eb36ebe77decf6
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-81E1F8
---
# NEXUS OS — Expert-Level Improvement Framework

**Classification:** Internal Architecture Review  
**Author:** Kilo (Systems Architect)  
**Date:** 2026-06-03  
**Grounding Commit:** `b707daf` (2026-06-03) — 1405/1405 tests passing  
**State Documents As Of:** `453e38a` (2026-06-03)

---

## TABLE OF CONTENTS

1. [Architectural Integrity Analysis](#1-architectural-integrity-analysis)
2. [Priority Matrix with Dependency Graph](#2-priority-matrix-with-dependency-graph)
3. [Execution Wave Planning](#3-execution-wave-planning)
4. [Anti-Patterns to Avoid](#4-anti-patterns-to-avoid)
5. [Measurable Success Criteria](#5-measurable-success-criteria)
6. [Risk Assessment](#6-risk-assessment)

---

## 1. Architectural Integrity Analysis

### 1.1 The Vault Invariant: Why It Is Non-Negotiable

NEXUS OS's governance model rests on a single architectural claim: **the Vault is the single source of truth for all durable agent state.** This is not a preference — it is a load-bearing invariant. Every governance decision (KAIJU gate, VAP chain entry, trust score mutation, token budget deduction) depends on the assumption that all state mutations flow through one canonical path with one consistent schema.

**What was violated:**

| Violation Site | Direct DB Path | Vault Schema | Tables Created | Lines |
|---|---|---|---|---|
| `nexus_os/mcp/server.py:639-672` | `nexus_mcp.db` | None | `vap_log`, `proposals`, `agents`, `defcon_log` | 33 |
| `models/guards/guard_plane_service.py:721-738` | `db/custom.db` | None | `GovernanceProposal` (and others) | 17 |

Both files were committed in `b707daf` with passing tests. The tests pass because they validate happy-path CRUD operations, not governance correctness.

**Why this matters — the cascade:**

1. **Schema drift.** MCP server creates `vap_log` with columns `(id, ts, type, data, hash, prev_hash)`. The canonical VAP chain in `nexus_os/governor/proof_chain.py` expects a different schema. If both are ever wired to the same database, writes will succeed but reads will silently return wrong data. Governance decisions will be based on incomplete VAP entries.

2. **Transaction isolation collapse.** The `query_db()` function in `guard_plane_service.py:724-738` opens a new `sqlite3.connect()` per call with `timeout=10.0`. There is no WAL mode, no connection pooling, no retry logic. Under concurrent agent load, `SQLITE_BUSY` will cause silent data loss — proposals will be accepted by the API but never persisted.

3. **Encryption bypass.** The Vault in `nexus_os/db/manager.py` uses `DBAdapter` with configurable encryption policy (`allow_unencrypted` flag). Both bypass sites write plaintext to unencrypted SQLite files. Any sensitive governance data (proposal details, agent trust scores, VAP chain entries) is stored without the Vault's encryption guarantees.

4. **Audit chain break.** The VAP chain is an append-only log with SHA-256 hash chaining. MCP server's `_log_vap()` at line 698-706 computes its own hash chain in its own database. If this chain is ever presented as authentic governance evidence, it will be a forgery — it was never signed by the canonical TrustKernel.

5. **Recovery impossibility.** `VaultManager` at `nexus_os/vault/manager.py` implements `store_track`/`retrieve_track` with the canonical 5-track schema. Neither bypass site uses this API. During disaster recovery, any data in `nexus_mcp.db` or `db/custom.db` will be invisible to Vault-based tooling.

### 1.2 The SOVEREIGN Mode Problem: A Living Security Debt

The V4 Master Plan (`NEXUS_OS_V4_MASTER_PLAN.md:397-406`) explicitly identifies SOVEREIGN as a CRITICAL risk level requiring mandatory PTY + KAIJU cross-agent evaluation + output sanitization. The `autonomous.py` SOVEREIGN level was flagged for disablement in Phase 0.0 (line 1055: "Disable SOVEREIGN autonomy level default, 1hr effort").

**Current state:** No code change was made. SOVEREIGN remains available. The `src/nexus_os/security/sanitizer.py` module exists with `TerminalSanitizer`, `AgentPTY`, and `VerifiableOutput` classes, but it has no production integration points — it is never imported by any runtime module, only by tests (`tests/security/test_sanitizer.py`).

**The security gap:** Any agent operating in SOVEREIGN mode can write ANSI escape sequences to stdout. Without TerminalSanitizer in the execution path, these escape sequences propagate to any consuming terminal or agent. This is the exact attack vector that prompted the V4 plan (V4 §5.1, the "Cross-Agent Terminal Injection" CWE-150 class).

### 1.3 State Document Staleness: The Trust Erosion Problem

AGENTS.md line 15 says: "Read `01_PROJECT_STATE.md` first for the current canonical state." This creates a direct dependency: if `01_PROJECT_STATE.md` is wrong, every agent that reads it starts with wrong assumptions.

| Document | Last Updated | Claims | Reality | Delta |
|---|---|---|---|---|
| `01_PROJECT_STATE.md` | 2026-05-17 | "636 passed in 27.32s" (line 13) | 1405 passed | 769 tests unaccounted for |
| `knowledge.md` | 2026-05-15 | "636 passed" (line 100) | 1405 passed | 769 tests unaccounted for |
| `worklog.md` | 2026-05-16 | "v3.1 dashboard" operational notes | b707daf committed | 18 days stale |

The PROJECT_GROUNDING_LEDGER.md (line 25) says "1405/1405 passing" but this ledger is not referenced by AGENTS.md as a primary source. The canonical state documents and the ledger are out of sync.

**Impact:** An agent reading `01_PROJECT_STATE.md` at line 17 ("All `pytest.mark.skip` removed") will believe the test baseline is 636. It will not know about the 769 new tests, the 10 new source files in b707daf, or the security integration points (Ethicore, Baseten) documented only in the audit notes section (lines 159-186).

### 1.4 Governance Duplication: Two Unreconciled KAIJUs

V4 Master Plan §6.1 (lines 423-433) documents the duplication:

| Component | NEXUS Main | HERMES Swarm Pack | Status |
|---|---|---|---|
| KAIJU Governor | `src/nexus_os/governor/base.py` | `nexus_kernel/kaiju.py` | DUPLICATED |
| VAP Chain | `src/nexus_os/governor/proof_chain.py` | `nexus_kernel/vap.py` | DUPLICATED |
| TokenGuard | `src/nexus_os/monitoring/token_guard.py` | `nexus_kernel/token_guard.py` | DUPLICATED |
| Archivist | `src/nexus_os/vault/manager.py` | `nexus_kernel/archivist.py` | DUPLICATED |

V4 §11.2 (lines 974-978) says "DELETE after import." Neither import nor deletion has occurred. Both copies continue to evolve independently.

**The risk:** If the swarm pack's KAIJU is ever activated against NEXUS main's agent fleet, it will use different trust scoring thresholds, different VAP chain schemas, and different TokenGuard budgets. An agent approved by one KAIJU may be denied by the other, creating an inconsistent governance surface.

### 1.5 Test Coverage Gaps: The False Confidence Problem

b707daf added 179 lines to `deployment_gate.py` and 98 lines to `guard_plane_service.py`. No tests exist for either.

| File | Lines Added | Tests | Coverage |
|---|---|---|---|
| `nexus_os/bridge/deployment_gate.py` | +179 | 0 | 0% |
| `models/guards/guard_plane_service.py` | +98 | Existing tests cover pre-filter logic only; governance endpoints untested | ~40% |
| `nexus_os/mcp/server.py` | +137 | `tests/mcp/test_governed_mcp_server.py` (happy paths only) | ~30% |

The 1405/1405 passing count creates an illusion of comprehensive coverage. The actual coverage is: core modules are well-tested, new governance integration points are not tested at all, and adversarial scenarios are entirely theoretical.

---

## 2. Priority Matrix with Dependency Graph

### 2.1 Dependency Chains

```
CREDENTIAL ROTATION (CR-1)
    │
    ├─► TERMINAL SANITIZER DEPLOY (P0-1)
    │       │
    │       └─► PTY ISOLATION ENFORCEMENT (P0-3)
    │               │
    │               └─► AGENTS.md SAFETY REWRITE (P0-4)
    │                       │
    │                       └─► SOVEREIGN MODE DISABLE (P0-2)
    │
    ├─► STATE DOCUMENT RECONCILIATION (P1-1)
    │       │
    │       └─► STALENESS DETECTOR (P1-2)
    │               │
    │               └─► ALL SUBSEQUENT WAVE PLANNING
    │
    └─► VAULT INVARIANT RESTORATION (P1-3)
            │
            └─► GOVERNANCE API REWRITE (P1-4)
                    │
                    └─► MCP SERVER REWRITE (P1-5)
                            │
                            └─► FULL INTEGRATION TEST SUITE (P2-3)
```

### 2.2 Priority Table

| ID | Item | Priority | Blocks | Blocked By | Effort |
|---|---|---|---|---|---|
| CR-1 | Rotate 4 exposed credentials | P0 | P0-1, P0-2 | — | 1hr |
| P0-1 | Deploy TerminalSanitizer to production execution path | P0 | P0-3 | CR-1 | 4hr |
| P0-2 | Disable SOVEREIGN default + add KAIJU cross-agent eval | P0 | P0-4 | P0-1 | 2hr |
| P0-3 | Enforce PTY isolation for all agent processes | P0 | P0-4 | P0-1 | 6hr |
| P0-4 | Rewrite AGENTS.md safety rules to reference actual deployed controls | P0 | — | P0-1, P0-2, P0-3 | 1hr |
| P1-1 | Reconcile 01_PROJECT_STATE.md, knowledge.md, worklog.md to current reality | P1 | P1-2 | — | 3hr |
| P1-2 | Implement staleness detector for state documents | P1 | P1-3 | P1-1 | 4hr |
| P1-3 | Vault invariant restoration: route MCP/guard_plane through VaultManager | P1 | P1-4 | P1-2 | 8hr |
| P1-4 | Rewrite governance API endpoints to use Vault 5-track schema | P1 | P1-5 | P1-3 | 6hr |
| P1-5 | Rewrite MCP server to use Vault for all durable state | P1 | P2-3 | P1-4 | 8hr |
| P1-6 | Import OpenShell policies from HERMES swarm pack | P1 | P2-1 | — | 1 day |
| P1-7 | Deprecate duplicate swarm pack kernel code | P1 | P2-1 | P1-6 | 1 day |
| P2-1 | Sandbox Abstraction Layer (Docker/Podman/WSL/OpenShell) | P2 | P2-2 | P1-6, P1-7 | 3 days |
| P2-2 | Platform Detector (adaptive deployment) | P2 | P2-3 | P2-1 | 1 day |
| P2-3 | Full integration test suite covering all governance paths | P2 | P3-1 | P1-5, P2-2 | 5 days |
| P3-1 | OpenClaw 1-Click RCE mitigation (CVE-2026-25253) | P3 | — | P2-3 | 2 days |
| P3-2 | Safetensors-only policy for GMR/TWAVE model loading | P3 | — | — | 1 day |
| P3-3 | ERNIE 7-expert red team execution (1200+ scenarios) | P3 | — | P2-3 | 5 days |
| P3-4 | Governance unification: NEXUS main KAIJU becomes sole canonical | P3 | — | P1-7 | 2 days |

---

## 3. Execution Wave Planning

### Wave 0: Emergency (Day 1 — Can Start Immediately)

**Goal:** Eliminate active security debt before any architectural work begins.

**Tasks:**

| Task | Files Touched | Evidence Required |
|---|---|---|
| CR-1: Rotate ORACLESTECH_API_KEY, BASETEN_API_KEY, Zilliz Serverless-01, CLOUDFLARE_AI_TOKEN | `.env`, provider dashboards | Provider dashboard screenshots showing key regeneration; old keys confirmed invalid |
| P0-1: Wire `TerminalSanitizer.sanitize()` into `Worker.execute_task()` output path | `src/nexus_os/security/sanitizer.py`, `nexus_os/swarm/worker.py` | Test: `tests/security/test_sanitizer.py` passes + new integration test verifying sanitization in Worker output |
| P0-1b: Add `from nexus_os.security.sanitizer import TerminalSanitizer` to `nexus_os/engine/hermes.py` output processing | `nexus_os/engine/hermes.py` | Hermes output passes through sanitizer; test证明 |

**Tests must pass before moving to Wave 1:** All 1405 existing + new integration tests for sanitizer wiring.

**Evidence of completion:**
```bash
python -m pytest tests/security/test_sanitizer.py tests/ -q --ignore=tests/integration/test_heartbeat.py
# Expected: 1405+ passed, 0 failed
grep -rn "TerminalSanitizer" nexus_os/swarm/worker.py nexus_os/engine/hermes.py
# Expected: at least 2 import sites
```

### Wave 1: Foundation Repair (Days 2-3)

**Goal:** Fix state document staleness and establish the staleness detection infrastructure that all subsequent waves depend on.

**Tasks:**

| Task | Files Touched | Evidence Required |
|---|---|---|
| P0-2: Add `SOVEREIGN = "sovereign"` deprecation warning in `autonomous.py` | `src/nexus_os/security/autonomous.py` | DeprecationWarning emitted when SOVEREIGN is selected |
| P0-3: Add PTY isolation enforcement in Worker startup | `nexus_os/swarm/worker.py` | Worker test verifies PTY creation |
| P0-4: Rewrite AGENTS.md §Continuous Autonomous Operation Rules | `AGENTS.md` | Section references TerminalSanitizer, PTY isolation, and TokenGuard as deployed controls |
| P1-1: Update `01_PROJECT_STATE.md` to reflect b707daf state | `01_PROJECT_STATE.md` | HEAD hash matches `b707daf`; test count shows 1405; all source files in b707daf listed |
| P1-1b: Update `knowledge.md` test count and module inventory | `knowledge.md` | Test count = 1405; new modules listed |
| P1-1c: Update `worklog.md` with b707daf entry | `worklog.md` | Entry dated 2026-06-03 references b707daf changes |
| P1-2: Create `scripts/staleness_checker.py` | `scripts/staleness_checker.py` (new) | Script reads doc headers, compares dates against `git log --format="%ai" -- <file>`, fails if delta > 7 days |
| P1-2b: Add staleness check to CI/pre-commit | `.pre-commit-config.yaml` or `pyproject.toml` | Staleness check runs automatically |

**Tests must pass before moving to Wave 2:**
```bash
python -m pytest tests/ -q --ignore=tests/integration/test_heartbeat.py
python scripts/staleness_checker.py --max-age-days 7 --docs 01_PROJECT_STATE.md knowledge.md worklog.md
# Expected: all docs PASS
```

### Wave 2: Vault Invariant Restoration (Days 4-7)

**Goal:** Eliminate all direct SQLite access. Route everything through VaultManager or DBManager.

**This is the highest-risk wave.** It touches the governance data path.

**Tasks:**

| Task | Files Touched | Evidence Required |
|---|---|---|
| P1-3a: Create `nexus_os/db/governance_tables.py` — canonical schema for governance tables (proposals, agents, vap_log, defcon_log) matching VaultManager's patterns | `nexus_os/db/governance_tables.py` (new) | Schema matches Vault 5-track patterns; migration script exists |
| P1-3b: Create migration script `scripts/migrate_governance_db.py` — moves data from `nexus_mcp.db` and `db/custom.db` into canonical Vault database | `scripts/migrate_governance_db.py` (new) | Dry-run mode; data integrity verification post-migration |
| P1-4: Rewrite `guard_plane_service.py` governance endpoints to use `VaultManager.store_track()` / `retrieve_track()` | `models/guards/guard_plane_service.py` | All `query_db()` calls replaced; tests pass |
| P1-5: Rewrite `mcp/server.py` to use `VaultManager` for all durable state | `nexus_os/mcp/server.py` | `sqlite3.connect()` calls removed; `ARMED_DB` constant removed |
| P1-6: Add integration tests for governance API through Vault | `tests/governance/test_vault_governance.py` (new) | Tests verify proposals, VAP chain, agent state all accessible via VaultManager |

**Tests must pass before moving to Wave 3:**
```bash
python -m pytest tests/ -q --ignore=tests/integration/test_heartbeat.py
# Expected: 1405+ passed, 0 failed
# Key validation: no sqlite3.connect() calls outside of nexus_os/db/ and nexus_os/vault/
grep -rn "sqlite3.connect" --include="*.py" nexus_os/ models/ | grep -v "db/manager.py" | grep -v "vault/"
# Expected: 0 results
```

### Wave 3: Integration Hardening (Days 8-12)

**Goal:** Governance duplication resolved, full test coverage for governance paths, deployment gate tested.

**Tasks:**

| Task | Files Touched | Evidence Required |
|---|---|---|
| P1-6: Import OpenShell policies | `nexus_os/sandbox/policies/` (new) | Policies from HERMES swarm pack copied |
| P1-7: Add deprecation headers to swarm pack kernel files | `HERMES/hermes-agent/nexus-swarm-pack/nexus_kernel/*.py` | Deprecation notice + import redirect |
| P2-3a: Write tests for `deployment_gate.py` | `tests/bridge/test_deployment_gate.py` (new) | All DeploymentCheck paths covered |
| P2-3b: Write adversarial tests for `guard_plane_service.py` governance endpoints | `tests/security/test_guard_plane_governance.py` (new) | SQL injection, concurrent writes, schema mismatch tests |
| P2-3c: Write adversarial tests for MCP server governance paths | `tests/mcp/test_governed_mcp_server.py` (expanded) | Tampered VAP chain detection, proposal forgery tests |
| P3-1: OpenClaw CSWSH mitigation | `nexus_os/bridge/openclaw_bridge.py` | Origin header validation; WebSocket upgrade restricted to localhost |
| P3-2: Safetensors-only policy | `nexus_os/gmr/model_loader.py`, `nexus_os/twave/` | `pickle.load()` calls removed or wrapped in allowlist |

### Wave 4: Architecture Evolution (Days 13-20)

**Goal:** Sandbox abstraction, platform detection, governance unification.

**Tasks:**

| Task | Files Touched | Evidence Required |
|---|---|---|
| P2-1: Sandbox Abstraction Layer | `nexus_os/sandbox/__init__.py` (new) | `SandboxBackend` interface with Docker, Podman, WSL, OpenShell backends |
| P2-2: Platform Detector | `nexus_os/system/platform.py` (new) | Detects Windows/Linux/Mac, WSL2, Docker, Podman |
| P3-4: Governance unification | `HERMES/hermes-agent/nexus-swarm-pack/nexus_kernel/` | All swarm pack governance code redirects to NEXUS main imports |

---

## 4. Anti-Patterns to Avoid

### 4.1 The "Tests Pass" Anti-Pattern

**Observed in:** b707daf commit message ("Fix 12 failing tests + stage v2.1 source changes")

**The problem:** Tests were fixed to pass against the new code, not to validate the new code's correctness. `guard_plane_service.py` gained 98 lines of governance endpoints. The test suite passes because no test exercises those endpoints. The commit message implies everything is validated. It is not.

**Rule:** Every commit adding governance, security, or state-management code must include at least one test that validates the invariant the code is supposed to uphold — not just that it doesn't crash.

### 4.2 The "Bypass the Abstraction" Anti-Pattern

**Observed in:** `mcp/server.py:639-672`, `guard_plane_service.py:721-738`

**The problem:** Direct `sqlite3.connect()` calls create a parallel data access layer that is invisible to the Vault's encryption policy, connection pooling, and schema management. This is not a shortcut — it is a fork of the data model.

**Rule:** No module outside `nexus_os/db/` and `nexus_os/vault/` may call `sqlite3.connect()`. All data access goes through `VaultManager` or `DBManager`. This invariant must be enforced by lint rule or CI check.

### 4.3 The "Stale State Doc" Anti-Pattern

**Observed in:** `01_PROJECT_STATE.md` (17 days stale), `knowledge.md` (19 days stale), `worklog.md` (16 days stale)

**The problem:** State documents are updated manually at the end of sessions. When sessions skip this step (autonomous mode, context overflow, interruption), the documents drift. Every subsequent agent that reads them starts with wrong assumptions. The staleness compounds.

**Rule:** State documents must be updated within the same commit that changes the referenced state. A staleness checker must run in CI. Documents older than 7 days without update must trigger a warning.

### 4.4 The "Happy Path Only" Anti-Pattern

**Observed in:** `test_governed_mcp_server.py` (tests proposal creation/approval but not concurrent writes, schema mismatches, or VAP chain tampering)

**The problem:** Governance code is only tested for the path where everything works correctly. Adversarial scenarios — what happens when two agents propose simultaneously, when the VAP chain hash doesn't match, when the database is locked — are never tested.

**Rule:** Every governance endpoint must have at least one adversarial test: concurrent write, schema mismatch, corrupted state recovery.

### 4.5 The "Commit Everything" Anti-Pattern

**Observed in:** AGENTS.md explicitly warns against `git add .` (line 33), yet the 20-file b707daf commit mixes test fixes, source changes, config changes, and new modules in a single atomic commit.

**The problem:** A single 1782-line commit with 20 files makes it impossible to revert one change without reverting all. If `deployment_gate.py` has a bug, you cannot revert just that file without also reverting the test fixes that are unrelated.

**Rule:** Test fixes and source changes should be separate commits. Config changes should be separate from source changes. New modules should be separate from modifications to existing modules.

### 4.6 The "Parallel Memory Models" Anti-Pattern

**Observed in:** V4 Master Plan §6.1 documents 5-track vs 8-channel conflict; both coexist in the codebase

**The problem:** Two memory schemas exist. Code that writes to one cannot be read by code that reads from the other. There is no reconciliation plan, no migration path, and no documentation of which schema is canonical for which use case.

**Rule:** One memory model, one canonical path. The 5-track schema (`event`, `trust`, `capability`, `failure_pattern`, `governance`) is canonical. The 8-channel model must either be reconciled into 5-track or explicitly deprecated with a migration script.

---

## 5. Measurable Success Criteria

### Wave 0 Success Criteria

| Criterion | Measurement | Target |
|---|---|---|
| Credentials rotated | `.env` contains new keys; old keys confirmed invalid at provider | 4/4 rotated |
| TerminalSanitizer in production path | `grep -rn "TerminalSanitizer" nexus_os/swarm/worker.py` returns match | 1+ integration point |
| All existing tests pass | `python -m pytest tests/ -q` | 1405+ passed, 0 failed |

### Wave 1 Success Criteria

| Criterion | Measurement | Target |
|---|---|---|
| SOVEREIGN deprecated | `python -c "from src.nexus_os.security.autonomous import ..."` emits DeprecationWarning | Warning emitted |
| PTY isolation enforced | Worker test verifies PTY creation | Test passes |
| AGENTS.md updated | Section references deployed controls, not planned controls | Section text matches deployed reality |
| State documents current | `python scripts/staleness_checker.py` returns PASS | 3/3 docs pass |
| Staleness checker in CI | Pre-commit hook or CI step runs staleness check | Automated |

### Wave 2 Success Criteria

| Criterion | Measurement | Target |
|---|---|---|
| No direct SQLite outside db/vault | `grep -rn "sqlite3.connect" --include="*.py" nexus_os/ models/ \| grep -v "db/" \| grep -v "vault/"` | 0 results |
| Governance tables in Vault schema | `VaultManager` can store/retrieve proposals, VAP entries, agent state | All CRUD operations work |
| Migration script works | `python scripts/migrate_governance_db.py --dry-run` | Reports all data that would migrate |
| Integration tests pass | `python -m pytest tests/governance/ -q` | All pass |

### Wave 3 Success Criteria

| Criterion | Measurement | Target |
|---|---|---|
| Deployment gate tested | `python -m pytest tests/bridge/test_deployment_gate.py -q` | All paths covered |
| Governance endpoints adversarially tested | `python -m pytest tests/security/test_guard_plane_governance.py -q` | Concurrent write, injection, tampering tests pass |
| OpenClaw CSWSH mitigated | WebSocket upgrade rejects non-localhost origins | Test proves rejection |
| Safetensors-only policy active | `grep -rn "pickle.load" --include="*.py" nexus_os/` returns only allowlisted sites | 0 unallowlisted pickle loads |

### Wave 4 Success Criteria

| Criterion | Measurement | Target |
|---|---|---|
| Sandbox abstraction exists | `nexus_os/sandbox/__init__.py` defines `SandboxBackend` ABC | Interface exists |
| Platform detector works | `python -c "from nexus_os.system.platform import detect_platform; print(detect_platform())"` returns correct platform | Correct detection |
| Swarm pack governance deprecated | All `nexus_kernel/kaiju.py` imports redirect to NEXUS main | Deprecation header + redirect |

---

## 6. Risk Assessment

### Wave 0 Risks

| Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|
| Credential rotation breaks live integrations | Medium | High | Test each provider after rotation; rotate one at a time | Revert `.env` to previous values; old keys still valid for grace period |
| TerminalSanitizer breaks legitimate ANSI output (e.g., progress bars) | Low | Medium | Add allowlist for known-safe ANSI sequences; test with existing output | Remove sanitizer import from Worker |

### Wave 1 Risks

| Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|
| SOVEREIGN deprecation breaks Pi Agent workflows | Medium | Medium | Emit warning, do not remove; Pi Agent can still use SOVEREIGN with explicit flag | Remove deprecation warning |
| PTY isolation breaks Windows agent execution | Medium | High | Test on Windows before deploying; PTY on Windows requires `winpty` | Disable PTY enforcement; fallback to sanitized subprocess |
| AGENTS.md rewrite introduces ambiguity | Low | Medium | Peer review before merge | Revert to previous AGENTS.md version |

### Wave 2 Risks

| Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|
| Vault schema migration loses data | Medium | Critical | Dry-run mode; backup before migration; verify row counts | Restore from backup; revert code changes |
| Governance API rewrite breaks dashboard | High | High | Dashboard tests against new endpoints before cutover | Keep old endpoints as deprecated aliases |
| MCP server rewrite breaks external tool integration | Medium | High | MCP protocol compliance test suite | Revert MCP server changes; old code still works |
| Connection pool exhaustion under load | Low | High | Load test with concurrent agents; monitor connection count | Increase pool size; add connection timeout |

### Wave 3 Risks

| Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|
| OpenClaw mitigation breaks legitimate WebSocket connections | Low | Medium | Test with known-good connections before deploying | Remove origin check |
| Safetensors policy blocks legitimate model loading | Medium | High | Allowlist known-safe pickle sources; test with all local models | Add exceptions to allowlist |

### Wave 4 Risks

| Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|
| Sandbox abstraction introduces performance overhead | Medium | Medium | Benchmark before/after; optimize hot path | Revert to direct container calls |
| Platform detection fails on exotic configurations | Low | Low | Fallback to subprocess_local with warning | Manual platform config override |
| Swarm pack deprecation breaks active swarm workflows | Medium | High | Verify all swarm workflows use NEXUS main imports before deprecating | Re-enable swarm pack imports |

---

## Appendix A: Key File Reference

| File | Role | Lines | Status |
|---|---|---|---|
| `nexus_os/mcp/server.py` | MCP bridge + governance API | 855 | VIOLATION: direct SQLite |
| `models/guards/guard_plane_service.py` | Guard plane + governance API | 1037 | VIOLATION: direct SQLite |
| `nexus_os/vault/manager.py` | Vault 5-track memory | 85 | CANONICAL: all state should flow here |
| `nexus_os/db/manager.py` | DB adapter + canonical schema | 307 | CANONICAL: schema definitions |
| `src/nexus_os/security/sanitizer.py` | TerminalSanitizer + AgentPTY + VerifiableOutput | 256+ | EXISTS but no production integration |
| `nexus_os/bridge/deployment_gate.py` | Deployment readiness checker | 326 | NO TESTS |
| `nexus_os/swarm/worker.py` | Agent worker | — | NEEDS sanitizer wiring |
| `AGENTS.md` | Agent operating protocol | 92 | STALE safety rules |
| `01_PROJECT_STATE.md` | Canonical state | 186 | STALE: claims 636 tests |
| `knowledge.md` | Quick reference | 182 | STALE: claims 636 tests |
| `worklog.md` | Session worklog | 172 | STALE: v3.1 dashboard notes only |
| `NEXUS_OS_V4_MASTER_PLAN.md` | Architecture roadmap | 1182 | CURRENT but Phase 0 uncompleted |

## Appendix B: Commit Reference

| Hash | Date | Description | Impact |
|---|---|---|---|
| `b707daf` | 2026-06-03 | Fix 12 failing tests + stage v2.1 source changes | 20 files, +1782 lines. Contains Vault invariant violations. |
| `453e38a` | 2026-06-03 | Ground on last 18h downloads, update plans and ledger | 4 files, +419 lines. Ledger updated but state docs not. |
| `0d8a708` | 2026-06-02 | Fix failing test combinations with capacity-aware thresholds | 268 lines to benchmark tests. |
| `99587b3` | 2026-05-16 | Unify core safety, memory adapter isolation, wiki checks | Safety work from prior session. |

## Appendix C: Credential Inventory (from PROJECT_GROUNDING_LEDGER.md)

| Credential | Provider | Status | Rotation Needed |
|---|---|---|---|
| `ORACLESTECH_API_KEY` | Ethicore/ORACLESTECH | In `.env`, used at `guard_plane_service.py:465` | YES — exposed during terminal poisoning window |
| `BASETEN_API_KEY` | Baseten | In `.env`, used at `model_relay.py:154` | YES — same window |
| `Zilliz Serverless-01` | Zilliz Cloud | In `.env` | YES — same window |
| `CLOUDFLARE_AI_TOKEN` | Cloudflare | In `.env` | YES — same window |
| `OPENROUTER_API_KEY` | OpenRouter | Account has $0 credits | LOW PRIORITY |
| `GROQ_API_KEY` | Groq | Free tier | LOW PRIORITY |

---

*This framework is grounded in direct code inspection of the NEXUS OS repository at commit `b707daf`. All file paths, line numbers, and test counts were verified against the actual codebase state. Recommendations are ordered by dependency: credential rotation enables security work, state doc reconciliation enables accurate planning, Vault invariant restoration enables governance correctness, and architecture evolution enables scale.*
