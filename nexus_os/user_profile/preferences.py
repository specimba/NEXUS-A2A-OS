"""nexus_os/user_profile/preferences.py — User preference data models for NEXUS OS.

Defines the core data structures for user profiles, tidyness rules, and auto-clone
configurations. All structures are serializable, auditable, and governance-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json


class RuleStatus(str, Enum):
    """Status of a tidyness rule in the user profile."""
    DRAFT = "draft"         # Created but not yet enabled
    ENABLED = "enabled"     # Active and auto-executed
    DISABLED = "disabled"   # Inactive but preserved
    REVIEW = "review"       # Needs user review before enabling


class RuleType(str, Enum):
    """Type of tidyness rule."""
    AUTO_CLONE = "auto_clone"     # Clone recent files to destination
    CLEANUP = "cleanup"           # Remove old files matching pattern
    INDEX = "index"             # Add files to ARCHIVIST index
    ORGANIZE = "organize"       # Move files into subdirectories by pattern


class FileScope(str, Enum):
    """Scope of files a rule applies to."""
    RECENT_ONLY = "recent_only"       # Only files within time window
    ALL_MATCHING = "all_matching"     # All files matching pattern, regardless of age
    EXPLICIT_LIST = "explicit_list"   # Only files in an explicit list


@dataclass
class AutoCloneRule:
    """Rule: automatically clone recent files from source to destination.

    Example: Clone all files from NEXUS/docs/research modified in last 48h
    to ARCHIVIST/NEXUS_latest for easy access.
    """
    rule_id: str
    name: str
    description: str

    # Source configuration
    source_path: str  # Absolute or relative path (resolved at runtime)
    file_patterns: List[str] = field(default_factory=list)  # e.g., ["*.md", "*.py"]
    exclude_patterns: List[str] = field(default_factory=list)  # e.g., ["*.tmp", "*.log"]

    # Time window
    time_window_hours: float = 48.0  # Only files modified within this window
    file_scope: FileScope = FileScope.RECENT_ONLY

    # Destination
    destination_path: str = ""  # Where to clone files
    preserve_structure: bool = True  # Maintain subdirectory structure
    create_manifest: bool = True  # Generate MANIFEST.md in destination

    # Governance
    status: RuleStatus = RuleStatus.DRAFT
    enabled_at: Optional[str] = None
    last_executed: Optional[str] = None
    execution_count: int = 0
    created_by: str = "user"  # "user" or "system_suggestion"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Metadata
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoCloneRule":
        # Convert string enums back to enum types
        if "file_scope" in data and isinstance(data["file_scope"], str):
            data["file_scope"] = FileScope(data["file_scope"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = RuleStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CleanupRule:
    """Rule: remove or archive old files matching a pattern.

    Example: Delete .tmp files older than 7 days from tests_tmp/.
    """
    rule_id: str
    name: str
    description: str

    target_path: str
    file_patterns: List[str] = field(default_factory=list)
    min_age_hours: float = 168.0  # 7 days
    action: str = "delete"  # "delete", "archive", "move"
    destination_if_move: str = ""  # Required if action == "move"

    # Safety: never delete without backup
    require_backup: bool = True
    backup_path: str = ""  # Where to backup before deletion
    max_delete_count: int = 100  # Safety limit per execution

    status: RuleStatus = RuleStatus.DRAFT
    enabled_at: Optional[str] = None
    last_executed: Optional[str] = None
    execution_count: int = 0
    created_by: str = "user"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleanupRule":
        if "status" in data and isinstance(data["status"], str):
            data["status"] = RuleStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class IndexRule:
    """Rule: add files to ARCHIVIST index for processing.

    Example: Auto-index all .md files from docs/research to ARCHIVIST pipeline.
    """
    rule_id: str
    name: str
    description: str

    source_path: str
    file_patterns: List[str] = field(default_factory=lambda: ["*.md"])
    time_window_hours: float = 48.0
    archivist_stage: str = "import"  # "import", "compile", "fit", or "all"

    status: RuleStatus = RuleStatus.DRAFT
    enabled_at: Optional[str] = None
    last_executed: Optional[str] = None
    execution_count: int = 0
    created_by: str = "user"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexRule":
        if "status" in data and isinstance(data["status"], str):
            data["status"] = RuleStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProfileRuleSet:
    """Collection of all tidyness rules for a user profile."""
    auto_clone_rules: List[AutoCloneRule] = field(default_factory=list)
    cleanup_rules: List[CleanupRule] = field(default_factory=list)
    index_rules: List[IndexRule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_clone_rules": [r.to_dict() for r in self.auto_clone_rules],
            "cleanup_rules": [r.to_dict() for r in self.cleanup_rules],
            "index_rules": [r.to_dict() for r in self.index_rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileRuleSet":
        return cls(
            auto_clone_rules=[AutoCloneRule.from_dict(r) for r in data.get("auto_clone_rules", [])],
            cleanup_rules=[CleanupRule.from_dict(r) for r in data.get("cleanup_rules", [])],
            index_rules=[IndexRule.from_dict(r) for r in data.get("index_rules", [])],
        )

    def all_rules(self) -> List[Any]:
        """Return all rules as a flat list."""
        return self.auto_clone_rules + self.cleanup_rules + self.index_rules

    def get_enabled_clone_rules(self) -> List[AutoCloneRule]:
        return [r for r in self.auto_clone_rules if r.status == RuleStatus.ENABLED]

    def get_enabled_cleanup_rules(self) -> List[CleanupRule]:
        return [r for r in self.cleanup_rules if r.status == RuleStatus.ENABLED]

    def get_enabled_index_rules(self) -> List[IndexRule]:
        return [r for r in self.index_rules if r.status == RuleStatus.ENABLED]

    def get_rule_by_id(self, rule_id: str) -> Optional[Any]:
        for rule in self.all_rules():
            if rule.rule_id == rule_id:
                return rule
        return None


@dataclass
class UserProfile:
    """A user profile in NEXUS OS, containing preferences and tidyness rules.

    Each user has one profile. The default user is "speci" (the system owner).
    Profiles are stored persistently and loaded at NEXUSCLAW startup.
    """
    user_id: str = "speci"
    display_name: str = "Speci"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Preferences
    preferences: Dict[str, Any] = field(default_factory=lambda: {
        "tidyness_auto_clone_enabled": True,
        "tidyness_cleanup_enabled": False,  # Cleanup requires explicit enable (safety)
        "tidyness_index_enabled": True,
        "default_clone_window_hours": 48.0,
        "default_clone_destination": "C:\\Users\\speci.000\\Downloads\\ARCHIVIST\\NEXUS_latest",
        "preserve_directory_structure": True,
        "generate_manifests": True,
        "excluded_paths": [
            "*.git*", "*.pytest_cache*", "*__pycache__*", "*node_modules*",
            "*.venv*", "*.tmp*", "*.log*", "*tests_tmp*", "*.brv*",
        ],
    })

    # Rules
    rules: ProfileRuleSet = field(default_factory=ProfileRuleSet)

    # Metadata
    version: int = 1  # Profile schema version for migrations
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "preferences": self.preferences,
            "rules": self.rules.to_dict(),
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        return cls(
            user_id=data.get("user_id", "speci"),
            display_name=data.get("display_name", "Speci"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            preferences=data.get("preferences", {}),
            rules=ProfileRuleSet.from_dict(data.get("rules", {})),
            version=data.get("version", 1),
            tags=data.get("tags", []),
        )

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()


class PreferenceStore:
    """Persistent storage for user profiles.

    Currently JSON-backed. Future: SQLite backend for scalability.
    All profiles are stored in a single directory with one JSON file per user.
    """

    def __init__(self, storage_dir: str = "C:\\Users\\speci.000\\Documents\\NEXUS\\.nexus_pi\\profiles") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        return self.storage_dir / f"{user_id}.json"

    def save(self, profile: UserProfile) -> None:
        """Save a user profile to disk."""
        profile.touch()
        path = self._profile_path(profile.user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, user_id: str) -> Optional[UserProfile]:
        """Load a user profile from disk. Returns None if not found."""
        path = self._profile_path(user_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return UserProfile.from_dict(data)

    def load_or_create(self, user_id: str = "speci") -> UserProfile:
        """Load a profile or create a default one if it doesn't exist."""
        profile = self.load(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            # Add default tidyness rules only for the default user
            if user_id == "speci":
                profile.rules.auto_clone_rules.append(AutoCloneRule(
                    rule_id="clone-recent-to-archivist",
                    name="Clone Recent NEXUS Files to ARCHIVIST",
                    description="Auto-clone all files from NEXUS main folder modified in the last 48 hours to ARCHIVIST/NEXUS_latest for easy access.",
                    source_path="C:\\Users\\speci.000\\Documents\\NEXUS",
                    file_patterns=["*.md", "*.py", "*.yaml", "*.json"],
                    exclude_patterns=["*.git*", "*.pytest_cache*", "*__pycache__*", "*node_modules*", "*.venv*", "*.tmp*", "*.log*", "*tests_tmp*", "*.brv*"],
                    time_window_hours=48.0,
                    file_scope=FileScope.RECENT_ONLY,
                    destination_path="C:\\Users\\speci.000\\Downloads\\ARCHIVIST\\NEXUS_latest",
                    preserve_structure=True,
                    create_manifest=True,
                    status=RuleStatus.ENABLED,
                    enabled_at=datetime.now(timezone.utc).isoformat(),
                    tags=["default", "archivist", "speci-preference"],
                ))
            self.save(profile)
        return profile

    def list_users(self) -> List[str]:
        """List all user IDs with stored profiles."""
        return [p.stem for p in self.storage_dir.glob("*.json")]

    def delete(self, user_id: str) -> bool:
        """Delete a user profile. Returns True if deleted."""
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            return True
        return False
