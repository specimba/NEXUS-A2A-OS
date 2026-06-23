from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_ai_provider_bridge_requests_glm52_and_preserves_echo_metadata():
    bridge = read("src/lib/ai-provider-bridge.ts")
    assert "reconcileZAIModelEcho" in bridge
    assert "requestedModel = 'glm-5.2'" in bridge
    assert "model: requestedModel" in bridge
    assert "providerResponseModel" in bridge
    assert "glm-4-plus" in bridge
    assert "actualModel: 'z-ai/glm-5.2'" in bridge


def test_direct_zai_routes_do_not_blindly_display_completion_model():
    routes = [
        "src/app/api/stresslab/route.ts",
        "src/app/api/ai/stresslab/run/route.ts",
        "src/app/api/ai/vault/query/route.ts",
        "src/app/api/ai/research/search/route.ts",
        "src/app/api/ai/research/analyze/route.ts",
    ]
    for rel in routes:
        content = read(rel)
        assert "reconcileZAIModelEcho" in content, rel
        assert "echoedModel" in content, rel
        assert "completion.model || 'glm-4.7'" not in content, rel
        assert "actualModel: completion.model" not in content, rel
        if rel == "src/app/api/ai/stresslab/run/route.ts":
            assert "requestedModel = 'glm-5.2'" in content, rel
            assert "model: model.trim()" not in content, rel


def test_panel_status_infrastructure_is_real_not_missing_imports():
    route = read("src/app/api/panel-status/route.ts")
    hook = read("src/hooks/use-panel-status.ts")
    component = read("src/components/nexus/panel-status.tsx")
    overview = read("src/components/nexus/tabs/overview-tab.tsx")

    assert "probeReadOnlyBrainRoutes" in route
    assert "summarizeBrainProbes" in route
    assert "PANEL_ROUTES" in route
    assert "fetch('/api/panel-status'" in hook
    assert "export function PanelStatus" in component
    assert "Brain API overall" in overview

def test_dashboard_surfaces_pin_zai_collaboration_to_glm52():
    checked = [
        "src/lib/modelrelay/config.ts",
        "src/components/nexus/tabs/modelrelay-tab.tsx",
        "src/components/nexus/ai-assistant.tsx",
        "src/app/api/ai/providers/route.ts",
        "src/components/nexus/tabs/stresslab-tab.tsx",
    ]
    for rel in checked:
        content = read(rel)
        assert "GLM-4.7" not in content, rel
        assert "zai/glm-4-7" not in content, rel
        assert "glm-4-7-nim" not in content, rel
        assert "glm-4-flash" not in content, rel

    modelrelay_config = read("src/lib/modelrelay/config.ts")
    assert "name: 'Z-AI (GLM-5.2)'" in modelrelay_config
    assert "models: ['glm-5.2']" in modelrelay_config
    assert "zai/glm-5.2" in modelrelay_config

    provider_route = read("src/app/api/ai/providers/route.ts")
    assert "displayName: 'GLM-5.2'" in provider_route
    assert "actualModel: 'z-ai/glm-5.2'" in provider_route


def test_stresslab_exposes_glm52_echo_diagnostic():
    stresslab = read("src/components/nexus/tabs/stresslab-tab.tsx")
    assert "requestedModel?: string | null" in stresslab
    assert "actualModel?: string | null" in stresslab
    assert "providerResponseModel?: string | null" in stresslab
    assert "echoReconciled" in stresslab
    assert "Model Echo Diagnostic" in stresslab
    assert "Provider Echo" in stresslab
    assert "glm-4-plus" in stresslab
    assert "<SelectItem value=\"z-ai/glm-5.2\">GLM-5.2 (z-ai Free)</SelectItem>" in stresslab
