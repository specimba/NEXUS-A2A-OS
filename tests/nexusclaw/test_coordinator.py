import pytest

from nexus_os.gmr.rotator import GeniusModelRotator
from nexus_os.gmr.telemetry import TelemetryIngest
from nexus_os.nexusclaw import NexusClawCoordinator, NexusClawRuntimeConfig
from nexus_os.nexusclaw.coordinator import PORT_OWNERSHIP
from nexus_os.relay import model_relay


def task_payload(**overrides):
    payload = {
        "task_id": "NC-DRY-001",
        "source": "pytest",
        "lane": "orchestrator",
        "intent": "validate dry-run dispatch",
        "risk_level": "low",
        "required_capabilities": ["dry_run"],
        "resource_budget": {"max_tokens": 256},
        "egress_policy": {
            "cloud_fallback": False,
            "remote_stdio": False,
            "all_filesystem_access": False,
        },
        "evidence_refs": ["docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md"],
    }
    payload.update(overrides)
    return payload


def test_runtime_config_reserves_ports_and_disables_fallbacks():
    config = NexusClawRuntimeConfig()

    assert PORT_OWNERSHIP[7352] == "nexus_governance"
    assert PORT_OWNERSHIP[7355] == "modelrelay_python"
    assert PORT_OWNERSHIP[7350] == "modelrelay_npm"
    assert config.cloud_fallback_enabled is False
    assert config.background_model_polling_enabled is False
    assert config.remote_stdio_enabled is False
    assert config.all_filesystem_access_enabled is False


def test_runtime_config_rejects_cloud_fallback():
    with pytest.raises(ValueError, match="cloud fallback"):
        NexusClawRuntimeConfig(cloud_fallback_enabled=True)


def test_modelrelay_defaults_are_lazy_and_node_port():
    assert model_relay.HEALTH_CHECK_INTERVAL_S == 0
    assert model_relay.STARTUP_PORT == 7355
    assert TelemetryIngest().url == "http://localhost:7350/api/models"
    assert GeniusModelRotator().telemetry.url == "http://localhost:7350/api/models"


def test_propose_and_dispatch_dry_run_result_envelope():
    coordinator = NexusClawCoordinator()
    task = coordinator.propose(task_payload())
    result = coordinator.dispatch_dry_run(task)

    assert result.to_dict()["status"] == "dry_run"
    assert result.vap_record_id == "vap-dryrun-NC-DRY-001"
    assert result.metrics["approved_by"] == "kaiju_dry_run_gate"
    assert result.metrics["cloud_fallback_enabled"] is False
    assert result.metrics["background_model_polling_enabled"] is False
    assert result.metrics["memory_context"]["raw_payload_included"] is False
    assert result.metrics["memory_context"]["semantic_count"] == 0
    assert "semantic_mem0:disabled_by_request" in result.metrics["memory_context"]["denied_paths"]


def test_halt_blocks_later_propose():
    coordinator = NexusClawCoordinator()
    result = coordinator.halt("operator stop")

    assert result.to_dict()["status"] == "halted"
    with pytest.raises(RuntimeError, match="halted"):
        coordinator.propose(task_payload())
