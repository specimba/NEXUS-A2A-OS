from __future__ import annotations

from types import SimpleNamespace

import pytest

from nexus_os.db.manager import DBConfig, DatabaseManager
from nexus_os.sentinel.repository import SentinelRepository
from nexus_os.sentinel.service import SentinelService


class FakeGovernor:
    def __init__(self, decision: str = "ALLOW"):
        self.decision = decision
        self.calls = 0
        self.last_kwargs = None

    def check_access(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return SimpleNamespace(decision=SimpleNamespace(value=self.decision.lower()))


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, **kwargs):
        self.calls += 1
        return {"task_id": f"task-{self.calls}", "status": "completed", "output": "ok"}


@pytest.fixture
def sentinel_factory(tmp_path):
    services = []

    def build(*, governor_decision="ALLOW", db_name="sentinel.db"):
        manager = DatabaseManager(
            DBConfig(
                db_path=str(tmp_path / db_name),
                passphrase="",
                encrypted=False,
                allow_unencrypted=True,
            )
        )
        manager.setup_schema()
        repository = SentinelRepository(manager)
        governor = FakeGovernor(governor_decision)
        executor = FakeExecutor()
        service = SentinelService(repository, governor, executor)
        services.append(service)
        return service, governor, executor

    yield build

    for service in services:
        try:
            service.repository.close()
        except Exception:
            pass

