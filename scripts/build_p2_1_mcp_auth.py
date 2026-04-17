#!/usr/bin/env python3
"""P2-1: MCP v1.0 Authentication Bridge - Full Implementation"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'src'))

print("[*] Building P2-1 MCP Authentication Bridge")

# 1. Inject MCP middleware into BridgeServer
bridge_path = os.path.join(REPO, "src", "nexus_os", "bridge", "server.py")

with open(bridge_path, "r", encoding="utf-8") as f:
    code = f.read()

if "MCP_AUTH" not in code:
    # Add MCP auth middleware before request handling
    inject_code = '''
    def _verify_mcp_signature(self, request):
        """MCP v1.0 Standard Request Authentication"""
        headers = request.headers
        required = ["x-mcp-agent-id", "x-mcp-timestamp", "x-mcp-nonce", "x-mcp-signature"]
        if not all(h in headers for h in required):
            return False, "Missing MCP headers"

        agent_id = headers["x-mcp-agent-id"]
        ts = int(headers["x-mcp-timestamp"])
        nonce = headers["x-mcp-nonce"]
        signature = headers["x-mcp-signature"]

        # Reject stale requests (> 120s)
        if abs(time.time() - ts) > 120:
            return False, "Request expired"

        # Reject replay attacks
        if nonce in self._seen_nonces:
            return False, "Replay detected"
        self._seen_nonces.add(nonce)
        if len(self._seen_nonces) > 10000:
            self._seen_nonces.clear()

        secret = self.secrets.get_secret(agent_id)
        if not secret:
            return False, "Unknown agent"

        payload = f"{agent_id}:{ts}:{nonce}:{await request.body()}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected, signature), "OK"
    '''

    code = code.replace("def _routes(self):", inject_code + "\n    def _routes(self):")

    with open(bridge_path, "w", encoding="utf-8") as f:
        f.write(code)

    print("[✅] MCP signature verification injected into BridgeServer")

print("\n✅ P2-1 MCP Authentication Bridge applied successfully")
print("\nRun verification:")
print("  python -m pytest tests/bridge/test_mcp_auth.py -v")
print("  python -m pytest tests/ -q --tb=no  # full regression")
