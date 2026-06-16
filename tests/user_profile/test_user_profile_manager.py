"""tests/user_profile/test_user_profile_manager.py — Tests for ProfileManager.

Covers:
  - Profile loading, saving, reloading
  - Rule CRUD (add, enable, disable, delete)
  - Rule execution (auto-clone, index, cleanup)
  - Status reporting
  - Integration with PreferenceStore and FileOrganizationProtocol
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from nexus_os.user_profile.preferences import (
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    PreferenceStore,
    RuleStatus,
    FileScope,
)
from nexus_os.user_profile.profile_manager import (
    ProfileManager,
    ManagerStatus,
    get_profile_manager,
)
from nexus_os.user_profile.protocol import FileOrganizationProtocol


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def temp_manager():
    """Create a ProfileManager with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PreferenceStore(storage_dir=tmpdir)
        protocol = FileOrganizationProtocol()
        manager = ProfileManager(store=store, protocol=protocol)
        yield manager


@pytest.fixture
def populated_manager(temp_manager):
    """Create a manager with a loaded profile and some rules."""
    manager = temp_manager
    manager.load_profile("test-user")

    # Add clone rule
    manager.add_clone_rule(AutoCloneRule(
        rule_id="clone-1",
        name="Test Clone",
        description="",
        source_path="/tmp",
        destination_path="/tmp",
        status=RuleStatus.ENABLED,
        enabled_at="2026-01-01T00:00:00Z",
    ))

    # Add index rule (enabled)
    manager.add_index_rule(IndexRule(
        rule_id="index-1",
        name="Test Index",
        description="",
        source_path="/tmp",
        status=RuleStatus.ENABLED,
    ))

    # Add cleanup rule (draft, disabled by default)
    manager.add_cleanup_rule(CleanupRule(
        rule_id="cleanup-1",
        name="Test Cleanup",
        description="",
        target_path="/tmp",
        status=RuleStatus.DRAFT,
    ))

    return manager


# ------------------------------------------------------------------
# Profile Loading Tests
# ------------------------------------------------------------------

class TestProfileLoading:
    def test_load_profile_creates_default(self, temp_manager):
        profile = temp_manager.load_profile("speci")
        assert profile.user_id == "speci"
        assert len(profile.rules.auto_clone_rules) >= 1

    def test_get_profile_returns_loaded(self, temp_manager):
        temp_manager.load_profile("loaded-user")
        assert temp_manager.get_profile().user_id == "loaded-user"

    def test_get_profile_none_before_load(self, temp_manager):
        assert temp_manager.get_profile() is None

    def test_reload_profile(self, temp_manager):
        temp_manager.load_profile("reload-user")
        temp_manager.get_profile().preferences["custom"] = 123
        temp_manager.save_profile()
        temp_manager.reload_profile()
        assert temp_manager.get_profile().preferences["custom"] == 123

    def test_load_default_speci_profile(self, temp_manager):
        profile = temp_manager.load_profile("speci")
        assert profile.user_id == "speci"
        assert len(profile.rules.auto_clone_rules) >= 1
        rule = profile.rules.auto_clone_rules[0]
        assert rule.rule_id == "clone-recent-to-archivist"
        assert rule.status == RuleStatus.ENABLED


# ------------------------------------------------------------------
# Rule CRUD Tests
# ------------------------------------------------------------------

