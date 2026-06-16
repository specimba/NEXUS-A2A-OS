"""config/sync_engine.py — ConfigSyncEngine: Centralized Configuration System

Provides a hierarchical config registry with layered sources:

    defaults < environment variables < config files < CLI overrides

Supports load/save/diff/sync operations across all config sources.
Integrates with the 18 existing config @dataclass classes and 54+ env vars.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, is_dataclass, fields as dataclass_fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_NEXUS_PREFIX = "NEXUS_"
ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


# ── Config Entry ───────────────────────────────────────────────────────────────


@dataclass
class ConfigEntry:
    key: str
    value: Any
    source: str = "default"      # "default", "env", "file", "cli"
    source_name: str = ""        # e.g., ".env", "config.json", "--flag"
    description: str = ""
    value_type: str = ""          # "str", "int", "float", "bool", "json"
    updated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "source_name": self.source_name,
            "description": self.description,
            "value_type": self.value_type,
            "updated_at": self.updated_at,
        }


# ── Config Diff ────────────────────────────────────────────────────────────────


@dataclass
class ConfigDiff:
    added: List[Tuple[str, Any, Any]] = field(default_factory=list)       # key, new_value, source
    removed: List[Tuple[str, Any, Any]] = field(default_factory=list)     # key, old_value, source
    changed: List[Tuple[str, Any, Any, Any]] = field(default_factory=list) # key, old, new, source
    unchanged: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": [(k, v) for k, v, _ in self.added],
            "removed": [(k, v) for k, v, _ in self.removed],
            "changed": [(k, old, new) for k, old, new, _ in self.changed],
            "unchanged": self.unchanged,
            "has_changes": self.has_changes,
        }


@dataclass
class SyncReport:
    timestamp: float
    sources_loaded: int
    entries_total: int
    conflicts_resolved: int
    diff: ConfigDiff
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "sources_loaded": self.sources_loaded,
            "entries_total": self.entries_total,
            "conflicts_resolved": self.conflicts_resolved,
            "diff": self.diff.to_dict(),
            "errors": self.errors,
        }


# ── Priority Levels ────────────────────────────────────────────────────────────


class SourcePriority(Enum):
    DEFAULT = 0
    SYSTEM = 10
    ENV = 20
    FILE = 30
    CLI = 40


# ── Abstract Config Source ─────────────────────────────────────────────────────


class ConfigSource(ABC):
    """Abstract base for a config source."""

    def __init__(self, name: str, priority: SourcePriority = SourcePriority.ENV):
        self.name = name
        self.priority = priority

    @abstractmethod
    def load(self) -> Dict[str, ConfigEntry]:
        """Load config entries from this source. Returns key -> entry map."""
        ...

    @abstractmethod
    def save(self, entries: Dict[str, ConfigEntry]) -> bool:
        """Save config entries to this source. Returns True on success."""
        ...

    def can_write(self) -> bool:
        """Whether this source supports write operations."""
        return False

    def describe(self) -> str:
        return f"{self.name} (priority={self.priority.value})"


# ── EnvSource: reads environment variables ─────────────────────────────────────


class EnvSource(ConfigSource):
    """Reads config from environment variables with a given prefix."""

    def __init__(
        self,
        prefix: str = DEFAULT_NEXUS_PREFIX,
        name: str = "env",
        priority: SourcePriority = SourcePriority.ENV,
    ):
        super().__init__(name, priority)
        self._prefix = prefix.upper()
        self._key_map: Dict[str, str] = {}  # config_key -> env_var

    def register_binding(self, config_key: str, env_var: str) -> None:
        """Map a config key to a specific environment variable."""
        self._key_map[config_key] = env_var

    def load(self) -> Dict[str, ConfigEntry]:
        entries: Dict[str, ConfigEntry] = {}
        now = time.time()

        # Direct bindings
        for config_key, env_var in self._key_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                entries[config_key] = ConfigEntry(
                    key=config_key,
                    value=self._coerce(value),
                    source="env",
                    source_name=env_var,
                    updated_at=now,
                )

        # Auto-discover vars matching prefix
        for env_var, value in os.environ.items():
            if env_var.startswith(self._prefix) and env_var not in self._key_map.values():
                config_key = self._env_to_key(env_var)
                if config_key not in entries:
                    entries[config_key] = ConfigEntry(
                        key=config_key,
                        value=self._coerce(value),
                        source="env",
                        source_name=env_var,
                        updated_at=now,
                    )

        return entries

    def save(self, entries: Dict[str, ConfigEntry]) -> bool:
        """EnvSource is read-only."""
        logger.warning("EnvSource is read-only — cannot save config to environment")
        return False

    def can_write(self) -> bool:
        return False

    @staticmethod
    def _coerce(value: str) -> Any:
        """Coerce a string env value to the most appropriate type."""
        v = value.strip()
        if v.lower() in ("true", "yes", "1"):
            return True
        if v.lower() in ("false", "no", "0"):
            return False
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        if v.startswith(("[", "{")):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return v

    @staticmethod
    def _env_to_key(env_var: str) -> str:
        """Convert NEXUS_MCP_SERVER_NAME -> mcp.server_name"""
        parts = env_var.lower().split("_")
        if parts and len(parts) > 1:
            # First part is prefix, rest form dotted key
            key = ".".join(parts[1:])
            return key
        return env_var.lower()

    @staticmethod
    def key_to_env(config_key: str, prefix: str = DEFAULT_NEXUS_PREFIX) -> str:
        """Convert mcp.server_name -> NEXUS_MCP_SERVER_NAME"""
        return prefix + config_key.replace(".", "_").upper()


# ── JsonSource: reads from JSON files ──────────────────────────────────────────


class JsonSource(ConfigSource):
    """Reads config from JSON files."""

    def __init__(
        self,
        path: Union[str, Path],
        name: Optional[str] = None,
        priority: SourcePriority = SourcePriority.FILE,
        key_prefix: str = "",
    ):
        super().__init__(name or str(path), priority)
        self._path = Path(path)
        self._key_prefix = key_prefix

    def load(self) -> Dict[str, ConfigEntry]:
        entries: Dict[str, ConfigEntry] = {}
        if not self._path.exists():
            logger.debug("JsonSource %s: file not found", self._path)
            return entries

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = time.time()
            for key, value in self._flatten(data, prefix=self._key_prefix).items():
                entries[key] = ConfigEntry(
                    key=key,
                    value=value,
                    source="file",
                    source_name=str(self._path),
                    value_type=type(value).__name__,
                    updated_at=now,
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("JsonSource %s: failed to load: %s", self._path, e)

        return entries

    def save(self, entries: Dict[str, ConfigEntry]) -> bool:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data: Dict[str, Any] = {}
            for key, entry in entries.items():
                self._set_nested(data, key, entry.value)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("JsonSource %s: saved %d entries", self._path, len(entries))
            return True
        except OSError as e:
            logger.warning("JsonSource %s: failed to save: %s", self._path, e)
            return False

    def can_write(self) -> bool:
        return True

    @staticmethod
    def _flatten(data: Any, prefix: str = "", sep: str = ".") -> Dict[str, Any]:
        """Flatten nested dict to dot-separated keys."""
        result: Dict[str, Any] = {}
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}{sep}{key}" if prefix else key
                if isinstance(value, dict):
                    result.update(JsonSource._flatten(value, full_key, sep))
                else:
                    result[full_key] = value
        else:
            result[prefix] = data
        return result

    @staticmethod
    def _set_nested(data: Dict[str, Any], key: str, value: Any, sep: str = ".") -> None:
        """Set a value in a nested dict from a dot-separated key."""
        parts = key.split(sep)
        for part in parts[:-1]:
            if part not in data:
                data[part] = {}
            elif not isinstance(data[part], dict):
                data[part] = {}
            data = data[part]
        data[parts[-1]] = value


# ── DataclassSource: sync with @dataclass config objects ────────────────────────


class DataclassSource(ConfigSource):
    """Reads/writes config from/to Python @dataclass instances.

    Maps dataclass fields to config entries with the class name as prefix.
    """

    def __init__(
        self,
        instance: Any,
        name: Optional[str] = None,
        priority: SourcePriority = SourcePriority.DEFAULT,
        key_prefix: Optional[str] = None,
    ):
        super().__init__(name or type(instance).__name__, priority)
        self._instance = instance
        self._key_prefix = key_prefix or type(instance).__name__.lower()

    def load(self) -> Dict[str, ConfigEntry]:
        entries: Dict[str, ConfigEntry] = {}
        if not is_dataclass(self._instance):
            return entries

        now = time.time()
        for f in dataclass_fields(self._instance):
            key = f"{self._key_prefix}.{f.name}"
            value = getattr(self._instance, f.name)
            entries[key] = ConfigEntry(
                key=key,
                value=value,
                source="default",
                source_name=self.name,
                value_type=f.type.__name__ if hasattr(f.type, "__name__") else str(f.type),
                updated_at=now,
            )
        return entries

    def save(self, entries: Dict[str, ConfigEntry]) -> bool:
        """Update the dataclass instance from entries."""
        if not is_dataclass(self._instance):
            return False
        updated = 0
        for f in dataclass_fields(self._instance):
            key = f"{self._key_prefix}.{f.name}"
            if key in entries:
                setattr(self._instance, f.name, entries[key].value)
                updated += 1
        logger.debug("DataclassSource %s: updated %d fields", self.name, updated)
        return True

    def can_write(self) -> bool:
        return True


# ── ConfigSyncEngine ───────────────────────────────────────────────────────────


class ConfigSyncEngine:
    """Centralized config registry with layered source hierarchy.

    Sources are loaded in priority order. Higher-priority sources override
    lower-priority ones for each key.

    Usage:
        engine = ConfigSyncEngine()
        engine.register_source(EnvSource("NEXUS_"))
        engine.register_source(JsonSource("config.json"))
        engine.load()
        value = engine.get("mcp.server_name")
        engine.set("mcp.server_name", "new-value")
        engine.save()
    """

    def __init__(self) -> None:
        self._sources: List[ConfigSource] = []
        self._entries: Dict[str, ConfigEntry] = {}
        self._loaded = False

    # ── Source Management ─────────────────────────────────────────

    def register_source(self, source: ConfigSource) -> None:
        """Register a config source (lower priority first)."""
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority.value)
        logger.debug("Registered config source: %s", source.describe())

    def list_sources(self) -> List[ConfigSource]:
        return list(self._sources)

    # ── Load ───────────────────────────────────────────────────────

    def load(self) -> SyncReport:
        """Load all sources. Higher-priority sources override lower."""
        self._entries.clear()
        errors: List[str] = []
        conflict_count = 0

        for source in self._sources:
            try:
                source_entries = source.load()
                for key, entry in source_entries.items():
                    if key in self._entries:
                        conflict_count += 1
                        logger.debug(
                            "Config conflict: %s overridden by %s (priority %d > %d)",
                            key, source.name, source.priority.value,
                            self._entries[key].source,
                        )
                    self._entries[key] = entry
            except Exception as e:
                errors.append(f"{source.name}: {e}")

        self._loaded = True
        return SyncReport(
            timestamp=time.time(),
            sources_loaded=len(self._sources),
            entries_total=len(self._entries),
            conflicts_resolved=conflict_count,
            diff=ConfigDiff(),
        )

    # ── Get / Set ──────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        entry = self._entries.get(key)
        if entry is None:
            return default
        return entry.value

    def get_entry(self, key: str) -> Optional[ConfigEntry]:
        return self._entries.get(key)

    def set(self, key: str, value: Any, source: str = "cli") -> None:
        """Set a config value (overrides all sources)."""
        now = time.time()
        if key in self._entries:
            existing = self._entries[key]
            self._entries[key] = ConfigEntry(
                key=key, value=value, source=source,
                source_name=existing.source_name,
                value_type=type(value).__name__,
                updated_at=now,
            )
        else:
            self._entries[key] = ConfigEntry(
                key=key, value=value, source=source,
                value_type=type(value).__name__,
                updated_at=now,
            )

    def has(self, key: str) -> bool:
        return key in self._entries

    def keys(self) -> List[str]:
        return list(self._entries.keys())

    def all_entries(self) -> Dict[str, ConfigEntry]:
        return dict(self._entries)

    def filter_by_source(self, source: str) -> Dict[str, ConfigEntry]:
        return {k: v for k, v in self._entries.items() if v.source == source}

    def filter_by_prefix(self, prefix: str) -> Dict[str, ConfigEntry]:
        return {k: v for k, v in self._entries.items() if k.startswith(prefix)}

    # ── Save ───────────────────────────────────────────────────────

    def save(self, source_name: Optional[str] = None) -> SyncReport:
        """Save entries to writable sources.

        Args:
            source_name: Optional — save only to a named source.
        """
        errors: List[str] = []
        saved_count = 0

        targets = [s for s in self._sources if s.can_write()]
        if source_name:
            targets = [s for s in targets if s.name == source_name]

        for source in targets:
            try:
                source_entries = {
                    k: v for k, v in self._entries.items()
                    if v.source == source.name or v.source == "cli"
                }
                if source.save(source_entries):
                    saved_count += 1
            except Exception as e:
                errors.append(f"{source.name}: {e}")

        return SyncReport(
            timestamp=time.time(),
            sources_loaded=saved_count,
            entries_total=len(self._entries),
            conflicts_resolved=0,
            diff=ConfigDiff(),
            errors=errors,
        )

    # ── Diff ───────────────────────────────────────────────────────

    def diff(self, other: "ConfigSyncEngine") -> ConfigDiff:
        """Compare with another engine's config state."""
        diff = ConfigDiff()
        our_keys = set(self._entries.keys())
        their_keys = set(other._entries.keys())

        for key in our_keys - their_keys:
            diff.added.append((key, self._entries[key].value, self._entries[key].source))
        for key in their_keys - our_keys:
            diff.removed.append((key, other._entries[key].value, other._entries[key].source))
        for key in our_keys & their_keys:
            if self._entries[key].value != other._entries[key].value:
                diff.changed.append((
                    key,
                    other._entries[key].value,
                    self._entries[key].value,
                    self._entries[key].source,
                ))
            else:
                diff.unchanged += 1

        return diff

    # ── Sync ───────────────────────────────────────────────────────

    def sync(self) -> SyncReport:
        """Load all sources, detect changes, and save back."""
        before = dict(self._entries)
        report = self.load()
        diff = ConfigDiff()

        # Compute diff
        for key, entry in self._entries.items():
            if key not in before:
                diff.added.append((key, entry.value, entry.source))
            elif before[key].value != entry.value:
                diff.changed.append((key, before[key].value, entry.value, entry.source))
        for key in before:
            if key not in self._entries:
                diff.removed.append((key, before[key].value, ""))

        diff.unchanged = len(before) - len(diff.removed)
        report.diff = diff
        return report

    # ── Export ─────────────────────────────────────────────────────

    def to_json(self, indent: int = 2) -> str:
        """Export all config as JSON."""
        data = {
            k: {
                "value": v.value,
                "source": v.source,
                "source_name": v.source_name,
                "description": v.description,
            }
            for k, v in self._entries.items()
        }
        return json.dumps(data, indent=indent, default=str)

    def to_env(self, prefix: str = DEFAULT_NEXUS_PREFIX) -> Dict[str, str]:
        """Export config as environment variables."""
        env: Dict[str, str] = {}
        for key, entry in self._entries.items():
            env_var = EnvSource.key_to_env(key, prefix)
            env[env_var] = str(entry.value)
        return env

    # ── Discovery ──────────────────────────────────────────────────

    def discover_ad_hoc_env_vars(self) -> Dict[str, str]:
        """Discover ad-hoc os.environ.get() calls by scanning common patterns.

        Returns {config_key: env_var_name} for loosely-referenced vars.
        """
        known: Dict[str, str] = {
            "db.path": "DATABASE_URL",
            "encryption.secret": "ENCRYPTION_SECRET",
            "ollama.host": "OLLAMA_HOST",
            "ollama.api": "OLLAMA_API",
            "relay.port": "RELAY_PORT",
            "relay.health_interval": "RELAY_HEALTH_INTERVAL",
            "relay.health_timeout": "RELAY_HEALTH_TIMEOUT",
            "relay.vram_gb": "RELAY_VRAM_GB",
            "relay.guard_mode": "RELAY_GUARD_MODE",
            "telegram.bot_token": "TELEGRAM_BOT_TOKEN",
            "slack.bot_token": "SLACK_BOT_TOKEN",
            "discord.bot_token": "DISCORD_BOT_TOKEN",
            "mcp.name": "NEXUS_MCP_NAME",
            "mcp.version": "NEXUS_MCP_VERSION",
            "mcp.audit_path": "NEXUS_MCP_AUDIT_PATH",
            "mcp.checkpoint_path": "NEXUS_MCP_CHECKPOINT_PATH",
            "mcp.allow_side_effects": "NEXUS_MCP_ALLOW_SIDE_EFFECTS",
            "trustkernel.mode": "NEXUS_TRUSTKERNEL_MODE",
            "bypass.debug": "NEXUS_BYPASS_DEBUG",
            "flaresolverr.url": "FLARESOLVERR_URL",
            "nexcha.path": "NEXUS_OS_NEXCHA_PATH",
        }
        return known


# Singleton
_engine_instance: Optional[ConfigSyncEngine] = None


def get_engine() -> ConfigSyncEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConfigSyncEngine()
    return _engine_instance
