"""tests/user_profile/test_user_profile_preferences.py — Tests for NEXUS OS User Profile System.

Covers:
  - UserProfile creation, serialization, deserialization
  - PreferenceStore load/save/list/delete
  - AutoCloneRule, CleanupRule, IndexRule data models
  - ProfileRuleSet operations (all_rules, get_enabled, get_by_id)
  - Default profile creation for "speci"
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from nexus_os.user_profile.preferences import (
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    ProfileRuleSet,
    PreferenceStore,
    RuleStatus,
    FileScope,
    UserProfile,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def temp_store():
    """Create a PreferenceStore in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PreferenceStore(storage_dir=tmpdir)
        yield store


@pytest.fixture
def sample_clone_rule():
    return AutoCloneRule(
        rule_id="clone-test-1",
        name="Test Clone Rule",
        description="Clone test files",
        source_path="/tmp/source",
        destination_path="/tmp/dest",
        file_patterns=["*.md"],
        exclude_patterns=["*.git*"],
        time_window_hours=24.0,
        file_scope=FileScope.RECENT_ONLY,
        preserve_structure=True,
        create_manifest=True,
        status=RuleStatus.ENABLED,
        enabled_at="2026-01-01T00:00:00Z",
        tags=["test"],
    )


@pytest.fixture
def sample_cleanup_rule():
    return CleanupRule(
        rule_id="cleanup-test-1",
        name="Test Cleanup Rule",
        description="Clean old temp files",
        target_path="/tmp/old",
        file_patterns=["*.tmp"],
        min_age_hours=168.0,
        action="delete",
        require_backup=True,
        max_delete_count=50,
        status=RuleStatus.DRAFT,
    )


@pytest.fixture
def sample_index_rule():
    return IndexRule(
        rule_id="index-test-1",
        name="Test Index Rule",
        description="Index research papers",
        source_path="/tmp/papers",
        file_patterns=["*.md"],
        time_window_hours=48.0,
        archivist_stage="import",
        status=RuleStatus.ENABLED,
    )


# ------------------------------------------------------------------
# UserProfile Tests
# ------------------------------------------------------------------

class TestUserProfile:
    def test_default_profile_creation(self):
        profile = UserProfile()
        assert profile.user_id == "speci"
        assert profile.display_name == "Speci"
        assert profile.version == 1
        assert isinstance(profile.preferences, dict)
        assert profile.preferences["tidyness_auto_clone_enabled"] is True
        assert profile.preferences["tidyness_cleanup_enabled"] is False

    def test_profile_to_dict(self):
        profile = UserProfile(user_id="test-user")
        d = profile.to_dict()
        assert d["user_id"] == "test-user"
        assert "preferences" in d
        assert "rules" in d
        assert "version" in d

    def test_profile_from_dict(self):
        profile = UserProfile(user_id="test-user")
        d = profile.to_dict()
        restored = UserProfile.from_dict(d)
        assert restored.user_id == "test-user"
        assert restored.version == 1
        assert restored.preferences["tidyness_auto_clone_enabled"] is True

    def test_profile_touch_updates_timestamp(self):
        profile = UserProfile()
        old_updated = profile.updated_at
        profile.touch()
        assert profile.updated_at != old_updated

    def test_default_profile_has_clone_rule(self, temp_store):
        profile = temp_store.load_or_create("speci")
        assert len(profile.rules.auto_clone_rules) >= 1
        rule = profile.rules.auto_clone_rules[0]
        assert rule.rule_id == "clone-recent-to-archivist"
        assert rule.status == RuleStatus.ENABLED

    def test_profile_with_custom_preferences(self):
        profile = UserProfile(
            user_id="custom",
            preferences={"default_clone_window_hours": 72.0, "custom_key": "value"},
        )
        assert profile.preferences["default_clone_window_hours"] == 72.0
        assert profile.preferences["custom_key"] == "value"


# ------------------------------------------------------------------
# PreferenceStore Tests
# ------------------------------------------------------------------

