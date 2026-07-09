import sys
from pathlib import Path
import inspect
import os
import shutil
import tempfile
import types
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _choose_test_temp_root() -> Path:
    """Pick a writable temp root that avoids stale repo-local ACL problems.

    Prefer system temp and explicit env over repo-local `.tmp/pytest_runtime`,
    which often hits WinError 5 on locked Windows trees.
    """
    candidates: list[Path] = []
    if os.environ.get("NEXUS_TEST_TEMP_ROOT"):
        candidates.append(Path(os.environ["NEXUS_TEST_TEMP_ROOT"]))
    candidates.extend([
        Path(tempfile.gettempdir()) / "nexus_pytest",
        Path("C:/tmp") / "nexus_pytest",
        Path.cwd() / "tests_tmp",
        Path.cwd() / ".tmp" / "pytest_runtime",
    ])

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / f".write_probe_{uuid.uuid4().hex}"
            probe.mkdir()
            probe.rmdir()
            return candidate
        except OSError:
            continue
    fallback = Path(tempfile.gettempdir()) / "nexus_pytest"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


_TEST_TEMP_ROOT = _choose_test_temp_root() / f"run_{uuid.uuid4().hex}"
_TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TEST_TEMP_ROOT)

# Isolate durable NEXUS state so tests never write to a RO ~/.nexus or
# repo-tracked SQLite (Windows WinError 5 / sqlite readonly).
_NEXUS_HOME = _TEST_TEMP_ROOT / "nexus_home"
_NEXUS_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NEXUS_HOME", str(_NEXUS_HOME))
os.environ.setdefault("NEXUS_GROUNDING_ROOT", str(_NEXUS_HOME / "grounding"))
os.environ.setdefault(
    "NEXUS_TRUST_MEMORY_PATH", str(_NEXUS_HOME / "trust_memory.json")
)
os.environ.setdefault(
    "NEXUS_CONTINUITY_LEDGER", str(_NEXUS_HOME / "continuity" / "runs.jsonl")
)
os.environ.setdefault("NEXUS_TEST_DB_PATH", str(_NEXUS_HOME / "test.db"))
os.environ.setdefault("NEXUS_TEST_TEMP_ROOT", str(_TEST_TEMP_ROOT))

try:
    import asyncio  # noqa: F401
except Exception:
    asyncio_stub = types.ModuleType("asyncio")
    asyncio_stub.iscoroutinefunction = inspect.iscoroutinefunction

    async def sleep(delay, result=None):
        return result

    def run(coro):
        try:
            while True:
                coro.send(None)
        except StopIteration as exc:
            return exc.value

    asyncio_stub.sleep = sleep
    asyncio_stub.run = run
    sys.modules["asyncio"] = asyncio_stub


@pytest.fixture
def tmp_path(request):
    """Workspace-local tmp_path replacement for this restricted Windows runtime."""
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request.node.name)[:80]
    path = _TEST_TEMP_ROOT / f"{safe_name}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def pytest_sessionfinish(session, exitstatus):
    """Best-effort cleanup; never mask the real pytest result."""
    try:
        shutil.rmtree(_TEST_TEMP_ROOT, ignore_errors=True)
    except OSError:
        pass
