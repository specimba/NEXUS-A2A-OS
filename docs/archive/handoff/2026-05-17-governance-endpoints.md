---
id: NODE-MIG-2026_05_17_GOVERNANCE_ENDPOINTS
authority_scope: experimental
origin_sha256: d7273243e320f1c73804a15ee208a1d1a34e59749898aeb470ac6c989c986e10
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-97FB9C
---
# Handoff: Governance API Endpoints + Cloudflare Bypass Stack

**Date:** 2026-05-17
**Agent:** Devin (Kimi K2.6)
**Branch:** main (direct commits, no feature branch — P0 hotfix style)

## What Was Built

### 1. Missing FastAPI Governance Endpoints (Port 7352)

All 6 missing endpoints from `01_PROJECT_STATE.md` P0 sequence item 5, plus the 2 from the worklog:

| Endpoint | Method | Purpose | Internal Service |
|----------|--------|---------|-----------------|
| `/skills/propose` | POST | Submit skill proposal for KAIJU review | `NexusGovernanceMCP.propose_skill()` |
| `/skills/status/{id}` | GET | Query proposal by ID | SQLite proposals table |
| `/dashboard/stats` | GET | Aggregated stats for Next.js UI | `get_vault_status()` + agent + proposal queries |
| `/governance/proposals` | GET | List all proposals (filter by status) | `list_proposals()` |
| `/governance/approve` | POST | Approve/deny a proposal | `approve_proposal()` |
| `/tasks/heartbeat` | POST | Agent heartbeat | `heartbeat()` |
| `/tasks/result` | POST | Submit task result + VAP log | `_log_vap("task_result", ...)` |

**Implementation location:** `nexus_os/bridge/server.py` inside `create_app()`, lines 710-800.

**Architecture decision:** These endpoints reuse the existing `NexusGovernanceMCP` engine (same SQLite DB as the stdio MCP server). This ensures single source of truth — whether an agent talks via stdio MCP (Claude Desktop) or REST (dashboard), it sees the same proposals, agents, and trust scores.

### 2. Cloudflare Bypass Stack

**File:** `nexus_os/bridge/cloudflare_bypass.py` (256 lines)

Layered fallback stack for accessing Cloudflare-protected commercial model APIs:

1. **cloudscraper25** — Enhanced fork with v3 challenge support, Node.js interpreter
2. **curl_cffi** — TLS fingerprint impersonation (Chrome124/Safari/Edge)
3. **FlareSolverr** — Docker-based headless browser proxy (port 8191)
4. **nexCHA** — Open-source Turnstile solver placeholder (from NopeCHALLC)

**Key design:**
- Each layer is optional — if the dependency isn't installed, it skips gracefully
- Session cookie caching across layers (cloudscraper cookies reused with curl_cffi)
- Configurable fallback chain, delay, timeout, proxy
- `DEBUG` mode via `NEXUS_BYPASS_DEBUG=1`

**Usage:**
```python
from nexus_os.bridge.cloudflare_bypass import CloudflareBypassStack
bypass = CloudflareBypassStack(proxy="http://user:pass@proxy:8080", delay=10)
result = bypass.fetch("https://api.protected-site.com/v1/chat")
if result.success:
    print(result.content)
```

### 3. Governance API Runner

**File:** `run_governance_api.py`

Single-command launcher: `python run_governance_api.py --port 7352`

### 4. Tests

**File:** `tests/bridge/test_governance_api.py` (10 test cases)

Tests all 7 new governance endpoints + 3 Cloudflare bypass module tests.

**Note:** `.gitignore` updated to allow this test file (`!tests/bridge/test_governance_api.py`).

## Verification Steps

1. **Syntax check:**
   ```bash
   python -m py_compile nexus_os/bridge/server.py
   python -m py_compile nexus_os/bridge/cloudflare_bypass.py
   python -m py_compile run_governance_api.py
   ```

2. **Run new tests:**
   ```bash
   python -m pytest tests/bridge/test_governance_api.py -v
   ```

3. **Run full suite (no regressions):**
   ```bash
   python -m pytest tests/ -q --ignore=tests/integration/test_heartbeat.py
   ```

4. **Start server manually:**
   ```bash
   python run_governance_api.py --port 7352
   # In another terminal:
   curl http://localhost:7352/health
   curl -X POST http://localhost:7352/skills/propose \
     -H "Content-Type: application/json" \
     -d '{"skill":"test.echo","params":{},"agent_id":"devin"}'
   ```

## Integration with Dashboard

The Next.js dashboard currently uses mock data. To wire it to real governance API:

1. Update dashboard API routes to call `http://localhost:7352/dashboard/stats`
2. Use `/governance/proposals` instead of local mock arrays
3. Use `/skills/propose` + `/governance/approve` for the governance proposal flow

## Known Limitations

- **Cloudflare stack** is install-on-demand — `cloudscraper25`, `curl_cffi`, and FlareSolverr Docker are not bundled. Install with:
  ```bash
  pip install cloudscraper25 curl_cffi requests
  docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
  ```
- **nexCHA** is a placeholder — requires building from `specimba/nopecha-extension` and setting `NEXUS_OS_NEXCHA_PATH`
- **Vault read/write** endpoints in bridge/server.py still return stubs (`"storage": "stub_non_durable"`) — out of scope for this pass

## Files Changed

- `nexus_os/bridge/server.py` — Added governance endpoints to `create_app()`
- `nexus_os/bridge/cloudflare_bypass.py` — New file
- `run_governance_api.py` — New file
- `tests/bridge/test_governance_api.py` — New file
- `.gitignore` — Added exception for new test file
- `01_PROJECT_STATE.md` — Updated status, port map, blockers, P0 sequence
- `scripts/check_syntax.py` — New helper script
