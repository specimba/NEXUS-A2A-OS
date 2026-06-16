"""tests/claw/test_config_integrity.py — Config integrity verification."""

from __future__ import annotations

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from nexus_os.claw.exceptions import ConfigIntegrityError
from nexus_os.claw.security.config_integrity import (
    ConfigIntegrityChecker,
    IntegrityFailureMode,
    hash_bytes,
    hash_file,
)


@pytest.fixture
def tmp_base(tmp_path: Path) -> str:
    return str(tmp_path)


def test_hash_generation_consistent() -> None:
    data = b"hello world"
    h1 = hash_bytes(data)
    h2 = hash_bytes(data)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_changes_on_modification(tmp_base: str) -> None:
    path = os.path.join(tmp_base, "test.json")
    with open(path, "w") as f:
        f.write('{"key": "value"}')
    h1 = hash_file(path)
    with open(path, "w") as f:
        f.write('{"key": "modified"}')
    h2 = hash_file(path)
    assert h1 != h2


def test_verify_passes_with_valid_hash(tmp_base: str) -> None:
    path = os.path.join(tmp_base, "config.json")
    with open(path, "w") as f:
        f.write("ok")
    expected = hash_file(path)
    checker = ConfigIntegrityChecker(
        {"config.json": expected},
        base_dir=tmp_base,
        failure_mode=IntegrityFailureMode.HALT,
    )
    assert checker.verify_all()


def test_verify_fails_with_mismatch(tmp_base: str) -> None:
    path = os.path.join(tmp_base, "config.json")
    with open(path, "w") as f:
        f.write("original")
    expected = hash_file(path)
    with open(path, "w") as f:
        f.write("tampered")
    checker = ConfigIntegrityChecker(
        {"config.json": expected},
        base_dir=tmp_base,
        failure_mode=IntegrityFailureMode.HALT,
    )
    with pytest.raises(ConfigIntegrityError):
        checker.verify_all()


def test_verify_halt_mode_stops_startup(tmp_base: str) -> None:
    checker = ConfigIntegrityChecker(
        {"missing.json": "abc123"},
        base_dir=tmp_base,
        failure_mode=IntegrityFailureMode.HALT,
    )
    with pytest.raises(ConfigIntegrityError):
        checker.verify_all()


def test_verify_warn_mode_allows_continued(tmp_base: str) -> None:
    path = os.path.join(tmp_base, "config.json")
    with open(path, "w") as f:
        f.write("original")
    expected = hash_file(path)
    with open(path, "w") as f:
        f.write("tampered")
    checker = ConfigIntegrityChecker(
        {"config.json": expected},
        base_dir=tmp_base,
        failure_mode=IntegrityFailureMode.WARN,
    )
    result = checker.verify_all()
    assert not result  # mismatch detected but no exception


def test_verify_one_specific_file(tmp_base: str) -> None:
    path = os.path.join(tmp_base, "a.json")
    with open(path, "w") as f:
        f.write("data")
    h = hash_file(path)
    checker = ConfigIntegrityChecker(
        {"a.json": h, "b.json": "unused"},
        base_dir=tmp_base,
        failure_mode=IntegrityFailureMode.HALT,
    )
    assert checker.verify_one("a.json")
    with open(path, "w") as f:
        f.write("changed")
    with pytest.raises(ConfigIntegrityError):
        checker.verify_one("a.json")


def test_to_snapshot(tmp_base: str) -> None:
    path_a = os.path.join(tmp_base, "a.json")
    path_b = os.path.join(tmp_base, "b.yaml")
    with open(path_a, "w") as f:
        f.write("aaa")
    with open(path_b, "w") as f:
        f.write("bbb")
    checker = ConfigIntegrityChecker({}, base_dir=tmp_base)
    snap = checker.to_snapshot({"a.json": path_a, "b.yaml": path_b})
    assert len(snap) == 2
    assert len(snap["a.json"]) == 64
    assert snap["a.json"] == hash_file(path_a)


if __name__ == "__main__":
    pytest.main([__file__])
