#!/usr/bin/env python3
"""P0 Patch: TokenGuard <-> Bridge Integration
Run: python scripts/patch_bridge_p0.py
"""
import os, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════
# PATCH 1: token_guard.py — Add get_remaining_budget() alias
# ═══════════════════════════════════════════════════════════════

tg_path = os.path.join(REPO_ROOT, "src", "nexus_os", "monitoring", "token_guard.py")
with open(tg_path, "r", encoding="utf-8") as f:
    tg = f.read()

alias = '\n    def get_remaining_budget(self, agent_id: str) -> int:\n        """Alias for GMR v3.0 compatibility."""\n        return self.remaining(agent_id)\n'

if "get_remaining_budget" not in tg:
    tg = tg.replace(
        "\n    def _get_budget_key(self, agent_id: str) -> str:",
        alias + "    def _get_budget_key(self, agent_id: str) -> str:"
    )
    with open(tg_path, "w", encoding="utf-8") as f:
        f.write(tg)
    print("[OK] token_guard.py: Added get_remaining_budget() alias")
else:
    print("[SKIP] token_guard.py: get_remaining_budget() already exists")

# ═══════════════════════════════════════════════════════════════
# PATCH 2: bridge/server.py — Budget gate + headers + fix
# ═══════════════════════════════════════════════════════════════

bs_path = os.path.join(REPO_ROOT, "src", "nexus_os", "bridge", "server.py")
with open(bs_path, "r", encoding="utf-8") as f:
    bs = f.read()

changes = 0

# 2a: Budget pre-check in handle_request()
BUDGET_GATE = """            # Budget pre-check (P0: TokenGuard gate)
            if not self.token_guard.check(req.agent_id, 1000):
                return 429, jsonrpc_error(
                    429, "Token budget exceeded",
                    trace_id=req.trace_id,
                    data={"remaining": self.token_guard.remaining(req.agent_id)},
                )

            # Track tokens (before dispatch if input_tokens known)"""

if "Budget pre-check (P0" not in bs:
    bs = bs.replace(
        "            # Track tokens (before dispatch if input_tokens known)",
        BUDGET_GATE,
        1
    )
    changes += 1
    print("[OK] bridge/server.py: Added budget pre-check in handle_request()")
else:
    print("[SKIP] bridge/server.py: Budget pre-check already in handle_request()")

# 2b: Budget pre-check in handle_submit()
OLD_SUBMIT = '            req.method = "tasks/submit"\n            self._authenticate(req)'
NEW_SUBMIT = '''            req.method = "tasks/submit"

            # Budget pre-check (P0: TokenGuard gate)
            if not self.token_guard.check(req.agent_id, 1000):
                return 429, jsonrpc_error(
                    429, "Token budget exceeded",
                    trace_id=req.trace_id,
                    data={"remaining": self.token_guard.remaining(req.agent_id)},
                )

            self._authenticate(req)'''

if OLD_SUBMIT in bs and bs.count("Budget pre-check (P0") < 2:
    bs = bs.replace(OLD_SUBMIT, NEW_SUBMIT, 1)
    changes += 1
    print("[OK] bridge/server.py: Added budget pre-check in handle_submit()")
else:
    print("[SKIP] bridge/server.py: Budget pre-check already in handle_submit() or pattern changed")

# 2c: Add X-Token-Remaining to FastAPI endpoint headers
OLD_HDR = '"X-Nexus-Output-Tokens": str(output_tokens)})'
NEW_HDR = '"X-Nexus-Output-Tokens": str(output_tokens),\n                                   "X-Token-Remaining": str(server.token_guard.remaining(agent_id))})'

if "X-Token-Remaining" not in bs:
    bs = bs.replace(OLD_HDR, NEW_HDR)
    changes += 1
    print("[OK] bridge/server.py: Added X-Token-Remaining headers")
else:
    print("[SKIP] bridge/server.py: X-Token-Remaining already present")

# 2d: Fix double-counting in jsonrpc_router
OLD_TRACK = """        status_code, response = server.handle_request("POST", body, req_headers)
        output_tokens = len(str(response).encode()) // 4
        server.token_guard.track(agent_id, input_tokens + output_tokens,
                                  operation="model_inference",
                                  input_tokens=input_tokens,
                                  output_tokens=output_tokens)"""

NEW_TRACK = """        status_code, response = server.handle_request("POST", body, req_headers)
        # handle_request() already tracks tokens via _track_tokens()
        output_tokens = len(str(response).encode()) // 4"""

if OLD_TRACK in bs:
    bs = bs.replace(OLD_TRACK, NEW_TRACK, 1)
    changes += 1
    print("[OK] bridge/server.py: Fixed double-counting in jsonrpc_router")
else:
    print("[SKIP] bridge/server.py: Double-counting fix already applied or pattern changed")

with open(bs_path, "w", encoding="utf-8") as f:
    f.write(bs)

print(f"\n[SUMMARY] bridge/server.py: {changes} changes applied")
print("Next: pytest tests/bridge/test_token_integration.py -v")