"""PortRegistry — Centralized port ownership and conflict prevention.

Manages the canonical port assignments for NEXUS OS subsystems and prevents
double-binding (e.g., GROSS MCP Bridge vs NEXUS MCP Bridge both claiming 7354).

Usage:
    registry = PortRegistry()
    registry.register(7354, "nexus_mcp_bridge", pid=os.getpid())
    if registry.is_available(7354):
        uvicorn.run(app, port=7354)
    else:
        owner = registry.get_owner(7354)
        raise PortConflictError(f"Port 7354 already owned by {owner}")
"""

from __future__ import annotations

import json
import os
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PortRecord:
    """Immutable record of port ownership."""
    port: int
    owner: str
    pid: Optional[int] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class PortConflictError(RuntimeError):
    """Raised when attempting to register a port that is already owned."""
    pass


class PortRegistry:
    """Thread-safe registry for port ownership.

    Uses a JSON-backed state file in `.nexus_pi/state/port_registry.json`.
    Also performs an active socket check to verify if a port is truly in use.
    """

    # Canonical port assignments.
    #
    # Hard rule: 7352 is the NEXUS Brain API / governance backend. It is not a
    # ModelRelay, dashboard, proxy, MCP, or experiment port. ModelRelay uses
    # 7350 for the Node/npm primary relay and 7355 for the Python fallback.
    CANONICAL_PORTS = {
        3001: "next_dashboard",
        7350: "modelrelay_npm",
        7352: "brain_api",
        7353: "twave",
        7354: "gross_bridge",
        7355: "modelrelay_python",
        7356: "static_dashboard",
        7357: "god_mode_proxy",
        8765: "state_manager_ws",
        8766: "state_manager_http",
        11434: "ollama_default",
        11435: "ollama_guard",
        11436: "nexusclaw_ollama_lane",
    }

    def __init__(self, state_dir: Optional[Path] = None) -> None:
        if state_dir is None:
            repo_root = self._find_repo_root()
            state_dir = (repo_root or Path.cwd()) / ".nexus_pi" / "state"
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._registry_file = self._state_dir / "port_registry.json"
        self._lock = threading.Lock()
        self._ports: Dict[int, PortRecord] = {}
        self._load()
        # Ensure registry file exists even when empty
        if not self._registry_file.exists():
            self._save()

    @staticmethod
    def _find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
        current = (start or Path.cwd()).resolve()
        for path in [current, *current.parents]:
            if (path / ".git").exists():
                return path
        return None

    def _load(self) -> None:
        if self._registry_file.exists():
            try:
                data = json.loads(self._registry_file.read_text(encoding="utf-8"))
                for port_str, record in data.items():
                    self._ports[int(port_str)] = PortRecord(**record)
            except (json.JSONDecodeError, TypeError):
                self._ports = {}

    def _save(self) -> None:
        data = {
            str(p.port): {
                "port": p.port,
                "owner": p.owner,
                "pid": p.pid,
                "timestamp": p.timestamp,
                "metadata": p.metadata,
            }
            for p in self._ports.values()
        }
        self._registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
        """Active check: try to bind to the port. If it fails, someone is using it."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True

    def is_available(self, port: int) -> bool:
        """Return True if port is not registered and not actively in use."""
        with self._lock:
            if port in self._ports:
                return False
        return not self.is_port_in_use(port)

    def get_owner(self, port: int) -> Optional[PortRecord]:
        """Return ownership record for a port, or None if unclaimed."""
        with self._lock:
            return self._ports.get(port)

    def register(
        self,
        port: int,
        owner: str,
        pid: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        force: bool = False,
    ) -> PortRecord:
        """Register ownership of a port.

        Raises:
            PortConflictError: If port is already owned and force=False.
        """
        with self._lock:
            if port in self._ports and not force:
                existing = self._ports[port]
                raise PortConflictError(
                    f"Port {port} already owned by {existing.owner} "
                    f"(pid={existing.pid}). Use force=True to override."
                )
            record = PortRecord(
                port=port,
                owner=owner,
                pid=pid or os.getpid(),
                timestamp=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
                metadata=metadata or {},
            )
            self._ports[port] = record
            self._save()
            return record

    def unregister(self, port: int) -> bool:
        """Remove ownership of a port. Return True if removed, False if not found."""
        with self._lock:
            if port in self._ports:
                del self._ports[port]
                self._save()
                return True
            return False

    def list_ports(self) -> Dict[int, PortRecord]:
        """Return a snapshot of all registered ports."""
        with self._lock:
            return dict(self._ports)

    def validate_canonical(self) -> Dict[int, str]:
        """Verify all canonical ports match their expected owners.

        Returns a dict of {port: error_message} for any mismatches.
        """
        mismatches = {}
        with self._lock:
            for port, expected_owner in self.CANONICAL_PORTS.items():
                if port in self._ports:
                    actual = self._ports[port].owner
                    if actual != expected_owner:
                        mismatches[port] = (
                            f"Expected owner '{expected_owner}' but found '{actual}'"
                        )
        return mismatches

    def health_check(self) -> Dict[str, Any]:
        """Run a full health check of all registered ports.

        Returns a dict with status, conflicts, and in-use verification.
        """
        conflicts = []
        in_use = {}
        with self._lock:
            for port, record in self._ports.items():
                used = self.is_port_in_use(port)
                in_use[port] = {
                    "owner": record.owner,
                    "pid": record.pid,
                    "registered": True,
                    "actively_listening": used,
                }
                # If registered but not in use, the process may have died
                if not used:
                    conflicts.append(
                        f"Port {port} registered to {record.owner} (pid={record.pid}) "
                        f"but not actively listening — stale registration."
                    )
        # Also check canonical ports that are not registered
        for port, expected in self.CANONICAL_PORTS.items():
            if port not in self._ports:
                used = self.is_port_in_use(port)
                in_use[port] = {
                    "owner": expected,
                    "registered": False,
                    "actively_listening": used,
                }
                if used:
                    conflicts.append(
                        f"Port {port} is actively listening but not registered in PortRegistry."
                    )

        return {
            "status": "ok" if not conflicts else "degraded",
            "conflicts": conflicts,
            "ports": in_use,
        }

    def release_stale(self) -> int:
        """Remove registrations for ports that are no longer actively in use.

        Returns the number of stale registrations removed.
        """
        removed = 0
        with self._lock:
            stale = [
                port for port in self._ports
                if not self.is_port_in_use(port)
            ]
            for port in stale:
                del self._ports[port]
                removed += 1
            if removed:
                self._save()
        return removed
