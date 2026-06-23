"""Tests for NEXUS CLI-CTL dashboard sync integration."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_cli_ctl.integrations.dashboard_sync import (
    DashboardSync,
    get_dashboard_sync,
    DASHBOARD_URL,
    BRAIN_API_WS,
    BRAIN_API_HTTP,
)


class TestDashboardSyncInit:
    def test_init_default(self):
        ds = DashboardSync()
        assert ds.running is False
        assert ds._ws_connected is False
        assert ds._dashboard_reachable is False
        assert ds.SYNC_INTERVAL == 5
        assert ds.PROBE_INTERVAL == 30

    def test_init_with_state_manager(self):
        sm = MagicMock()
        ds = DashboardSync(state_manager=sm)
        assert ds.sm is sm

    def test_topics_set(self):
        ds = DashboardSync()
        assert "system" in ds.TOPICS
        assert "agents" in ds.TOPICS
        assert "tasks" in ds.TOPICS
        assert "model_relay" in ds.TOPICS
        assert "wiki" in ds.TOPICS
        assert "messaging" in ds.TOPICS


class TestDashboardSyncStatus:
    def test_status_structure(self):
        ds = DashboardSync()
        status = ds.get_status()
        assert "running" in status
        assert "ws_connected" in status
        assert "dashboard_reachable" in status
        assert "dashboard_url" in status
        assert "brain_api" in status
        assert "topics" in status
        assert "last_sync" in status
        assert isinstance(status["topics"], list)
        assert status["dashboard_url"] == DASHBOARD_URL


class TestDashboardSyncAsyncLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        ds = DashboardSync()
        await ds.start()
        assert ds.running is True
        await ds.stop()
        assert ds.running is False

    @pytest.mark.asyncio
    async def test_double_start_no_op(self):
        ds = DashboardSync()
        await ds.start()
        await ds.start()
        await ds.stop()


class TestDashboardSyncProbeLoop:
    @pytest.mark.asyncio
    async def test_probe_loop_marks_unreachable_on_error(self):
        import asyncio
        from unittest.mock import AsyncMock
        ds = DashboardSync()
        ds.PROBE_INTERVAL = 0.05
        ds.running = True
        with patch("nexus_cli_ctl.integrations.dashboard_sync.httpx.AsyncClient") as mock_client:
            cm = AsyncMock()
            cm.get = AsyncMock(side_effect=Exception("conn fail"))
            cm.__aenter__ = AsyncMock(return_value=cm)
            cm.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = cm
            task = asyncio.create_task(ds._probe_loop())
            await asyncio.sleep(0.3)
            ds.running = False
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            assert ds._dashboard_reachable is False
            assert ds._ws_connected is False

    @pytest.mark.asyncio
    async def test_push_to_dashboard_skips_when_unreachable(self):
        ds = DashboardSync()
        ds._dashboard_reachable = False
        # Should not raise
        await ds._push_to_dashboard({"type": "test"})


class TestDashboardSyncSingleton:
    def test_singleton(self):
        a = get_dashboard_sync()
        b = get_dashboard_sync()
        assert a is b

    def test_singleton_attach_state(self):
        sm = MagicMock()
        ds = get_dashboard_sync(state_manager=sm)
        assert ds.sm is sm


class TestNextGovernanceRouteContract:
    def test_governance_get_uses_brain_api_stats_contract(self):
        route = (ROOT / "src" / "app" / "api" / "governance" / "route.ts").read_text(encoding="utf-8")

        assert "NEXUS_BRAIN_API_URL" in route
        assert "`${BRAIN_API_BASE}/api/stats`" in route
        assert "/dashboard/stats" not in route


class TestBrainApiDashboardContract:
    def test_brain_api_contract_has_canonical_ports_and_routes(self):
        contract = (ROOT / "src" / "lib" / "brain-api" / "contract.ts").read_text(encoding="utf-8")
        port_doctor = (ROOT / "src" / "app" / "api" / "doctor" / "ports" / "route.ts").read_text(encoding="utf-8")

        assert "http://127.0.0.1:7352" in contract
        assert "'/health'" in contract
        assert "'/api/stats'" in contract
        assert "'/api/providers'" in contract
        assert "'/api/dashboard/sync'" in contract
        assert "7350" in port_doctor
        assert "7352" in port_doctor
        assert "7355" in port_doctor
        assert "7356" in port_doctor
        assert "3001" in port_doctor
        assert "7352 returned HTML instead of Brain API JSON" in port_doctor

    def test_brain_proxy_mutations_are_disabled_by_default(self):
        proxy = (ROOT / "src" / "app" / "api" / "brain" / "[...path]" / "route.ts").read_text(encoding="utf-8")

        assert "NEXUS_ENABLE_BRAIN_PROXY_MUTATIONS" in proxy
        assert "BRAIN_PROXY_MUTATIONS_DISABLED" in proxy
        assert "NEXUS_BRAIN_API_KEY" in proxy

    def test_settings_route_masks_provider_secrets_and_no_fake_zai_green(self):
        settings = (ROOT / "src" / "app" / "api" / "settings" / "route.ts").read_text(encoding="utf-8")

        assert "zai_sdk: true" not in settings
        assert "providerStatus" in settings
        assert "maskedSettings" in settings
        assert "maskValue" in settings

    def test_brain_status_tab_is_wired(self):
        store = (ROOT / "src" / "store" / "nexus-store.ts").read_text(encoding="utf-8")
        content = (ROOT / "src" / "components" / "nexus" / "tab-content.tsx").read_text(encoding="utf-8")
        sidebar = (ROOT / "src" / "components" / "nexus" / "sidebar.tsx").read_text(encoding="utf-8")

        assert "'brain-status'" in store
        assert "BrainStatusTab" in content
        assert "'brain-status': BrainStatusTab" in content
        assert "Brain Status" in sidebar


class TestPortOwnershipDocs:
    def test_active_docs_reject_7352_modelrelay_claims(self):
        active_docs = [
            ROOT / "AGENTS.md",
            ROOT / "knowledge.md",
            ROOT / "01_PROJECT_STATE.md",
            ROOT / "docs" / "handbook" / "08_PORT_OWNERSHIP_RULESET.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in active_docs)

        stale_claims = [
            "| 7352 | ModelRelay",
            "7352 | ModelRelay",
            "7352: ModelRelay primary",
            "7352: modelrelay",
        ]
        for claim in stale_claims:
            assert claim not in combined

        assert "7352` is Brain API only" in combined or "7352` = Brain API" in combined
        assert "7350` = Node/npm primary relay" in combined
        assert "7355` = Python fallback" in combined

    def test_port_ruleset_contains_required_preflight(self):
        rules = (ROOT / "docs" / "handbook" / "08_PORT_OWNERSHIP_RULESET.md").read_text(encoding="utf-8")

        assert "OBLIGATORY FOR ALL AGENTS" in rules
        assert "python -m pytest tests/bridge/test_port_registry.py -q" in rules
        assert "python -m nexus_os.cli.nexusctl dashboard --doctor --json" in rules
        assert "Any future agent plan, automation, or dashboard patch that mentions `7352 = ModelRelay`" in rules
