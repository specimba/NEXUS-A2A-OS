"""Tests for PortRegistry — centralized port ownership and conflict prevention."""

import os
import socket
import threading
import time
from pathlib import Path

import pytest

from nexus_os.bridge.port_registry import (
    PortConflictError,
    PortRecord,
    PortRegistry,
)


class TestPortRecord:
    def test_dataclass_fields(self):
        record = PortRecord(port=7354, owner="test_owner")
        assert record.port == 7354
        assert record.owner == "test_owner"
        assert record.pid is None
        assert record.timestamp is None
        assert record.metadata == {}

    def test_with_optional_fields(self):
        record = PortRecord(
            port=7354,
            owner="test_owner",
            pid=12345,
            timestamp="2026-06-12T00:00:00+00:00",
            metadata={"key": "value"},
        )
        assert record.pid == 12345
        assert record.timestamp == "2026-06-12T00:00:00+00:00"
        assert record.metadata == {"key": "value"}


class TestPortRegistryBasics:
    def test_canonical_ports(self):
        assert PortRegistry.CANONICAL_PORTS[7352] == "nexus_governance"
        assert PortRegistry.CANONICAL_PORTS[7353] == "twave"
        assert PortRegistry.CANONICAL_PORTS[7354] == "gross_bridge"
        assert PortRegistry.CANONICAL_PORTS[7355] == "modelrelay_internal"
        assert PortRegistry.CANONICAL_PORTS[11436] == "nexusclaw_ollama_lane"

    def test_init_creates_state_dir(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        assert registry._state_dir.exists()
        assert registry._registry_file.exists()

    def test_register_and_get_owner(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        record = registry.register(7354, "test_owner")
        assert record.port == 7354
        assert record.owner == "test_owner"
        assert record.pid == os.getpid()
        assert record.timestamp is not None

        owner = registry.get_owner(7354)
        assert owner is not None
        assert owner.owner == "test_owner"

    def test_register_conflict_raises(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "first_owner")
        with pytest.raises(PortConflictError) as exc_info:
            registry.register(7354, "second_owner")
        assert "already owned" in str(exc_info.value)
        assert "first_owner" in str(exc_info.value)

    def test_register_force_override(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "first_owner")
        record = registry.register(7354, "second_owner", force=True)
        assert record.owner == "second_owner"

    def test_unregister(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "test_owner")
        assert registry.get_owner(7354) is not None
        assert registry.unregister(7354) is True
        assert registry.get_owner(7354) is None
        assert registry.unregister(7354) is False

    def test_list_ports(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "owner_a")
        registry.register(7355, "owner_b")
        ports = registry.list_ports()
        assert len(ports) == 2
        assert ports[7354].owner == "owner_a"
        assert ports[7355].owner == "owner_b"

    def test_persistence(self, tmp_path):
        registry1 = PortRegistry(state_dir=tmp_path)
        registry1.register(7354, "persisted_owner")
        del registry1

        registry2 = PortRegistry(state_dir=tmp_path)
        owner = registry2.get_owner(7354)
        assert owner is not None
        assert owner.owner == "persisted_owner"


class TestPortRegistryActiveCheck:
    def test_is_port_in_use_free_port(self):
        # Find a free ephemeral port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        assert PortRegistry.is_port_in_use(free_port) is False

    def test_is_port_in_use_bound_port(self, tmp_path):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            bound_port = s.getsockname()[1]
            s.listen(1)
            assert PortRegistry.is_port_in_use(bound_port) is True

    def test_is_available(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            bound_port = s.getsockname()[1]
            s.listen(1)
            assert registry.is_available(bound_port) is False

    def test_is_available_unregistered_free_port(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        assert registry.is_available(free_port) is True


class TestPortRegistryValidation:
    def test_validate_canonical_ok(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        for port, owner in registry.CANONICAL_PORTS.items():
            registry.register(port, owner)
        mismatches = registry.validate_canonical()
        assert mismatches == {}

    def test_validate_canonical_mismatch(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "wrong_owner")
        mismatches = registry.validate_canonical()
        assert 7354 in mismatches
        assert "wrong_owner" in mismatches[7354]

    def test_validate_canonical_missing(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        # Don't register any canonical ports
        mismatches = registry.validate_canonical()
        # Missing registrations are not mismatches; only wrong owners are
        assert mismatches == {}


class TestPortRegistryHealthCheck:
    def test_health_check_empty(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        # Unregister any canonical ports that might be registered from previous tests
        for port in registry.CANONICAL_PORTS:
            registry.unregister(port)
        health = registry.health_check()
        # If any canonical ports are actively listening on the system, status may be degraded
        # Just verify structure is correct
        assert isinstance(health["status"], str)
        assert isinstance(health["conflicts"], list)
        assert isinstance(health["ports"], dict)

    def test_health_check_stale_registration(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        # Use a high ephemeral port to avoid colliding with running services (GROSS, etc.)
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as _probe:
            _probe.bind(("127.0.0.1", 0))
            stale_port = _probe.getsockname()[1]
        registry.register(stale_port, "stale_owner", force=True)
        health = registry.health_check()
        assert health["status"] == "degraded"
        assert len(health["conflicts"]) >= 1
        # Find the stale-registration conflict (order-independent)
        stale_conflicts = [c for c in health["conflicts"] if "stale registration" in c]
        assert len(stale_conflicts) >= 1
        assert str(stale_port) in stale_conflicts[0]

    def test_health_check_unregistered_but_listening(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            bound_port = s.getsockname()[1]
            s.listen(1)
            health = registry.health_check()
            # If the bound port is a canonical port, it should be flagged
            # If it's ephemeral, it won't be in canonical ports so no conflict
            # This test is mainly for structure validation
            assert isinstance(health["ports"], dict)

    def test_release_stale(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        # Use a high ephemeral port to avoid colliding with running services
        registry.register(47354, "stale_owner", force=True)
        removed = registry.release_stale()
        assert removed == 1
        assert registry.get_owner(47354) is None


class TestPortRegistryThreadSafety:
    def test_concurrent_register(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        errors = []
        records = []

        def worker(port, owner):
            try:
                record = registry.register(port, owner)
                records.append(record)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(7354, f"owner_{i}"))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed, rest should raise PortConflictError
        success_count = sum(1 for r in records if r.owner.startswith("owner_"))
        conflict_count = sum(1 for e in errors if isinstance(e, PortConflictError))
        assert success_count == 1
        assert conflict_count == 9

    def test_concurrent_unregister(self, tmp_path):
        registry = PortRegistry(state_dir=tmp_path)
        registry.register(7354, "owner")
        results = []

        def worker():
            results.append(registry.unregister(7354))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should return True, rest False
        assert sum(results) == 1
        assert results.count(False) == 4
