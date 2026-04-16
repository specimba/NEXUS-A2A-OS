"""tests/bridge/test_token_integration.py — P0: TokenGuard <-> Bridge Integration"""
import json
import pytest
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.bridge.server import BridgeServer


@pytest.fixture
def guard():
    """TokenGuard with small budget for testing."""
    return TokenGuard(budgets={"agent": 5000}, hard_stop_threshold=95.0)


@pytest.fixture
def bridge(guard):
    """BridgeServer with TokenGuard, auth bypassed for testing."""
    b = BridgeServer(token_guard=guard)
    b._authenticate = lambda req: None
    b._authorize = lambda req: None
    return b


def _request(bridge, agent_id="test-agent", payload=None):
    """Send request through handle_request()."""
    body = json.dumps(payload or {
        "method": "tasks/submit",
        "description": "test task",
    }).encode()
    headers = {
        "x-nexus-agent-id": agent_id,
        "x-nexus-project-id": "test-project",
        "x-nexus-trace-id": "trace-001",
        "x-nexus-signature": "test-sig",
    }
    return bridge.handle_request("POST", body, headers)


def _submit(bridge, agent_id="test-agent", description="test"):
    """Send request through handle_submit()."""
    body = json.dumps({"description": description}).encode()
    headers = {
        "x-nexus-agent-id": agent_id,
        "x-nexus-project-id": "test-project",
        "x-nexus-trace-id": "trace-002",
        "x-nexus-signature": "test-sig",
    }
    return bridge.handle_submit(body, headers)


# ── Budget Pre-Check ──────────────────────────────────────────

class TestBudgetGate:
    """P0: Budget gate returns 429 when budget exceeded."""

    def test_allows_when_budget_available(self, bridge, guard):
        status, resp = _request(bridge)
        assert status == 200

    def test_blocks_when_budget_exhausted(self, bridge, guard):
        guard.track("test-agent", 5000)
        status, resp = _request(bridge)
        assert status == 429

    def test_429_includes_remaining(self, bridge, guard):
        guard.track("test-agent", 4500)  # 500 remaining < 1000 required
        status, resp = _request(bridge)
        assert status == 429
        data = resp.get("error", {}).get("data", {})
        assert data.get("remaining") == 500

    def test_allows_when_above_threshold(self, bridge, guard):
        guard.track("test-agent", 3000)  # 2000 remaining > 1000 required
        status, resp = _request(bridge)
        assert status == 200

    def test_submit_also_blocks(self, bridge, guard):
        guard.track("test-agent", 5000)
        status, resp = _submit(bridge)
        assert status == 429

    def test_hard_stop_blocks(self, bridge, guard):
        # 95% of 5000 = 4750 used
        guard.track("test-agent", 4750)
        status, resp = _request(bridge)
        assert status == 429


# ── Token Tracking ─────────────────────────────────────────────

class TestTokenTracking:
    """P0: Token usage tracked after successful requests."""

    def test_remaining_decreases(self, bridge, guard):
        before = guard.remaining("test-agent")
        _request(bridge)
        after = guard.remaining("test-agent")
        assert after < before

    def test_audit_trail_created(self, bridge, guard):
        _request(bridge)
        audit = guard.get_audit(agent_id="test-agent")
        assert len(audit) > 0

    def test_multiple_requests_tracked(self, bridge, guard):
        for _ in range(3):
            _request(bridge)
        audit = guard.get_audit(agent_id="test-agent")
        assert len(audit) >= 3


# ── TokenGuard API ─────────────────────────────────────────────

class TestTokenGuardAPI:
    """P0: TokenGuard API compatibility checks."""

    def test_remaining_method(self, guard):
        assert guard.remaining("test-agent") == 5000

    def test_get_remaining_budget_alias(self, guard):
        assert guard.get_remaining_budget("test-agent") == guard.remaining("test-agent")

    def test_check_method(self, guard):
        assert guard.check("test-agent", 1000) is True
        guard.track("test-agent", 4500)
        assert guard.check("test-agent", 1000) is False


# ── Edge Cases ─────────────────────────────────────────────────

class TestEdgeCases:
    """P0: Edge cases for budget integration."""

    def test_unknown_agent_gets_default_budget(self, guard):
        # Unknown agents map to 'agent' budget category
        assert guard.check("unknown-agent", 1000) is True

    def test_budget_reset_allows_requests(self, bridge, guard):
        guard.track("test-agent", 5000)
        status, _ = _request(bridge)
        assert status == 429
        guard.reset_budget("agent")
        status, _ = _request(bridge)
        assert status == 200