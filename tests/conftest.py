import sys
from pathlib import Path
import inspect
import tempfile
import types
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_REPO_TEMP_ROOT = Path.cwd() / "tests_tmp"
_REPO_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_REPO_TEMP_ROOT)

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
    path = _REPO_TEMP_ROOT / f"{safe_name}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path
