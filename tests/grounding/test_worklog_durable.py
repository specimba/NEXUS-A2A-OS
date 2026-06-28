from pathlib import Path

from nexus_os.grounding.store import GroundingStore
from nexus_os.nexusclaw.worklog import WorklogSystem
from nexus_os.vault.memory_channels import MemoryChannelManager


def test_worklog_queue_survives_new_store_instance(tmp_path: Path):
    store = GroundingStore(tmp_path)
    worklog = WorklogSystem(
        memory_channels=MemoryChannelManager(),
        grounding_store=store,
    )

    entry = worklog.log_task(
        agent_id="grounding-test",
        task_id="task-durable",
        intent="persist worklog evidence",
        status="success",
        duration_ms=12,
    )

    reopened = GroundingStore(tmp_path)
    assert worklog.queue_depth() == 1
    assert reopened.pending_count("nexusclaw.worklog") == 1
    assert entry.metadata["all_sinks_ok"] is True
    assert any(
        result["sink"] == "archivist:grounding_ledger"
        for result in entry.metadata["sink_results"]
    )
