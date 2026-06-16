from pathlib import Path

from nexus_os.nexusclaw import WorklogEntry, WorklogSystem
from nexus_os.vault.memory_channels import MemoryChannel, MemoryChannelManager


class FailingMemoryChannels:
    def append_episodic(self, **kwargs):
        raise RuntimeError("episodic unavailable")

    def append_task(self, **kwargs):
        raise RuntimeError("task unavailable")

    def append_meta(self, **kwargs):
        raise RuntimeError("meta unavailable")


def test_public_worklog_exports():
    assert WorklogSystem is not None
    assert WorklogEntry is not None


def test_log_task_writes_memory_channels_and_queue():
    memory = MemoryChannelManager()
    worklog = WorklogSystem(memory_channels=memory)

    entry = worklog.log_task(
        agent_id="nexusclaw-test",
        task_id="task-001",
        intent="dry-run dispatch",
        status="success",
        duration_ms=42,
        metadata={"token_count": 7},
    )

    assert worklog.queue_depth() == 1
    assert worklog.get_archivist_queue()[0]["record"]["entry_id"] == entry.entry_id
    assert memory.get_records("nexusclaw-test", MemoryChannel.EPISODIC)
    assert memory.get_records("nexusclaw-test", MemoryChannel.TASK)
    assert memory.get_records("nexusclaw-test", MemoryChannel.META)
    assert entry.metadata["all_sinks_ok"] is True


def test_markdown_append_matches_existing_section_case_insensitively(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("# Agents\n\n## agent worklog\n\n", encoding="utf-8")
    (tmp_path / "SKILLS.md").write_text("# Skills\n\n## Skill Worklog\n\n", encoding="utf-8")
    (tmp_path / "SOUL.md").write_text("# Soul\n\n## Soul Worklog\n\n", encoding="utf-8")
    worklog = WorklogSystem(
        memory_channels=MemoryChannelManager(),
        repo_root=tmp_path,
        markdown_enabled=True,
    )

    worklog.log_task(
        agent_id="nexusclaw-test",
        task_id="task-002",
        intent="append audit line",
        status="success",
        duration_ms=10,
    )

    agents_text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "task-002" in agents_text
    assert "## agent worklog" in agents_text


def test_markdown_append_creates_missing_files_and_sections(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("# Agents\n\nNo worklog here.\n", encoding="utf-8")
    worklog = WorklogSystem(
        memory_channels=MemoryChannelManager(),
        repo_root=tmp_path,
        markdown_enabled=True,
    )

    entry = worklog.log_task(
        agent_id="nexusclaw-test",
        task_id="task-003",
        intent="create markdown sections",
        status="success",
        duration_ms=11,
    )

    for filename, section in (
        ("AGENTS.md", "## Agent Worklog"),
        ("SKILLS.md", "## Skill Worklog"),
        ("SOUL.md", "## Soul Worklog"),
    ):
        text = (tmp_path / filename).read_text(encoding="utf-8")
        assert section in text
        assert entry.task_id in text


def test_default_worklog_does_not_mutate_real_markdown(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Agents\n", encoding="utf-8")
    worklog = WorklogSystem(memory_channels=MemoryChannelManager(), repo_root=tmp_path)

    worklog.log_task(
        agent_id="nexusclaw-test",
        task_id="task-004",
        intent="no default markdown mutation",
        status="success",
        duration_ms=12,
    )

    assert agents.read_text(encoding="utf-8") == "# Agents\n"


def test_sink_failures_are_reported_not_silently_successful(tmp_path: Path):
    worklog = WorklogSystem(memory_channels=FailingMemoryChannels(), repo_root=tmp_path)

    entry = worklog.log_task(
        agent_id="nexusclaw-test",
        task_id="task-005",
        intent="surface sink failures",
        status="partial",
        duration_ms=13,
    )

    failed = [result for result in entry.metadata["sink_results"] if not result["success"]]
    assert entry.metadata["all_sinks_ok"] is False
    assert {result["sink"] for result in failed} == {
        "memory:episodic",
        "memory:task",
        "memory:meta",
    }
