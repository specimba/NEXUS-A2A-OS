from nexus_os.nexusclaw.browser_ai import BrowserAINexusClawBridge
from tools.browser_ai_supervisor.external_browser_ai_director import CycleObservation, DirectorDecision


class FakeHermesDecision:
    selected_model = "internai-free-director"
    fallback_models = ["longcat-preview", "deepseek-v4-flash-free"]
    domain = "security"
    complexity = "standard"


class FakeHermes:
    def __init__(self):
        self.calls = []

    def route(self, task_id, prompt, context):
        self.calls.append((task_id, prompt, context))
        return FakeHermesDecision()


class FakeChimeraDecision:
    model = "qwen2.5-3b-instruct-q4_k_m"
    temperature = 0.4
    temperature_policy = "edt"
    tier = "local_std"


class FakeChimera:
    def __init__(self):
        self.calls = []

    def route(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return FakeChimeraDecision()


def test_non_material_browser_ai_decision_does_not_create_task():
    bridge = BrowserAINexusClawBridge(hermes_router=FakeHermes(), chimera_selector=FakeChimera())

    packet = bridge.route_packet(
        run_id="noop",
        source_id="grok-project-nexus",
        observation=CycleObservation(cdp_status="ok", visible_marker="same", visible_tail="same"),
        decision=DirectorDecision(action="NOOP_UNCHANGED", reason="visible_fingerprint_unchanged"),
    )

    assert packet.task is None
    assert packet.relay_execution_allowed is False
    assert packet.hermes == {}
    assert packet.chimera == {}


def test_material_browser_ai_artifact_builds_nexusclaw_task_and_routes_dry_run():
    hermes = FakeHermes()
    chimera = FakeChimera()
    bridge = BrowserAINexusClawBridge(hermes_router=hermes, chimera_selector=chimera)

    observation = CycleObservation(
        cdp_status="ok",
        bridge_status="ok",
        visible_marker="Grok",
        visible_tail="GrokMCPGatewayDefenseMatrix_v1 recommends schema drift and output taint tests",
        new_artifact_name="GrokMCPGatewayDefenseMatrix_v1",
        requires_bridge=True,
    )
    decision = DirectorDecision(
        action="ARTIFACT_CAPTURED",
        reason="material_delta_requires_single_provider_eval",
        provider_allowed=True,
        provider="internai",
        bridge_tools=("ping", "registry_debug", "http_diagnostic", "task_add"),
    )

    packet = bridge.route_packet(
        run_id="20260625-001",
        source_id="grok-project-nexus",
        observation=observation,
        decision=decision,
    )

    assert packet.task is not None
    assert packet.task.task_id == "BAI-20260625-001"
    assert packet.task.lane == "integration"
    assert packet.task.egress_policy["cloud_fallback"] is False
    assert packet.task.egress_policy["network_access"] == "allowlisted_public_https_via_7354_only"
    assert "mcp_http_diagnostic" in packet.task.required_capabilities
    assert "coordination_queue" in packet.task.required_capabilities
    assert packet.hermes["status"] == "routed"
    assert packet.hermes["selected_model"] == "internai-free-director"
    assert packet.chimera["status"] == "selected"
    assert packet.chimera["model"] == "qwen2.5-3b-instruct-q4_k_m"
    assert packet.relay_execution_allowed is False
    assert hermes.calls and chimera.calls


def test_browser_ai_bridge_public_export():
    from nexus_os.nexusclaw import BrowserAINexusClawBridge as Exported

    assert Exported is BrowserAINexusClawBridge
