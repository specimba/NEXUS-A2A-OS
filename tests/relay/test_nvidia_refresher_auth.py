"""nvidia_refresher must hard-fail without NVIDIA_API_KEY (no committed fallback)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import nexus_os.relay.nvidia_refresher as nr


def test_no_committed_key_fallback(monkeypatch, tmp_path):
    """The module-level default must be empty — a leaked literal fallback
    was committed here once and must never return.

    The key now resolves via nexus_os.security.secrets (env -> vault ->
    ~/.modelrelay.json), so both file stores are pointed at empty temp
    paths: with every legitimate source empty, any non-empty value could
    only be a committed literal."""
    import importlib

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("NEXUS_SECRETS_FILE", str(tmp_path / "no_vault.json"))
    monkeypatch.setenv("MODELRELAY_CONFIG", str(tmp_path / "no_relay.json"))
    try:
        importlib.reload(nr)
        assert nr.NVIDIA_API_KEY == ""
    finally:
        importlib.reload(nr)


def test_check_model_errors_without_key(monkeypatch):
    monkeypatch.setattr(nr, "NVIDIA_API_KEY", "")
    refresher = nr.NvidiaRefresher() if hasattr(nr, "NvidiaRefresher") else None
    checker = refresher or _find_checker()
    result = checker.check_model("nvidia/some-model")
    assert result["status"] == "error"
    assert "NVIDIA_API_KEY" in result["error"]


def _find_checker():
    """Locate the class exposing check_model regardless of its name."""
    for name in dir(nr):
        obj = getattr(nr, name)
        if isinstance(obj, type) and hasattr(obj, "check_model"):
            return obj()
    raise AssertionError("no class with check_model found")
