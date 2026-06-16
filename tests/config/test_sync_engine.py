"""tests/config/test_sync_engine.py — ConfigSyncEngine tests"""

import json
import pytest
from dataclasses import dataclass, field
from nexus_os.config.sync_engine import (
    ConfigSyncEngine,
    ConfigSource,
    ConfigEntry,
    ConfigDiff,
    SyncReport,
    EnvSource,
    JsonSource,
    DataclassSource,
    SourcePriority,
    get_engine,
)


@dataclass
class TestAppConfig:
    name: str = "test-app"
    version: str = "1.0.0"
    debug: bool = False
    hosts: list = field(default_factory=lambda: ["localhost"])
    port: int = 8080


@pytest.fixture
def engine():
    return ConfigSyncEngine()


class TestConfigSyncEngine:
    def test_initial_state(self, engine):
        assert engine._entries == {}
        assert len(engine._sources) == 0

    def test_register_and_load_dataclass(self, engine):
        cfg = TestAppConfig()
        source = DataclassSource(cfg, priority=SourcePriority.DEFAULT)
        engine.register_source(source)
        report = engine.load()
        assert report.sources_loaded >= 1
        assert engine.get("testappconfig.name") == "test-app"
        assert engine.get("testappconfig.version") == "1.0.0"
        assert engine.get("testappconfig.port") == 8080

    def test_register_and_load_json(self, engine, tmp_path):
        data = {"name": "json-app", "debug": True}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(data))
        source = JsonSource(str(f), priority=SourcePriority.FILE)
        engine.register_source(source)
        engine.load()
        assert engine.get("name") == "json-app"
        assert engine.get("debug") is True

    def test_env_source_auto_discover(self, engine, monkeypatch):
        monkeypatch.setenv("NEXUS_MODE", "production")
        monkeypatch.setenv("NEXUS_PORT", "9090")
        source = EnvSource("NEXUS_", priority=SourcePriority.ENV)
        engine.register_source(source)
        engine.load()
        assert engine.get("mode") == "production"
        assert engine.get("port") == 9090

    def test_env_source_direct_binding(self, engine, monkeypatch):
        monkeypatch.setenv("MY_SPECIAL_VAR", "direct_val")
        source = EnvSource("NEXUS_", priority=SourcePriority.ENV)
        source.register_binding("special.key", "MY_SPECIAL_VAR")
        engine.register_source(source)
        engine.load()
        assert engine.get("special.key") == "direct_val"

    def test_priority_overrides(self, engine):
        low = DataclassSource(TestAppConfig(), priority=SourcePriority.DEFAULT)
        high = DataclassSource(TestAppConfig(port=9999, debug=True), priority=SourcePriority.CLI)
        engine.register_source(low)
        engine.register_source(high)
        engine.load()
        assert engine.get("testappconfig.port") == 9999
        assert engine.get("testappconfig.debug") is True

    def test_get_missing_key(self, engine):
        engine.load()
        assert engine.get("nonexistent") is None

    def test_get_with_default(self, engine):
        engine.load()
        assert engine.get("nonexistent", "fallback") == "fallback"

    def test_has_key(self, engine):
        engine.set("custom_key", "custom_value")
        assert engine.has("custom_key") is True
        assert engine.has("nonexistent") is False

    def test_keys(self, engine):
        engine.set("k1", "v1")
        engine.set("k2", "v2")
        assert set(engine.keys()) == {"k1", "k2"}

    def test_all_entries(self, engine):
        engine.set("key1", "val1")
        entries = engine.all_entries()
        assert "key1" in entries
        assert entries["key1"].value == "val1"

    def test_set_and_get(self, engine):
        engine.set("custom_key", "custom_value")
        assert engine.get("custom_key") == "custom_value"

    def test_set_overrides_existing(self, engine):
        cfg = TestAppConfig()
        engine.register_source(DataclassSource(cfg, priority=SourcePriority.DEFAULT))
        engine.load()
        engine.set("testappconfig.port", 3000)
        assert engine.get("testappconfig.port") == 3000

    def test_get_entry(self, engine):
        engine.set("test.key", 42, source="cli")
        entry = engine.get_entry("test.key")
        assert entry is not None
        assert entry.value == 42
        assert entry.source == "cli"

    def test_filter_by_source(self, engine):
        engine.set("cli_key", "cli_val", source="cli")
        engine.set("env_key", "env_val", source="env")
        cli = engine.filter_by_source("cli")
        assert "cli_key" in cli
        assert "env_key" not in cli

    def test_filter_by_prefix(self, engine):
        engine.register_source(DataclassSource(TestAppConfig(), priority=SourcePriority.DEFAULT))
        engine.load()
        filtered = engine.filter_by_prefix("testappconfig")
        assert len(filtered) >= 4
        assert "testappconfig.name" in filtered

    def test_list_sources(self, engine):
        engine.register_source(EnvSource("NEXUS_"))
        sources = engine.list_sources()
        assert len(sources) == 1

    def test_to_json(self, engine):
        engine.set("key1", "val1")
        j = engine.to_json()
        parsed = json.loads(j)
        assert parsed["key1"]["value"] == "val1"

    def test_to_env(self, engine):
        engine.set("server.name", "myserver")
        env = engine.to_env("NEXUS_")
        assert "NEXUS_SERVER_NAME" in env
        assert env["NEXUS_SERVER_NAME"] == "myserver"

    def test_diff_between_engines(self):
        e1 = ConfigSyncEngine()
        e2 = ConfigSyncEngine()
        e1.set("added_key", "val")
        e2.set("removed_key", "old_val")
        e1.set("changed_key", "new_val")
        e2.set("changed_key", "old_val")
        e2.set("same_key", "same")

        diff = e1.diff(e2)
        assert any(k == "added_key" for k, _, _ in diff.added)
        assert any(k == "removed_key" for k, _, _ in diff.removed)
        assert any(k == "changed_key" for k, _, _, _ in diff.changed)
        assert diff.unchanged >= 0