class TestPreferenceStore:
    def test_save_and_load(self, temp_store):
        profile = UserProfile(user_id="test-save")
        temp_store.save(profile)
        loaded = temp_store.load("test-save")
        assert loaded is not None
        assert loaded.user_id == "test-save"
        assert loaded.display_name == "Speci"

    def test_load_nonexistent_returns_none(self, temp_store):
        loaded = temp_store.load("nonexistent")
        assert loaded is None

    def test_load_or_create_creates_default(self, temp_store):
        profile = temp_store.load_or_create("speci")
        assert profile.user_id == "speci"
        assert len(profile.rules.auto_clone_rules) >= 1

    def test_list_users(self, temp_store):
        temp_store.save(UserProfile(user_id="user-a"))
        temp_store.save(UserProfile(user_id="user-b"))
        users = temp_store.list_users()
        assert "user-a" in users
        assert "user-b" in users

    def test_delete_user(self, temp_store):
        temp_store.save(UserProfile(user_id="to-delete"))
        assert temp_store.delete("to-delete") is True
        assert temp_store.load("to-delete") is None
        assert temp_store.delete("nonexistent") is False

    def test_persistence(self, temp_store):
        profile = UserProfile(user_id="persist-test")
        profile.preferences["custom"] = 123
        temp_store.save(profile)
        # Simulate reload (new store instance, same dir)
        store2 = PreferenceStore(storage_dir=temp_store.storage_dir)
        loaded = store2.load("persist-test")
        assert loaded.preferences["custom"] == 123

    def test_default_clone_rule_destination(self, temp_store):
        profile = temp_store.load_or_create("speci")
        rule = profile.rules.auto_clone_rules[0]
        assert "ARCHIVIST" in rule.destination_path
        assert "NEXUS_latest" in rule.destination_path

    def test_json_file_created(self, temp_store):
        temp_store.save(UserProfile(user_id="file-test"))
        path = Path(temp_store.storage_dir) / "file-test.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["user_id"] == "file-test"


# ------------------------------------------------------------------
# Rule Data Model Tests
# ------------------------------------------------------------------

class TestAutoCloneRule:
    def test_rule_creation(self, sample_clone_rule):
        assert sample_clone_rule.rule_id == "clone-test-1"
        assert sample_clone_rule.status == RuleStatus.ENABLED
        assert sample_clone_rule.file_scope == FileScope.RECENT_ONLY

    def test_rule_to_dict(self, sample_clone_rule):
        d = sample_clone_rule.to_dict()
        assert d["rule_id"] == "clone-test-1"
        assert d["status"] == "enabled"
        assert d["file_scope"] == "recent_only"

    def test_rule_from_dict(self, sample_clone_rule):
        d = sample_clone_rule.to_dict()
        restored = AutoCloneRule.from_dict(d)
        assert restored.rule_id == "clone-test-1"
        assert restored.status == RuleStatus.ENABLED
        assert restored.file_scope == FileScope.RECENT_ONLY

    def test_rule_timestamps(self, sample_clone_rule):
        assert sample_clone_rule.created_at is not None
        assert sample_clone_rule.enabled_at is not None  # sample_clone_rule is ENABLED


class TestCleanupRule:
    def test_safety_defaults(self, sample_cleanup_rule):
        assert sample_cleanup_rule.require_backup is True
        assert sample_cleanup_rule.max_delete_count == 50
        assert sample_cleanup_rule.status == RuleStatus.DRAFT

    def test_to_dict_from_dict(self, sample_cleanup_rule):
        d = sample_cleanup_rule.to_dict()
        restored = CleanupRule.from_dict(d)
        assert restored.rule_id == "cleanup-test-1"
        assert restored.require_backup is True


class TestIndexRule:
    def test_advisory_stage(self, sample_index_rule):
        assert sample_index_rule.archivist_stage == "import"
        assert sample_index_rule.status == RuleStatus.ENABLED

    def test_to_dict_from_dict(self, sample_index_rule):
        d = sample_index_rule.to_dict()
        restored = IndexRule.from_dict(d)
        assert restored.rule_id == "index-test-1"
        assert restored.archivist_stage == "import"


# ------------------------------------------------------------------
# ProfileRuleSet Tests
# ------------------------------------------------------------------

