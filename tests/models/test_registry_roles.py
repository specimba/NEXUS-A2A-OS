from nexus_os.models.modal_budget import ModalRunContract, validate_modal_run_config
from nexus_os.models.registry import ModelRegistry
from nexus_os.nexusclaw.model_intake import NexusClawModelArena
from nexus_os.monitoring.provider_health import ProviderHealthMonitor


def test_core_model_budget_rejects_large_default_core_model() -> None:
    registry = ModelRegistry()
    registry.register_model(
        "qwen2.5-coder-14b",
        "hf",
        role="core",
        params_b=14.7,
        allowed_lanes=["core"],
    )

    report = registry.validate_core_resident_budget()

    assert report["passed"] is False
    assert report["violations"][0]["name"] == "qwen2.5-coder-14b"


def test_probe_and_teacher_models_do_not_violate_core_budget() -> None:
    registry = ModelRegistry()
    registry.register_model("gemma-4-12b", "hf", role="probe", params_b=12.0, allowed_lanes=["eval"])
    registry.register_model("nemotron-ultra-550b", "modal", role="teacher", params_b=550.0, active_params_b=55.0)

    report = registry.validate_core_resident_budget()

    assert report["passed"] is True


def test_quarantine_metadata_detects_uncensored_and_remote_code_models() -> None:
    registry = ModelRegistry()
    registry.register_model("safe-small-guard", "hf", role="core", params_b=0.6)
    registry.register_model("gemma-4-12b-obliterated", "hf", role="probe", params_b=12.0)
    registry.register_model("minimax-m3", "hf", role="teacher", params_b=427.0, trust_remote_code=True)

    quarantined = {model.name for model in registry.list_quarantined_models()}
    behavior_lab = {model.name for model in registry.list_behavior_control_models()}

    assert "safe-small-guard" not in quarantined
    assert "gemma-4-12b-obliterated" in quarantined
    assert "minimax-m3" in quarantined
    assert "gemma-4-12b-obliterated" in behavior_lab
    assert "minimax-m3" not in behavior_lab


def test_nexusclaw_intake_routes_obliterated_label_to_lab_only() -> None:
    arena = NexusClawModelArena()

    decision = arena.validate_intake("OBLITERATUS/Gemma-4-12B-OBLITERATED", labels=["probe"])

    assert decision.allowed is False
    assert decision.route_class == "quarantine"
    assert decision.lab_allowed is False

    lab_decision = arena.validate_intake(
        "OBLITERATUS/Gemma-4-12B-OBLITERATED",
        labels=["probe"],
        requested_lane="behavior_control",
        intent="filtering behavior analysis",
    )

    assert lab_decision.allowed is False
    assert lab_decision.route_class == "behavior_control"
    assert lab_decision.lab_allowed is True


def test_modal_contract_accepts_bounded_scale_to_zero_pilot() -> None:
    report = ModalRunContract(max_spend_usd=40.0).validate()

    assert report["passed"] is True


def test_modal_contract_rejects_always_on_and_background_polling() -> None:
    report = validate_modal_run_config(
        {
            "operation": "fine_tune",
            "max_spend_usd": 80.0,
            "min_containers": 1,
            "background_polling": True,
            "broad_model_health_checks": True,
        }
    )

    assert report["passed"] is False
    assert any("max_spend_usd" in error for error in report["errors"])
    assert any("min_containers" in error for error in report["errors"])
    assert any("background_polling" in error for error in report["errors"])
    assert any("broad_model_health_checks" in error for error in report["errors"])


def test_provider_health_periodic_loop_is_disabled_by_default() -> None:
    monitor = ProviderHealthMonitor()

    assert monitor.CHECK_INTERVAL == 0


def test_curated_models_do_not_enter_core_resident_lane() -> None:
    registry = ModelRegistry.load_default()

    longcat = registry.get_model("LongCat-2.0")
    fastcontext = registry.get_model("FastContext-1.0-4B-SFT")
    vibethinker = registry.get_model("VibeThinker-3B")

    assert longcat is not None
    assert longcat.role == "teacher"
    assert "core" not in longcat.allowed_lanes
    assert "teacher" in longcat.allowed_lanes
    assert registry.get_model("LongCat-2.0-Preview") is None

    assert fastcontext is not None
    assert fastcontext.role == "probe"
    assert "core" not in fastcontext.allowed_lanes

    assert vibethinker is not None
    assert vibethinker.role == "probe"
    assert set(vibethinker.allowed_lanes) == {"local", "eval"}


def test_behavior_control_models_are_lab_only_not_normal_route() -> None:
    registry = ModelRegistry.load_default()

    lab_models = {model.name: model for model in registry.list_behavior_control_models()}

    assert "Huihui-Nex-N2-mini-abliterated" in lab_models
    assert lab_models["Huihui-Nex-N2-mini-abliterated"].normal_route_allowed() is False
    assert lab_models["Huihui-Nex-N2-mini-abliterated"].lab_route_allowed() is True
