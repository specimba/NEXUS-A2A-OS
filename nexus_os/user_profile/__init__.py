"""nexus_os/user_profile/__init__.py — User Profile Preference System for NEXUS OS

This package provides user-centric file organization, tidyness rules, and preference
management for NEXUS OS. It is designed as a first-class system feature, not a one-off
utility.

Key features:
  - UserProfile: stores preferences, tidyness rules, auto-clone rules
  - PreferenceStore: persistent storage of profiles (JSON-backed, future SQLite)
  - TidynessRule: configurable rules for file organization (clone, cleanup, index)
  - FileOrganizationProtocol: executes rules with governance gates (user-approved)
  - ProfileManager: integrates with ARCHIVIST, worklog, and NEXUSCLAW runner

All operations are:
  - Evidence-grounded (logged to worklog + META channel)
  - User-approved (rules are advisory until explicitly enabled)
  - Auditable (every clone/cleanup is tracked)
  - Reversible (clone operations are tracked, originals untouched)
"""

from nexus_os.user_profile.preferences import (
    UserProfile,
    PreferenceStore,
    AutoCloneRule,
    CleanupRule,
    IndexRule,
    ProfileRuleSet,
    RuleStatus,
    FileScope,
)
from nexus_os.user_profile.protocol import (
    FileOrganizationProtocol,
    RuleExecutionResult,
    CloneOperation,
)
from nexus_os.user_profile.profile_manager import (
    ProfileManager,
    get_profile_manager,
)

__all__ = [
    "UserProfile",
    "PreferenceStore",
    "AutoCloneRule",
    "CleanupRule",
    "IndexRule",
    "ProfileRuleSet",
    "RuleStatus",
    "FileScope",
    "FileOrganizationProtocol",
    "RuleExecutionResult",
    "CloneOperation",
    "ProfileManager",
    "get_profile_manager",
]
