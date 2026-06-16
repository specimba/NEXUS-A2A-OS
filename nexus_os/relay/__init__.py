"""nexus_os.relay - ModelRelay singleton adapter for NEXUSCLAW model selection."""

import os

_RELAY_SINGLETON = None
RELAY_PORT_DEFAULT = int(os.environ.get("RELAY_PORT", "7355"))


def _build_relay_url(port: int = RELAY_PORT_DEFAULT) -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if ":" in host:
        return f"http://127.0.0.1:{port}"
    return f"http://127.0.0.1:{port}"


def get_model_relay(port: int = RELAY_PORT_DEFAULT):
    global _RELAY_SINGLETON
    if _RELAY_SINGLETON is None:
        from nexus_os.relay.model_relay import ModelRelay
        _RELAY_SINGLETON = ModelRelay()
    return _RELAY_SINGLETON


def reset_model_relay():
    global _RELAY_SINGLETON
    _RELAY_SINGLETON = None
