from __future__ import annotations

import asyncio
import sys
import types

from nexus_os.twave.diagnostics import create_twave_router, twave_diagnostics, twave_health


# CANARY: 21cdfb174857432d734f0d3c2116e999
def test_twave_health_is_read_only() -> None:
    payload = twave_health()

    assert payload["status"] == "ok"
    assert payload["runtime_version"] == "2.0"
    assert payload["mode"] == "read_only_diagnostics"
    assert payload["algorithm_mutation"] is False
    assert payload["modules"]["chimera_router_v2"] is True


def test_twave_diagnostics_runs_bounded_smoke() -> None:
    payload = twave_diagnostics("Short safety routing smoke test.")

    assert payload["status"] in {"ok", "degraded"}
    assert payload["algorithm_mutation"] is False
    assert payload["router"]["model"]
    assert payload["router"]["use_qwave"] is True
    if payload["tracker"]["status"] == "ok":
        assert payload["tracker"]["tokens_generated"] == 3
    else:
        assert payload["tracker"]["error"]


class _FakeAPIRouter:
    def __init__(self) -> None:
        self.handlers = {}

    def get(self, path):
        def decorator(func):
            self.handlers[path] = func
            return func

        return decorator


def test_twave_router_exposes_health_and_diagnostics(monkeypatch) -> None:
    fake_fastapi = types.ModuleType("fastapi")
    fake_fastapi.APIRouter = _FakeAPIRouter
    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)

    router = create_twave_router()
    health = asyncio.run(router.handlers["/health"]())
    diagnostics = asyncio.run(router.handlers["/diagnostics"]())

    assert health["status"] == "ok"
    assert diagnostics["status"] in {"ok", "degraded"}
    if diagnostics["tracker"]["status"] == "ok":
        assert diagnostics["tracker"]["tokens_generated"] == 3
    else:
        assert diagnostics["tracker"]["error"]