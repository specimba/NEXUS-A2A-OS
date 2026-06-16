from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# CANARY: 4e89f8911ae11e922f35b8bad1f132c8
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "zo_nexus_state_bridge.py"


def load_module():
    spec = importlib.util.spec_from_file_location("zo_nexus_state_bridge", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_digest_excludes_env_contents(tmp_path):
    module = load_module()
    env_path = REPO_ROOT / ".env"
    digest = module.build_digest(run_probes=False)
    encoded = json.dumps(digest)

    assert digest["security"]["no_env"] is True
    assert str(env_path) not in encoded
    assert "OPENAI_API_KEY" not in encoded
    assert "AZURE_GROK_API_KEY" not in encoded


def test_endpoint_payload_limits_routes():
    module = load_module()
    snapshot = {"git": {"branch": "test"}, "queue": {"pending": 0}}

    status, payload = module.endpoint_payload(snapshot, "/git")
    assert status == 200
    assert payload == {"branch": "test"}

    status, payload = module.endpoint_payload(snapshot, "/does-not-exist")
    assert status == 404
    assert "allowed_endpoints" in payload


def test_authorization_requires_exact_bearer_token():
    module = load_module()

    assert module.is_authorized("Bearer secret", "secret") is True
    assert module.is_authorized("Bearer wrong", "secret") is False
    assert module.is_authorized(None, "secret") is False
    assert module.is_authorized("Bearer secret", None) is False


def test_write_snapshot_creates_json(tmp_path):
    module = load_module()
    output = tmp_path / "digest.json"

    digest = module.write_snapshot(output, run_probes=False)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert loaded["schema_version"] == 1
    assert loaded["generated_at"] == digest["generated_at"]
    assert loaded["security"]["no_command_execution_in_server_mode"] is True
