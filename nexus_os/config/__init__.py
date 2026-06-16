"""nexus_os/config/ — Centralized Configuration System

ConfigSyncEngine provides a hierarchical config registry with layered sources:
  defaults < environment variables < config files < CLI overrides

Usage:
    engine = ConfigSyncEngine()
    engine.register_source(EnvSource("NEXUS_"))
    engine.load()
    value = engine.get("mcp.server_name", "default-value")
    engine.sync()
"""

from nexus_os.config.sync_engine import (
    ConfigSyncEngine,
    ConfigSource,
    ConfigEntry,
    EnvSource,
    JsonSource,
    DataclassSource,
    ConfigDiff,
    SyncReport,
)

__all__ = [
    "ConfigSyncEngine",
    "ConfigSource",
    "ConfigEntry",
    "EnvSource",
    "JsonSource",
    "DataclassSource",
    "ConfigDiff",
    "SyncReport",
]