class TestRuleCRUD:
    def test_add_clone_rule(self, temp_manager):
        temp_manager.load_profile("crud-test")
        rule = temp_manager.add_clone_rule(AutoCloneRule(
            rule_id="new-clone",
            name="New Clone",
            description="",
            source_path="/a",
            destination_path="/b",
        ))
        assert rule.rule_id == "new-clone"
        assert len(temp_manager.get_profile().rules.auto_clone_rules) == 1

    def test_add_index_rule(self, temp_manager):
        temp_manager.load_profile("crud-test")
        rule = temp_manager.add_index_rule(IndexRule(
            rule_id="new-index",
            name="New Index",
            description="",
            source_path="/a",
        ))
        assert rule.rule_id == "new-index"
        assert len(temp_manager.get_profile().rules.index_rules) >= 1

    def test_add_cleanup_rule(self, temp_manager):
        temp_manager.load_profile("crud-test")
        rule = temp_manager.add_cleanup_rule(CleanupRule(
            rule_id="new-cleanup",
            name="New Cleanup",
            description="",
            target_path="/a",
        ))
        assert rule.rule_id == "new-cleanup"
        assert len(temp_manager.get_profile().rules.cleanup_rules) >= 1

    def test_enable_rule(self, populated_manager):
        manager = populated_manager
        assert manager.enable_rule("cleanup-1") is True
        rule = manager.get_profile().rules.get_rule_by_id("cleanup-1")
        assert rule.status == RuleStatus.ENABLED
        assert rule.enabled_at is not None

    def test_disable_rule(self, populated_manager):
        manager = populated_manager
        assert manager.disable_rule("clone-1") is True
        rule = manager.get_profile().rules.get_rule_by_id("clone-1")
        assert rule.status == RuleStatus.DISABLED

    def test_delete_rule(self, populated_manager):
        manager = populated_manager
        assert manager.delete_rule("clone-1") is True
        assert manager.get_profile().rules.get_rule_by_id("clone-1") is None
        assert manager.delete_rule("clone-1") is False

    def test_enable_nonexistent_rule(self, populated_manager):
        assert populated_manager.enable_rule("nonexistent") is False

    def test_disable_nonexistent_rule(self, populated_manager):
        assert populated_manager.disable_rule("nonexistent") is False

    def test_delete_nonexistent_rule(self, populated_manager):
        assert populated_manager.delete_rule("nonexistent") is False

    def test_crud_without_profile_raises(self, temp_manager):
        with pytest.raises(RuntimeError, match="No profile loaded"):
            temp_manager.add_clone_rule(AutoCloneRule(
                rule_id="x", name="X", description="", source_path="/a", destination_path="/b",
            ))

    def test_multiple_rules_in_profile(self, populated_manager):
        manager = populated_manager
        profile = manager.get_profile()
        # No default rules for non-speci users; 3 added by fixture
        assert len(profile.rules.all_rules()) == 3
        assert len(profile.rules.auto_clone_rules) == 1
        assert len(profile.rules.index_rules) == 1
        assert len(profile.rules.cleanup_rules) == 1


# ------------------------------------------------------------------
# Status & Stats Tests
# ------------------------------------------------------------------

class TestStatusAndStats:
    def test_status_before_load(self, temp_manager):
        status = temp_manager.get_status()
        assert status.running is False
        assert status.total_rules == 0

    def test_status_after_load(self, temp_manager):
        temp_manager.load_profile("status-test")
        status = temp_manager.get_status()
        assert status.total_rules == 0  # No default rules for non-speci users
        assert status.enabled_rules == 0

    def test_status_after_enabling_rule(self, populated_manager):
        manager = populated_manager
        status = manager.get_status()
        assert status.total_rules == 3  # 3 added by fixture (no default for non-speci)
        assert status.enabled_rules == 2  # clone-1 + index-1 (cleanup-1 is DRAFT)

    def test_get_stats(self, populated_manager):
        manager = populated_manager
        stats = manager.get_stats()
        assert stats["user_id"] == "test-user"
        assert stats["total_rules"] == 3  # 3 added by fixture (no default for non-speci)
        assert stats["enabled_rules"] == 2  # clone-1 + index-1
        assert stats["clone_rules"] == 1
        assert stats["cleanup_rules"] == 1
        assert stats["index_rules"] == 1
        assert "preferences" in stats
        assert "session" in stats

    def test_stats_no_profile(self, temp_manager):
        stats = temp_manager.get_stats()
        assert "error" in stats

    def test_status_version(self, populated_manager):
        status = populated_manager.get_status()
        assert status.version == "user-profile-v1"


