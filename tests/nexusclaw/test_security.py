from nexus_os.nexusclaw.security import (
    validate_mcp_transport,
    validate_model_intake,
    validate_openclaw_gateway,
    validate_runtime_config_patch,
)


def test_mcp_transport_rejects_remote_stdio():
    decision = validate_mcp_transport("stdio", remote=True)

    assert decision.allowed is False
    assert "remote stdio" in decision.reason


def test_mcp_transport_allows_local_stdio_only():
    assert validate_mcp_transport("stdio", remote=False).allowed is True


def test_mcp_transport_rejects_unknown_remote_transport():
    decision = validate_mcp_transport("ssh-shell", remote=True)

    assert decision.allowed is False
    assert "not allowlisted" in decision.reason


def test_openclaw_gateway_accepts_localhost_3000_origin():
    decision = validate_openclaw_gateway(
        "ws://localhost:18789/session",
        origin="http://localhost:3000",
        token_bound=True,
    )

    assert decision.allowed is True


def test_openclaw_gateway_accepts_tailscale_ip_host():
    decision = validate_openclaw_gateway(
        "ws://100.80.1.25:18789/session",
        origin="http://100.80.1.25:3000",
        token_bound=True,
    )

    assert decision.allowed is True


def test_openclaw_gateway_rejects_userinfo_query_token_and_bad_origin():
    assert validate_openclaw_gateway(
        "ws://token:secret@localhost:18789/session",
        origin="http://localhost:3000",
        token_bound=True,
    ).allowed is False
    assert validate_openclaw_gateway(
        "ws://localhost:18789/session?token=secret",
        origin="http://localhost:3000",
        token_bound=True,
    ).allowed is False
    assert validate_openclaw_gateway(
        "ws://localhost:18789/session",
        origin="https://evil.example",
        token_bound=True,
    ).allowed is False


def test_openclaw_gateway_requires_token_bound_access():
    decision = validate_openclaw_gateway(
        "ws://localhost:18789/session",
        origin="http://localhost:3000",
        token_bound=False,
    )

    assert decision.allowed is False
    assert "bound access token" in decision.reason


def test_runtime_config_patch_blocks_sensitive_keys_without_governance():
    patch = {
        "approval_policy": "never",
        "sandbox_mode": "danger-full-access",
        "trustedProxies": ["0.0.0.0/0"],
    }

    decision = validate_runtime_config_patch(patch, kaiju_approved=False, vap_record_id=None)

    assert decision.allowed is False
    assert "KAIJU approval" in decision.reason


def test_runtime_config_patch_blocks_json_patch_rce_knobs_without_governance():
    patch = [{"op": "replace", "path": "/tools/exec/host", "value": "gateway"}]

    decision = validate_runtime_config_patch(patch, kaiju_approved=False, vap_record_id=None)

    assert decision.allowed is False


def test_runtime_config_patch_allows_sensitive_keys_with_kaiju_and_vap():
    patch = {"permission_mode": "ask"}

    decision = validate_runtime_config_patch(patch, kaiju_approved=True, vap_record_id="vap-123")

    assert decision.allowed is True


def test_model_intake_blocks_pickle_torch_and_remote_code():
    assert validate_model_intake("model.pkl").allowed is False
    assert validate_model_intake("weights.bin").allowed is False
    assert validate_model_intake("checkpoint.pt").allowed is False
    assert validate_model_intake("repo/model", trust_remote_code=True).allowed is False


def test_model_intake_quarantines_unsafe_labels_and_accepts_safe_formats():
    assert validate_model_intake("local-uncensored-7b.gguf").allowed is False
    assert validate_model_intake("model.safetensors", labels=["guarded"]).allowed is True
    assert validate_model_intake("local-model.gguf", labels=["hash-provenance-ok"]).allowed is True


def test_behavior_control_labels_are_lab_only_not_normal_route():
    normal = validate_model_intake("DavidAU/VibeThinker-heretic-uncensored")

    assert normal.allowed is False
    assert normal.normal_allowed is False
    assert normal.lab_allowed is False
    assert normal.route_class == "quarantine"
    assert normal.blocked_reason == "behavior_control_context_required"

    lab = validate_model_intake(
        "DavidAU/VibeThinker-heretic-uncensored",
        requested_lane="behavior_control",
        intent="refusal restoration behavior analysis",
    )

    assert lab.allowed is False
    assert lab.normal_allowed is False
    assert lab.lab_allowed is True
    assert lab.route_class == "behavior_control"
    assert lab.allowed_lanes == ("behavior_control",)
    assert "kaiju_approval" in lab.required_controls
    assert "no_tool_execution" in lab.required_controls


def test_safe_base_model_can_enter_behavior_control_lab_by_context():
    decision = validate_model_intake(
        "WeiboAI/VibeThinker-3B",
        requested_lane="behavior_control",
        intent="guard stress testing and refusal ablation",
    )

    assert decision.allowed is False
    assert decision.normal_allowed is True
    assert decision.lab_allowed is True
    assert decision.route_class == "behavior_control"
