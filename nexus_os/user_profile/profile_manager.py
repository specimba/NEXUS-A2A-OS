"""nexus_os/user_profile/profile_manager.py — User Profile Manager for NEXUS OS.

The ProfileManager is the central integration layer for the User Profile Preference System.
It:
  - Loads/creates user profiles on startup
  - Periodically executes enabled tidyness rules (clone, cleanup, index)
  - Integrates with NEXUSCLAW worklog for audit logging
  - Integrates with ARCHIVIST for index rule processing
  - Provides a governance-safe API: rules are enabled by user, not auto-enabled

The manager runs as part of the NEXUSCLAW runner heartbeat cycle or as a standalone
background task. It is lightweight and designed for 24/7 operation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nexus_os.user_profile.preferences import (
    UserProfile,
    PreferenceStore,
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    ProfileRuleSet,
    RuleStatus,
)
from nexus_os.user_profile.protocol import (
    FileOrganizationProtocol,
    RuleExecutionResult,
)
from nexus_os.nexusclaw.worklog import WorklogSystem

logger = logging.getLogger("nexusclaw.user_profile.manager")


@dataclass
class ManagerStatus:
    """Current status of the ProfileManager."""
    running: bool = False
    last_execution: Optional[str] = None
    total_rules: int = 0
    enabled_rules: int = 0
    rules_executed_this_session: int = 0
    files_cloned_this_session: int = 0
    errors_this_session: int = 0
    version: str = "user-profile-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "last_execution": self.last_execution,
            "total_rules": self.total_rules,
            "enabled_rules": self.enabled_rules,
            "rules_executed_this_session": self.rules_executed_this_session,
            "files_cloned_this_session": self.files_cloned_this_session,
            "errors_this_session": self.errors_this_session,
            "version": self.version,
        }


class ProfileManager:
    """Central manager for user profiles and tidyness rule execution.

    Usage:
        manager = ProfileManager()
        manager.load_profile("speci")  # Loads or creates default profile
        manager.execute_all_enabled_rules()  # Run all enabled rules

    Integration with NEXUSCLAW runner:
        manager = ProfileManager()
        manager.load_profile("speci")
        # In runner heartbeat, call manager.execute_all_enabled_rules() periodically
    """

    def __init__(
        self,
        store: Optional[PreferenceStore] = None,
        protocol: Optional[FileOrganizationProtocol] = None,
        worklog: Optional[WorklogSystem] = None,
    ) -> None:
        self.store = store or PreferenceStore()
        self.protocol = protocol or FileOrganizationProtocol(worklog=worklog)
        self.worklog = worklog or WorklogSystem()
        self._profile: Optional[UserProfile] = None
        self._status = ManagerStatus()

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def load_profile(self, user_id: str = "speci") -> UserProfile:
        """Load or create a user profile."""
        self._profile = self.store.load_or_create(user_id)
        self._update_status()
        logger.info("Loaded profile for user '%s' with %d rules", user_id,
                    len(self._profile.rules.all_rules()))
        return self._profile

    def get_profile(self) -> Optional[UserProfile]:
        """Get the currently loaded profile."""
        return self._profile

    def save_profile(self) -> None:
        """Save the current profile to disk."""
        if self._profile:
            self.store.save(self._profile)
            logger.info("Saved profile for user '%s'", self._profile.user_id)

    def reload_profile(self) -> UserProfile:
        """Reload the current profile from disk."""
        if not self._profile:
            return self.load_profile()
        self._profile = self.store.load(self._profile.user_id)
        if self._profile is None:
            self._profile = self.store.load_or_create("speci")
        self._update_status()
        return self._profile

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    def add_clone_rule(self, rule: AutoCloneRule) -> AutoCloneRule:
        """Add a new auto-clone rule to the profile."""
        if not self._profile:
            raise RuntimeError("No profile loaded. Call load_profile() first.")
        self._profile.rules.auto_clone_rules.append(rule)
        self._profile.touch()
        self.save_profile()
        self._update_status()
        return rule

    def add_cleanup_rule(self, rule: CleanupRule) -> CleanupRule:
        """Add a new cleanup rule to the profile."""
        if not self._profile:
            raise RuntimeError("No profile loaded. Call load_profile() first.")
        self._profile.rules.cleanup_rules.append(rule)
        self._profile.touch()
        self.save_profile()
        self._update_status()
        return rule

    def add_index_rule(self, rule: IndexRule) -> IndexRule:
        """Add a new index rule to the profile."""
        if not self._profile:
            raise RuntimeError("No profile loaded. Call load_profile() first.")
        self._profile.rules.index_rules.append(rule)
        self._profile.touch()
        self.save_profile()
        self._update_status()
        return rule

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID. Returns True if found and enabled."""
        if not self._profile:
            return False
        rule = self._profile.rules.get_rule_by_id(rule_id)
        if rule is None:
            return False
        rule.status = RuleStatus.ENABLED
        rule.enabled_at = datetime.now(timezone.utc).isoformat()
        self._profile.touch()
        self.save_profile()
        self._update_status()
        logger.info("Enabled rule '%s' (%s)", rule_id, rule.name)
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID. Returns True if found and disabled."""
        if not self._profile:
            return False
        rule = self._profile.rules.get_rule_by_id(rule_id)
        if rule is None:
            return False
        rule.status = RuleStatus.DISABLED
        self._profile.touch()
        self.save_profile()
        self._update_status()
        logger.info("Disabled rule '%s' (%s)", rule_id, rule.name)
        return True

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by ID. Returns True if found and deleted."""
        if not self._profile:
            return False
        for category in ["auto_clone_rules", "cleanup_rules", "index_rules"]:
            rules = getattr(self._profile.rules, category)
            for i, rule in enumerate(rules):
                if rule.rule_id == rule_id:
                    rules.pop(i)
                    self._profile.touch()
                    self.save_profile()
                    self._update_status()
                    logger.info("Deleted rule '%s'", rule_id)
                    return True
        return False

    # ------------------------------------------------------------------
    # Rule Execution
    # ------------------------------------------------------------------

    def execute_all_enabled_rules(self) -> List[RuleExecutionResult]:
        """Execute all enabled rules in the current profile.

        Returns a list of results. Rules are executed in order:
        1. Auto-clone rules (safe, copies only)
        2. Index rules (advisory, no file changes)
        3. Cleanup rules (dry-run only in v1)
        """
        if not self._profile:
            logger.warning("No profile loaded, cannot execute rules")
            return []

        self._status.running = True
        self._status.last_execution = datetime.now(timezone.utc).isoformat()

        results: List[RuleExecutionResult] = []

        # 1. Execute auto-clone rules (safest)
        for rule in self._profile.rules.get_enabled_clone_rules():
            result = self.protocol.execute_clone_rule(rule)
            results.append(result)
            rule.last_executed = datetime.now(timezone.utc).isoformat()
            rule.execution_count += 1
            self._status.rules_executed_this_session += 1
            self._status.files_cloned_this_session += result.files_processed
            if result.errors:
                self._status.errors_this_session += len(result.errors)

        # 2. Execute index rules (advisory only)
        for rule in self._profile.rules.get_enabled_index_rules():
            result = self.protocol.execute_index_rule(rule)
            results.append(result)
            rule.last_executed = datetime.now(timezone.utc).isoformat()
            rule.execution_count += 1
            self._status.rules_executed_this_session += 1

        # 3. Execute cleanup rules (dry-run only in v1)
        for rule in self._profile.rules.get_enabled_cleanup_rules():
            result = self.protocol.execute_cleanup_rule(rule)
            results.append(result)
            rule.last_executed = datetime.now(timezone.utc).isoformat()
            rule.execution_count += 1
            self._status.rules_executed_this_session += 1

        self._profile.touch()
        self.save_profile()

        # Log summary
        total_cloned = sum(r.files_processed for r in results if r.rule_type == "auto_clone")
        total_errors = sum(len(r.errors) for r in results)
        logger.info(
            "Executed %d rules: %d files cloned, %d errors",
            len(results), total_cloned, total_errors,
        )

        self._log_execution_summary(results, total_cloned, total_errors)

        return results

    def execute_rule_by_id(self, rule_id: str) -> Optional[RuleExecutionResult]:
        """Execute a single rule by ID."""
        if not self._profile:
            return None
        rule = self._profile.rules.get_rule_by_id(rule_id)
        if rule is None:
            return None

        if isinstance(rule, AutoCloneRule):
            result = self.protocol.execute_clone_rule(rule)
        elif isinstance(rule, CleanupRule):
            result = self.protocol.execute_cleanup_rule(rule)
        elif isinstance(rule, IndexRule):
            result = self.protocol.execute_index_rule(rule)
        else:
            return None

        rule.last_executed = datetime.now(timezone.utc).isoformat()
        rule.execution_count += 1
        self._profile.touch()
        self.save_profile()
        return result

    # ------------------------------------------------------------------
    # Status & Stats
    # ------------------------------------------------------------------

    def get_status(self) -> ManagerStatus:
        """Get current manager status."""
        self._update_status()
        return self._status

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats about the user profile system."""
        if not self._profile:
            return {"error": "No profile loaded"}

        all_rules = self._profile.rules.all_rules()
        return {
            "user_id": self._profile.user_id,
            "profile_version": self._profile.version,
            "profile_updated": self._profile.updated_at,
            "total_rules": len(all_rules),
            "enabled_rules": sum(1 for r in all_rules if r.status == RuleStatus.ENABLED),
            "disabled_rules": sum(1 for r in all_rules if r.status == RuleStatus.DISABLED),
            "draft_rules": sum(1 for r in all_rules if r.status == RuleStatus.DRAFT),
            "clone_rules": len(self._profile.rules.auto_clone_rules),
            "cleanup_rules": len(self._profile.rules.cleanup_rules),
            "index_rules": len(self._profile.rules.index_rules),
            "session": self._status.to_dict(),
            "preferences": self._profile.preferences,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_status(self) -> None:
        """Update internal status counters."""
        if not self._profile:
            self._status.total_rules = 0
            self._status.enabled_rules = 0
            return

        all_rules = self._profile.rules.all_rules()
        self._status.total_rules = len(all_rules)
        self._status.enabled_rules = sum(1 for r in all_rules if r.status == RuleStatus.ENABLED)

    def _log_execution_summary(
        self,
        results: List[RuleExecutionResult],
        total_cloned: int,
        total_errors: int,
    ) -> None:
        """Log execution summary to worklog."""
        try:
            self.worklog.log_task(
                agent_id="nexusclaw-user-profile",
                task_id="profile-rule-execution-batch",
                intent="execute_all_enabled_rules",
                status="ok" if total_errors == 0 else "partial",
                duration_ms=sum(r.duration_ms for r in results),
                evidence=[
                    f"Rules executed: {len(results)}",
                    f"Files cloned: {total_cloned}",
                    f"Errors: {total_errors}",
                ],
                metadata={
                    "results": [r.to_dict() for r in results],
                    "total_cloned": total_cloned,
                    "total_errors": total_errors,
                },
            )
        except Exception as e:
            logger.warning("Failed to log execution summary to worklog: %s", e)


# Singleton instance
_manager_instance: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get the singleton ProfileManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ProfileManager()
    return _manager_instance