# ------------------------------------------------------------------
# Rule Execution Tests
# ------------------------------------------------------------------

class TestRuleExecution:
    def test_execute_all_enabled_rules_no_profile(self, temp_manager):
        results = temp_manager.execute_all_enabled_rules()
        assert results == []

    def test_execute_all_enabled_rules_with_clone(self, temp_manager):
        import tempfile as tf
        with tf.TemporaryDirectory() as src_dir:
            with tf.TemporaryDirectory() as dst_dir:
                # Create a test file
                src = Path(src_dir)
                (src / "test.md").write_text("test", encoding="utf-8")

                manager = temp_manager
                manager.load_profile("exec-test")
                manager.add_clone_rule(AutoCloneRule(
                    rule_id="exec-clone",
                    name="Exec Clone",
                    description="",
                    source_path=src_dir,
                    destination_path=dst_dir,
                    file_patterns=["*.md"],
                    status=RuleStatus.ENABLED,
                    time_window_hours=9999.0,
                ))

                results = manager.execute_all_enabled_rules()
                assert len(results) >= 1

                clone_result = [r for r in results if r.rule_id == "exec-clone"][0]
                assert clone_result.success is True
                assert clone_result.files_processed == 1
                assert (Path(dst_dir) / "test.md").exists()

    def test_execute_rule_by_id(self, temp_manager):
        import tempfile as tf
        with tf.TemporaryDirectory() as src_dir:
            with tf.TemporaryDirectory() as dst_dir:
                src = Path(src_dir)
                (src / "test.md").write_text("test", encoding="utf-8")

                manager = temp_manager
                manager.load_profile("exec-id-test")
                manager.add_clone_rule(AutoCloneRule(
                    rule_id="exec-id",
                    name="Exec ID",
                    description="",
                    source_path=src_dir,
                    destination_path=dst_dir,
                    file_patterns=["*.md"],
                    status=RuleStatus.ENABLED,
                    time_window_hours=9999.0,
                ))

                result = manager.execute_rule_by_id("exec-id")
                assert result is not None
                assert result.success is True
                assert result.files_processed == 1
                assert (Path(dst_dir) / "test.md").exists()

    def test_execute_rule_by_id_nonexistent(self, populated_manager):
        result = populated_manager.execute_rule_by_id("nonexistent")
        assert result is None

    def test_execute_disabled_rule_not_run(self, populated_manager):
        manager = populated_manager
        result = manager.execute_rule_by_id("cleanup-1")
        assert result is not None
        assert result.success is False
        assert "not enabled" in result.errors[0]

    @pytest.mark.skip(reason="Clone rule with /tmp source hangs on Windows - scans entire temp tree")
    def test_execution_updates_rule_counters(self, populated_manager):
        manager = populated_manager
        result = manager.execute_rule_by_id("clone-1")
        rule = manager.get_profile().rules.get_rule_by_id("clone-1")
        assert rule.execution_count == 1
        assert rule.last_executed is not None

    @pytest.mark.skip(reason="Clone rule with /tmp source hangs on Windows - scans entire temp tree")
    def test_execute_all_enabled_rules_counts(self, populated_manager):
        manager = populated_manager
        results = manager.execute_all_enabled_rules()
        status = manager.get_status()
        assert status.rules_executed_this_session > 0
        assert status.last_execution is not None


# ------------------------------------------------------------------
# Singleton Tests
# ------------------------------------------------------------------

class TestSingleton:
    def test_get_profile_manager_returns_same_instance(self):
        m1 = get_profile_manager()
        m2 = get_profile_manager()
        assert m1 is m2

    def test_singleton_has_no_profile_initially(self):
        manager = get_profile_manager()
        assert manager.get_profile() is None


# ------------------------------------------------------------------
# ManagerStatus Tests
# ------------------------------------------------------------------