class TestJsonSource:
    def test_save_and_reload(self, engine, tmp_path):
        f = tmp_path / "saved.json"
        source = JsonSource(str(f), priority=SourcePriority.FILE)
        engine.register_source(source)
        engine.set("name", "test")
        engine.set("value", 42)
        report = engine.save()  # saves to JsonSource
        assert report.sources_loaded >= 1

        # Verify file was written
        saved = json.loads(f.read_text())
        assert saved["name"] == "test"
        assert saved["value"] == 42

    def test_json_source_malformed(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}")
        source = JsonSource(str(f), priority=SourcePriority.FILE)
        entries = source.load()
        assert entries == {}

    def test_json_source_nonexistent(self, tmp_path):
        source = JsonSource(str(tmp_path / "nonexistent.json"))
        entries = source.load()
        assert entries == {}


class TestEnvSource:
    def test_key_to_env(self):
        result = EnvSource.key_to_env("mcp.server_name", "NEXUS_")
        assert result == "NEXUS_MCP_SERVER_NAME"

    def test_env_to_key(self):
        result = EnvSource._env_to_key("NEXUS_MCP_SERVER_NAME")
        assert result == "mcp.server.name"


class TestDataclassSource:
    def test_non_dataclass(self):
        class NotADataclass:
            pass

        source = DataclassSource(NotADataclass(), priority=SourcePriority.DEFAULT)
        entries = source.load()
        assert entries == {}


class TestConfigEntry:
    def test_to_dict(self):
        entry = ConfigEntry(key="k", value="v", source="env", source_name="MY_VAR")
        d = entry.to_dict()
        assert d["key"] == "k"
        assert d["value"] == "v"
        assert d["source"] == "env"

    def test_defaults(self):
        entry = ConfigEntry(key="k", value="v")
        assert entry.source == "default"
        assert entry.source_name == ""
        assert entry.value_type == ""


class TestConfigDiff:
    def test_has_changes_false(self):
        diff = ConfigDiff()
        assert diff.has_changes is False

    def test_has_changes_true(self):
        diff = ConfigDiff(added=[("k", "v", "cli")])
        assert diff.has_changes is True

    def test_to_dict(self):
        diff = ConfigDiff(added=[("k", "v", "cli")])
        d = diff.to_dict()
        assert d["has_changes"] is True


class TestSyncReport:
    def test_to_dict(self):
        report = SyncReport(
            timestamp=1000.0,
            sources_loaded=2,
            entries_total=10,
            conflicts_resolved=1,
            diff=ConfigDiff(),
        )
        d = report.to_dict()
        assert d["sources_loaded"] == 2
        assert d["diff"]["has_changes"] is False


class TestSingleton:
    def test_singleton(self):
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2


class TestSyncFlow:
    def test_sync_returns_report(self, engine):
        report = engine.sync()
        assert isinstance(report, SyncReport)
        assert report.sources_loaded >= 0

    def test_sync_with_changes(self, engine):
        engine.set("key", "val")
        report = engine.sync()
        assert report.diff.has_changes


class TestDiscoverEnvVars:
    def test_engine_discover(self, engine):
        discovered = engine.discover_ad_hoc_env_vars()
        assert isinstance(discovered, dict)
        assert len(discovered) >= 20

    def test_engine_discover_keys(self, engine):
        discovered = engine.discover_ad_hoc_env_vars()
        assert "db.path" in discovered
        assert discovered["db.path"] == "DATABASE_URL"
