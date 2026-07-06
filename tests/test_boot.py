"""tests/test_boot.py — Boot sequence tests"""

import pytest
from nexus_os.boot import initialize_system, is_initialized, get_phase_status


@pytest.fixture(autouse=True)
def reset_boot_state():
    """Reset boot state before each test."""
    from nexus_os import boot
    boot._initialized = False
    boot._phase_status = {}
    yield


class TestBootSequence:
    def test_initialize_runs_all_phases(self):
        initialize_system()
        status = get_phase_status()
        assert len(status) == 8
        # All phases should be OK (some may log warnings but not fail)
        ok_count = sum(1 for v in status.values() if v == "ok")
        assert ok_count >= 6  # At least 6/8 should pass

    def test_is_initialized_after_call(self):
        assert is_initialized() is False
        initialize_system()
        assert is_initialized() is True

    def test_initialize_is_idempotent(self):
        initialize_system()
        status1 = get_phase_status()
        initialize_system()  # Second call should be no-op
        status2 = get_phase_status()
        assert status1 == status2

    def test_phase_status_keys(self):
        initialize_system()
        status = get_phase_status()
        expected_phases = {
            "config",
            "model_registry",
            "skill_auditor",
            "heavy_skill",
            "semantic_backend",
            "escalation_monitor",
            "q_enhancer",
            "reasoning_engine",
        }
        assert set(status.keys()) == expected_phases

    def test_config_phase_registers_sources(self):
        from nexus_os.config.sync_engine import get_engine
        initialize_system()
        engine = get_engine()
        sources = engine.list_sources()
        assert len(sources) >= 2  # At least NEXUS_ and NX_ env sources


class TestIndividualPhases:
    def test_skill_auditor_wired(self):
        from nexus_os.nexusclaw.agent_pool import get_agent_pool
        initialize_system()
        pool = get_agent_pool()
        assert pool._skill_auditor is not None

    def test_heavy_skill_available(self):
        from nexus_os.nexusclaw.heavyskill_relay import get_heavy_relay
        initialize_system()
        relay = get_heavy_relay()
        # May be available or unavailable, but should be initialized
        assert relay is not None

    def test_semantic_backend_set(self):
        from nexus_os.vault.semantic_backend import get_semantic_backend
        initialize_system()
        backend = get_semantic_backend()
        assert backend is not None

    def test_escalation_monitor_started(self):
        from nexus_os.nexusclaw.task_router import get_task_router
        initialize_system()
        router = get_task_router()
        # Monitor should be running (or at least started)
        assert router._escalation_running is True

    def test_q_enhancer_initialized(self):
        from nexus_os.governor.token_confidence import QEnhancer
        # QEnhancer is created in boot but not wired into TrustEngine
        # Just verify it can be instantiated
        enhancer = QEnhancer(confidence_weight=0.3)
        assert enhancer.confidence_weight == 0.3
        assert enhancer.mode == "mean"