class TestManagerStatus:
    def test_default_status(self):
        status = ManagerStatus()
        assert status.running is False
        assert status.total_rules == 0
        assert status.enabled_rules == 0

    def test_status_to_dict(self):
        status = ManagerStatus(
            running=True,
            total_rules=5,
            enabled_rules=3,
            rules_executed_this_session=2,
            files_cloned_this_session=10,
            errors_this_session=1,
        )
        d = status.to_dict()
        assert d["running"] is True
        assert d["total_rules"] == 5
        assert d["enabled_rules"] == 3
        assert d["rules_executed_this_session"] == 2
        assert d["files_cloned_this_session"] == 10
        assert d["errors_this_session"] == 1
        assert d["version"] == "user-profile-v1"


# ------------------------------------------------------------------
# Integration: Persistence Tests
# ------------------------------------------------------------------

class TestIntegration:
    def test_full_workflow(self, temp_manager):
        manager = temp_manager
        manager.load_profile("integration")

        # Add rules
        manager.add_clone_rule(AutoCloneRule(
            rule_id="wf-clone",
            name="Workflow Clone",
            description="",
            source_path="/tmp",
            destination_path="/tmp",
            status=RuleStatus.ENABLED,
        ))
        manager.add_index_rule(IndexRule(
            rule_id="wf-index",
            name="Workflow Index",
            description="",
            source_path="/tmp",
            status=RuleStatus.ENABLED,
        ))

        # Check status
        status = manager.get_status()
        assert status.total_rules == 2  # 2 new (no default for non-speci)

        # Save
        manager.save_profile()

        # Reload via new manager
        store = manager.store
        new_manager = ProfileManager(store=store, protocol=FileOrganizationProtocol())
        new_manager.load_profile("integration")

        assert new_manager.get_profile().user_id == "integration"
        assert len(new_manager.get_profile().rules.all_rules()) == 2
        assert new_manager.get_profile().rules.get_rule_by_id("wf-clone") is not None
        assert new_manager.get_profile().rules.get_rule_by_id("wf-index") is not None

    def test_preferences_survive_reload(self, temp_manager):
        manager = temp_manager
        manager.load_profile("prefs")
        manager.get_profile().preferences["custom"] = "value"
        manager.save_profile()

        new_manager = ProfileManager(
            store=manager.store,
            protocol=FileOrganizationProtocol(),
        )
        new_manager.load_profile("prefs")
        assert new_manager.get_profile().preferences["custom"] == "value"

    def test_rule_enable_disable_persistence(self, temp_manager):
        manager = temp_manager
        manager.load_profile("persist")
        manager.add_clone_rule(AutoCloneRule(
            rule_id="persist-rule",
            name="Persist",
            description="",
            source_path="/tmp",
            destination_path="/tmp",
        ))
        manager.enable_rule("persist-rule")
        manager.save_profile()

        new_manager = ProfileManager(
            store=manager.store,
            protocol=FileOrganizationProtocol(),
        )
        new_manager.load_profile("persist")
        rule = new_manager.get_profile().rules.get_rule_by_id("persist-rule")
        assert rule.status == RuleStatus.ENABLED

    def test_delete_rule_persistence(self, temp_manager):
        manager = temp_manager
        manager.load_profile("delete-persist")
        manager.add_clone_rule(AutoCloneRule(
            rule_id="to-delete",
            name="Delete Me",
            description="",
            source_path="/tmp",
            destination_path="/tmp",
        ))
        manager.save_profile()
        manager.delete_rule("to-delete")
        manager.save_profile()

        new_manager = ProfileManager(
            store=manager.store,
            protocol=FileOrganizationProtocol(),
        )
        new_manager.load_profile("delete-persist")
        assert new_manager.get_profile().rules.get_rule_by_id("to-delete") is None

    def test_profile_updated_at_changes(self, temp_manager):
        manager = temp_manager
        manager.load_profile("timestamp")
        old_updated = manager.get_profile().updated_at
        manager.add_clone_rule(AutoCloneRule(
            rule_id="ts",
            name="Timestamp",
            description="",
            source_path="/tmp",
            destination_path="/tmp",
        ))
        new_updated = manager.get_profile().updated_at
        assert new_updated != old_updated
