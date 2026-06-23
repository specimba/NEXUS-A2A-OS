import pytest

from nexus_os.nexusclaw.model_intake import (
    ModelIntakeRequest,
    NexusClawModelArena,
    integrate_with_coordinator,
)
from nexus_os.nexusclaw.security import SecurityDecision
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope


class TestModelIntakeRequest:
    def test_to_envelope_creates_valid_task(self):
        request = ModelIntakeRequest(
            operation="evaluate",
            model_name="test-model",
            parameters={"temperature": 0.7},
            labels=["benchmark"],
        )
        envelope = request.to_envelope()

        assert envelope.task_id == "model-intake-test-model"
        assert envelope.source == "modelarena"
        assert envelope.lane == "orchestrator"
        assert envelope.intent == "evaluate model test-model"
        assert envelope.risk_level.value == "high"
        assert "model_access" in envelope.required_capabilities
        assert "vault_read" in envelope.required_capabilities

    def test_to_envelope_custom_source(self):
        request = ModelIntakeRequest(
            operation="compress",
            model_name="model",
            parameters={},
            labels=[],
        )
        envelope = request.to_envelope(source="custom-agent")
        assert envelope.source == "custom-agent"


class TestNexusClawModelArena:
    def test_validate_intake_caches_decision(self):
        arena = NexusClawModelArena()
        arena._cache.clear()

        decision = arena.validate_intake("safe-model.safetensors")
        assert decision.allowed is True

        decision2 = arena.validate_intake("safe-model.safetensors")
        assert decision2 is decision

    def test_hqq_compress_request(self):
        arena = NexusClawModelArena()
        request = arena.hqq_compress_request("model-7b", bits=4, group_size=64)

        assert request.operation == "hqq_compress"
        assert request.parameters["bits"] == 4
        assert request.parameters["group_size"] == 64
        assert "hqq" in request.labels

    def test_ties_merge_request(self):
        arena = NexusClawModelArena()
        request = arena.ties_merge_request("base", ["m1", "m2"], sparsity=0.3)

        assert request.operation == "ties_merge"
        assert request.parameters["merge_models"] == ["m1", "m2"]
        assert request.parameters["sparsity"] == 0.3

    def test_astra_risk_request(self):
        arena = NexusClawModelArena()
        request = arena.astra_risk_request("model-x")

        assert request.operation == "astra_risk"
        assert "astra" in request.labels
        assert "risk_assessment" in request.labels

    def test_behavior_control_request_is_lab_only(self):
        arena = NexusClawModelArena()
        request = arena.behavior_control_request("DavidAU/VibeThinker-heretic-uncensored")
        result = arena.dry_run_task(request)

        assert result["operation"] == "behavior_control"
        assert result["route_class"] == "behavior_control"
        assert result["allowed_lanes"] == ["behavior_control"]
        assert result["security_decision"]["allowed"] is False
        assert result["security_decision"]["lab_allowed"] is True
        assert "vap_record" in result["security_decision"]["required_controls"]

    def test_dry_run_task_returns_structure(self):
        arena = NexusClawModelArena()
        request = ModelIntakeRequest(
            operation="test",
            model_name="safe.safetensors",
            parameters={"param": 1},
            labels=["test"],
        )
        result = arena.dry_run_task(request)

        assert result["operation"] == "test"
        assert result["model"] == "safe.safetensors"
        assert result["dry_run"] is True
        assert "security_decision" in result


class TestIntegrateWithCoordinator:
    def test_integrate_returns_result_for_allowed_model(self):
        class MockCoordinator:
            def dispatch_dry_run(self):
                return type("Result", (), {"to_dict": lambda self: {"status": "dry_run", "task_id": "test"}})()

        result = integrate_with_coordinator(MockCoordinator(), "safe-model.safetensors")
        assert result["status"] == "dry_run"

    def test_integrate_returns_rejection_for_quarantined_model(self):
        class MockCoordinator:
            def dispatch_dry_run(self):
                return type("Result", (), {"to_dict": lambda self: {"status": "dry_run"}})()

        result = integrate_with_coordinator(MockCoordinator(), "uncensored-model.gguf")
        assert result["status"] == "rejected"
        assert result["route_class"] == "quarantine"
        assert result["blocked_reason"] == "behavior_control_context_required"
