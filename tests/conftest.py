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
    """Pick a writable temp root that avoids stale repo-local ACL problems."""
    candidates: list[Path] = []
    if os.environ.get("NEXUS_TEST_TEMP_ROOT"):
        candidates.append(Path(os.environ["NEXUS_TEST_TEMP_ROOT"]))
    candidates.extend([
        Path("C:/tmp") / "nexus_pytest",
        Path.cwd() / ".tmp" / "pytest_runtime",
        Path.cwd() / "tests_tmp",
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
