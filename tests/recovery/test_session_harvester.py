"""Recovery-at-locals session harvester (nexus_os/recovery/session_harvester.py)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_os.recovery.session_harvester import (
    RecoveryLedger,
    SessionHarvester,
    _iter_transcript_values,
    main,
)

FAKE_KEY = "sk-" + "a1B2c3D4e5F6g7H8i9J0" * 2


def _assistant(*content) -> str:
    return json.dumps({
        "type": "assistant",
        "timestamp": "2026-07-03T10:00:00Z",
        "message": {"role": "assistant", "content": list(content)},
    })


def _tool_use(name: str, input_: dict, id_: str = "tu_1") -> dict:
    return {"type": "tool_use", "id": id_, "name": name, "input": input_}


def _user_text(text: str) -> str:
    return json.dumps({
        "type": "user",
        "timestamp": "2026-07-03T10:01:00Z",
        "message": {"role": "user", "content": text},
    })


def _tool_result(text: str, tool_use_id: str = "tu_1") -> str:
    return json.dumps({
        "type": "user",
        "timestamp": "2026-07-03T10:02:00Z",
        "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_use_id,
             "content": [{"type": "text", "text": text}]},
        ]},
    })


def _transcript_lines() -> list[str]:
    return [
        _assistant(_tool_use("ExitPlanMode", {"plan": f"# The Plan\nuse key {FAKE_KEY}"})),
        _assistant(_tool_use("TaskCreate", {"subject": "Slice X: do the thing",
                                            "description": "details"})),
        _assistant(_tool_use("TaskUpdate", {"taskId": "3", "status": "completed"})),
        _assistant(_tool_use("AskUserQuestion",
                             {"questions": [{"question": "Adopt or discard?"}]},
                             id_="tu_ask")),
        _tool_result('Your questions have been answered: "Adopt (Recommended)"',
                     tool_use_id="tu_ask"),
        _user_text("continue the hardening tasks calmly, no key rotation"),
        _user_text("<local-command-caveat>ignore this command noise</local-command-caveat>"),
        _user_text("<task-notification><task-id>t1</task-id>"
                   "<summary>Agent \"miner\" finished</summary>"
                   "<result>Ranked findings: 14 upgrades.</result></task-notification>"),
        _tool_result("[branch abc1234def] vault: fix the seam\n 1 file changed",
                     tool_use_id="tu_bash"),
        _assistant({"type": "text", "text": "API Error: safeguards flagged this message"}),
    ]


@pytest.fixture
def claude_home(tmp_path: Path) -> Path:
    home = tmp_path / ".claude"
    proj = home / "projects" / "C--proj"
    proj.mkdir(parents=True)
    (proj / "sess-1.jsonl").write_text(
        "\n".join(_transcript_lines()) + "\n", encoding="utf-8"
    )
    plans = home / "plans"
    plans.mkdir()
    (plans / "great-plan.md").write_text("# Plan doc\nsteps...", encoding="utf-8")
    return home


def _harvest(claude_home: Path, tmp_path: Path, **kw):
    h = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out", **kw)
    return h, h.harvest()


def test_extracts_every_kind(claude_home, tmp_path):
    h, stats = _harvest(claude_home, tmp_path)
    assert stats.by_kind == {
        "plan": 1,
        "task": 2,
        "decision": 2,       # question asked + answer
        "user_directive": 1,  # caveat/xml messages excluded
        "agent_report": 1,
        "commit": 1,
        "session_death": 1,
        "plan_file": 1,
    }
    entries = h.ledger.entries()
    report = next(e for e in entries if e["kind"] == "agent_report")
    assert "14 upgrades" in report["body"]
    assert report["title"].startswith('Agent "miner"')
    death = next(e for e in entries if e["kind"] == "session_death")
    assert "API Error" in death["title"]


def test_bodies_are_redacted(claude_home, tmp_path):
    h, _ = _harvest(claude_home, tmp_path)
    raw = h.ledger.ledger_path.read_text(encoding="utf-8")
    assert FAKE_KEY not in raw
    assert "[REDACTED:" in raw


def test_idempotent_rerun_adds_nothing(claude_home, tmp_path):
    h, first = _harvest(claude_home, tmp_path)
    h2 = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    second = h2.harvest()
    assert first.entries_new > 0
    assert second.entries_new == 0
    assert len(h2.ledger.entries()) == first.entries_new


def test_offsets_only_parse_new_lines(claude_home, tmp_path):
    _harvest(claude_home, tmp_path)
    transcript = claude_home / "projects" / "C--proj" / "sess-1.jsonl"
    with transcript.open("a", encoding="utf-8") as f:
        f.write(_assistant(_tool_use("ExitPlanMode", {"plan": "# Plan two"})) + "\n")
    h2 = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    stats = h2.harvest()
    assert stats.entries_new == 1
    assert stats.lines_parsed == 1  # only the appended tail line
    assert stats.by_kind == {"plan": 1}


def test_rewritten_file_is_reread(claude_home, tmp_path):
    h, first = _harvest(claude_home, tmp_path)
    transcript = claude_home / "projects" / "C--proj" / "sess-1.jsonl"
    transcript.write_text(
        _assistant(_tool_use("ExitPlanMode", {"plan": "# Fresh plan"})) + "\n",
        encoding="utf-8",
    )
    h2 = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    stats = h2.harvest()
    assert stats.by_kind == {"plan": 1}


def test_tool_attribution_survives_offset_resume(claude_home, tmp_path):
    """An AskUserQuestion answered AFTER the first harvest still resolves."""
    _harvest(claude_home, tmp_path)
    transcript = claude_home / "projects" / "C--proj" / "sess-1.jsonl"
    with transcript.open("a", encoding="utf-8") as f:
        f.write(_tool_result("answered later: option B", tool_use_id="tu_ask") + "\n")
    h2 = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    stats = h2.harvest()
    assert stats.by_kind == {"decision": 1}


def test_changed_plan_file_creates_new_entry(claude_home, tmp_path):
    _harvest(claude_home, tmp_path)
    (claude_home / "plans" / "great-plan.md").write_text("# Plan doc v2", encoding="utf-8")
    h2 = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    stats = h2.harvest()
    assert stats.by_kind == {"plan_file": 1}


def test_index_regenerated(claude_home, tmp_path):
    h, _ = _harvest(claude_home, tmp_path)
    index = h.ledger.index_path.read_text(encoding="utf-8")
    assert "sess-1" in index
    assert "plan=1" in index
    assert "session_death=1" in index


def test_project_filter(claude_home, tmp_path):
    other = claude_home / "projects" / "C--other"
    other.mkdir()
    (other / "sess-2.jsonl").write_text(
        _assistant(_tool_use("ExitPlanMode", {"plan": "# Other plan"})) + "\n",
        encoding="utf-8",
    )
    h, stats = _harvest(claude_home, tmp_path, projects=["C--other"])
    assert stats.by_kind == {"plan": 1, "plan_file": 1}
    assert all(e["session"] in ("sess-2", "plans") for e in h.ledger.entries())


def test_dry_run_writes_nothing(claude_home, tmp_path):
    h = SessionHarvester(claude_home=claude_home, out_root=tmp_path / "out")
    stats = h.harvest(dry_run=True)
    assert stats.entries_new > 0
    assert not h.ledger.ledger_path.exists()
    assert not h.ledger.offsets_path.exists()


def test_malformed_lines_are_skipped(claude_home, tmp_path):
    transcript = claude_home / "projects" / "C--proj" / "sess-1.jsonl"
    with transcript.open("a", encoding="utf-8") as f:
        f.write("{not json}\n\n")
    _, stats = _harvest(claude_home, tmp_path)
    assert stats.entries_new > 0  # crawl survives garbage


def test_cli_main(claude_home, tmp_path, capsys):
    rc = main([
        "--claude-home", str(claude_home),
        "--out", str(tmp_path / "out"),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "entries: +" in out
    assert "ledger:" in out


def test_ledger_survives_corrupt_line(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    (root / "ledger.jsonl").write_text("garbage\n", encoding="utf-8")
    ledger = RecoveryLedger(root)
    assert ledger.append({"id": "x1", "ts": "", "session": "s", "kind": "plan",
                          "title": "t", "body": "b", "source": "s:1"})
    assert len(ledger.entries()) == 1  # corrupt line ignored, new entry present


def test_iter_values_ignores_unknown_tools():
    obj = json.loads(_assistant(_tool_use("Bash", {"command": "ls"})))
    assert list(_iter_transcript_values(obj, 1, {})) == []