class TestProfileRuleSet:
    def test_empty_ruleset(self):
        rs = ProfileRuleSet()
        assert rs.all_rules() == []
        assert rs.get_enabled_clone_rules() == []

    def test_add_and_retrieve(self, sample_clone_rule, sample_cleanup_rule, sample_index_rule):
        rs = ProfileRuleSet()
        rs.auto_clone_rules.append(sample_clone_rule)
        rs.cleanup_rules.append(sample_cleanup_rule)
        rs.index_rules.append(sample_index_rule)

        assert len(rs.all_rules()) == 3
        assert len(rs.get_enabled_clone_rules()) == 1
        assert len(rs.get_enabled_cleanup_rules()) == 0  # DRAFT
        assert len(rs.get_enabled_index_rules()) == 1

    def test_get_rule_by_id(self, sample_clone_rule, sample_cleanup_rule):
        rs = ProfileRuleSet()
        rs.auto_clone_rules.append(sample_clone_rule)
        rs.cleanup_rules.append(sample_cleanup_rule)

        found = rs.get_rule_by_id("clone-test-1")
        assert found is not None
        assert found.rule_id == "clone-test-1"

        found2 = rs.get_rule_by_id("cleanup-test-1")
        assert found2 is not None
        assert found2.rule_id == "cleanup-test-1"

        not_found = rs.get_rule_by_id("nonexistent")
        assert not_found is None

    def test_serialization_roundtrip(self, sample_clone_rule, sample_cleanup_rule, sample_index_rule):
        rs = ProfileRuleSet()
        rs.auto_clone_rules.append(sample_clone_rule)
        rs.cleanup_rules.append(sample_cleanup_rule)
        rs.index_rules.append(sample_index_rule)

        d = rs.to_dict()
        restored = ProfileRuleSet.from_dict(d)

        assert len(restored.auto_clone_rules) == 1
        assert len(restored.cleanup_rules) == 1
        assert len(restored.index_rules) == 1
        assert restored.auto_clone_rules[0].status == RuleStatus.ENABLED
        assert restored.cleanup_rules[0].status == RuleStatus.DRAFT

    def test_to_dict_with_no_rules(self):
        rs = ProfileRuleSet()
        d = rs.to_dict()
        assert d["auto_clone_rules"] == []
        assert d["cleanup_rules"] == []
        assert d["index_rules"] == []


# ------------------------------------------------------------------
# Integration: Profile + Store + Rules
# ------------------------------------------------------------------

class TestProfileIntegration:
    def test_full_profile_workflow(self, temp_store):
        # Create profile
        profile = UserProfile(user_id="integration-test")
        profile.rules.auto_clone_rules.append(AutoCloneRule(
            rule_id="custom-clone",
            name="Custom Clone",
            description="Test",
            source_path="/src",
            destination_path="/dst",
            status=RuleStatus.ENABLED,
        ))
        temp_store.save(profile)

        # Reload and verify
        loaded = temp_store.load("integration-test")
        assert loaded.rules.auto_clone_rules[0].rule_id == "custom-clone"
        assert loaded.rules.auto_clone_rules[0].status == RuleStatus.ENABLED

        # Modify and save
        loaded.rules.auto_clone_rules[0].status = RuleStatus.DISABLED
        temp_store.save(loaded)

        # Reload and verify modification
        loaded2 = temp_store.load("integration-test")
        assert loaded2.rules.auto_clone_rules[0].status == RuleStatus.DISABLED

    def test_multiple_rules_same_id(self, temp_store):
        profile = UserProfile(user_id="multi-rule")
        profile.rules.auto_clone_rules.append(AutoCloneRule(
            rule_id="same-id", name="Clone", description="", source_path="/s", destination_path="/d",
        ))
        profile.rules.cleanup_rules.append(CleanupRule(
            rule_id="same-id", name="Cleanup", description="", target_path="/t",
        ))

        # get_rule_by_id returns the first match (clone rule)
        found = profile.rules.get_rule_by_id("same-id")
        assert isinstance(found, AutoCloneRule)

    def test_profile_preferences_survive_roundtrip(self, temp_store):
        profile = UserProfile(user_id="prefs-test")
        profile.preferences["custom_setting"] = True
        profile.preferences["another_key"] = [1, 2, 3]
        temp_store.save(profile)

        loaded = temp_store.load("prefs-test")
        assert loaded.preferences["custom_setting"] is True
        assert loaded.preferences["another_key"] == [1, 2, 3]

    def test_default_speci_profile_has_archivist_rule(self, temp_store):
        profile = temp_store.load_or_create("speci")
        assert profile.user_id == "speci"
        assert len(profile.rules.auto_clone_rules) >= 1

        rule = profile.rules.auto_clone_rules[0]
        assert rule.name == "Clone Recent NEXUS Files to ARCHIVIST"
        assert rule.status == RuleStatus.ENABLED
        assert "ARCHIVIST" in rule.destination_path
        assert "NEXUS_latest" in rule.destination_path
        assert rule.preserve_structure is True
        assert rule.create_manifest is True
        assert rule.time_window_hours == 48.0
        assert "*.git*" in rule.exclude_patterns
        assert "*__pycache__*" in rule.exclude_patterns

    def test_profile_version_field(self, temp_store):
        profile = UserProfile(user_id="version-test")
        assert profile.version == 1
        temp_store.save(profile)
        loaded = temp_store.load("version-test")
        assert loaded.version == 1
