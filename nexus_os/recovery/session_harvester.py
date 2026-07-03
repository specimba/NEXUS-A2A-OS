"""Recovery-at-locals session harvester — durable values from local transcripts.

Crawls the local Claude Code state that crashed or cleared sessions leave
behind and extracts the artifacts worth keeping into an append-only,
redacted, idempotent RECOVERY LEDGER:

  - ``~/.claude/projects/<proj>/*.jsonl`` transcripts:
      * plans approved via ExitPlanMode
      * task lists (TaskCreate subjects + TaskUpdate status transitions)
      * operator decisions (AskUserQuestion answers)
      * subagent final reports (<task-notification> <result> bodies —
        the tasks/*.output files they point at are temp and often empty)
      * commits landed (git commit result lines)
      * operator directives (plain user messages)
      * session-death markers (API-error assistant turns) — where to resume
  - ``~/.claude/plans/*.md`` plan documents

Ledger layout (default ``~/.nexus/recovery/``):
  - ``ledger.jsonl``  — one redacted entry per harvested value (append-only)
  - ``offsets.json``  — per-transcript progress (line count + size) so
    reruns only parse new lines; a shrunk/rewritten file is re-read fully
  - ``INDEX.md``      — regenerated per run: per-session kind counts and
    latest titles, newest first

Idempotent: entry ids are content-addressed (sha1 of source + position +
payload), reruns never duplicate. All bodies pass through the central
redactor (nexus_os.security.redaction) before touching disk.

Usage:
    python -m nexus_os.recovery.session_harvester            # harvest all
    python -m nexus_os.recovery.session_harvester --dry-run  # count only
    python -m nexus_os.recovery.session_harvester --project C--Users-...-NEXUS
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from nexus_os.security.redaction import redact

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_HOME = Path.home() / ".claude"
DEFAULT_OUT_ROOT = Path.home() / ".nexus" / "recovery"

#: Body size cap per ledger entry — a ledger is a recovery net, not a mirror.
MAX_BODY_CHARS = 20_000

_COMMIT_LINE_RE = re.compile(r"^\[[^\]\n]+\s+[0-9a-f]{7,40}\]\s.+$", re.MULTILINE)
_TASK_RESULT_RE = re.compile(
    r"<summary>(?P<summary>.*?)</summary>.*?<result>(?P<result>.*?)</result>",
    re.DOTALL,
)


@dataclass
class HarvestStats:
    files_scanned: int = 0
    lines_parsed: int = 0
    entries_new: int = 0
    entries_skipped: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)

    def count(self, kind: str, new: bool) -> None:
        if new:
            self.entries_new += 1
            self.by_kind[kind] = self.by_kind.get(kind, 0) + 1
        else:
            self.entries_skipped += 1


def _entry_id(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()[:20]


def _clip(text: str, limit: int = MAX_BODY_CHARS) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[clipped {len(text) - limit} chars]"


def _content_items(obj: dict) -> list:
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        return content
    return []


def _iter_transcript_values(
    obj: dict,
    lineno: int,
    tool_names: dict[str, str],
) -> Iterator[tuple[str, str, str]]:
    """Yield (kind, title, body) triples for one transcript JSONL object.

    ``tool_names`` maps tool_use ids to tool names across the scan so
    tool_results (which carry no name) can be attributed.
    """
    otype = obj.get("type")

    if otype == "assistant":
        for c in _content_items(obj):
            ctype = c.get("type")
            if ctype == "tool_use":
                tool_names[c.get("id", "")] = c.get("name", "")
                name = c.get("name", "")
                inp = c.get("input") or {}
                if name == "ExitPlanMode" and inp.get("plan"):
                    yield "plan", str(inp["plan"]).splitlines()[0][:120], str(inp["plan"])
                elif name == "TaskCreate" and inp.get("subject"):
                    yield (
                        "task",
                        f"CREATE {inp['subject']}"[:160],
                        json.dumps(inp, ensure_ascii=False),
                    )
                elif name == "TaskUpdate" and inp.get("status"):
                    yield (
                        "task",
                        f"UPDATE #{inp.get('taskId', '?')} -> {inp['status']}",
                        json.dumps(inp, ensure_ascii=False),
                    )
                elif name == "AskUserQuestion":
                    questions = [
                        q.get("question", "")
                        for q in (inp.get("questions") or [])
                        if isinstance(q, dict)
                    ]
                    if questions:
                        yield (
                            "decision",
                            f"ASKED {questions[0][:120]}",
                            json.dumps(questions, ensure_ascii=False),
                        )
            elif ctype == "text":
                text = c.get("text", "")
                if text.startswith("API Error:"):
                    yield "session_death", text.splitlines()[0][:160], text

    elif otype == "user":
        msg = obj.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            stripped = content.strip()
            if "<task-notification>" in stripped:
                m = _TASK_RESULT_RE.search(stripped)
                if m and m.group("result").strip():
                    yield (
                        "agent_report",
                        m.group("summary").strip()[:160],
                        m.group("result"),
                    )
            elif (
                stripped
                and not stripped.startswith("<")
                and len(stripped) >= 20
            ):
                yield "user_directive", stripped.splitlines()[0][:160], stripped
        elif isinstance(content, list):
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_result":
                    continue
                text = _tool_result_text(c)
                if not text:
                    continue
                name = tool_names.get(c.get("tool_use_id", ""), "")
                if name == "AskUserQuestion":
                    yield "decision", "ANSWERED " + text.splitlines()[0][:140], text
                else:
                    for cm in _COMMIT_LINE_RE.findall(text):
                        yield "commit", cm[:160], cm


def _tool_result_text(c: dict) -> str:
    content = c.get("content")
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, list):
        for cc in content:
            if isinstance(cc, str):
                parts.append(cc)
            elif isinstance(cc, dict) and cc.get("type") == "text":
                parts.append(cc.get("text", ""))
    return "\n".join(parts)


class RecoveryLedger:
    """Append-only redacted ledger with content-addressed idempotence."""

    def __init__(self, out_root: Path):
        self.root = Path(out_root)
        self.ledger_path = self.root / "ledger.jsonl"
        self.offsets_path = self.root / "offsets.json"
        self.index_path = self.root / "INDEX.md"
        self._seen_ids: set[str] = set()
        self._entries_cache: list[dict] | None = None
        if self.ledger_path.exists():
            with self.ledger_path.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        self._seen_ids.add(json.loads(line)["id"])
                    except Exception:
                        continue

    def load_offsets(self) -> dict[str, dict]:
        if self.offsets_path.exists():
            try:
                return json.loads(self.offsets_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_offsets(self, offsets: dict[str, dict]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.offsets_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(offsets, indent=2), encoding="utf-8")
        tmp.replace(self.offsets_path)

    def append(self, entry: dict) -> bool:
        """Append a redacted entry; returns False if already present."""
        if entry["id"] in self._seen_ids:
            return False
        self.root.mkdir(parents=True, exist_ok=True)
        entry = dict(entry)
        entry["title"] = redact(entry.get("title", ""))
        entry["body"] = redact(_clip(entry.get("body", "")))
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._seen_ids.add(entry["id"])
        self._entries_cache = None
        return True

    def entries(self) -> list[dict]:
        if self._entries_cache is None:
            out: list[dict] = []
            if self.ledger_path.exists():
                with self.ledger_path.open(encoding="utf-8") as f:
                    for line in f:
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            continue
            self._entries_cache = out
        return self._entries_cache

    def rebuild_index(self) -> None:
        """Regenerate INDEX.md: per-session kind counts + latest titles."""
        sessions: dict[str, list[dict]] = {}
        for e in self.entries():
            sessions.setdefault(e.get("session", "?"), []).append(e)

        lines = [
            "# NEXUS Recovery Ledger Index",
            "",
            f"_Regenerated {datetime.now(timezone.utc).isoformat(timespec='seconds')} — "
            f"{sum(len(v) for v in sessions.values())} entries across "
            f"{len(sessions)} sources. Full bodies in `ledger.jsonl`._",
            "",
        ]
        def newest(entries: list[dict]) -> str:
            return max((e.get("ts") or "" for e in entries), default="")

        for session, entries in sorted(
            sessions.items(), key=lambda kv: newest(kv[1]), reverse=True
        ):
            kinds: dict[str, int] = {}
            for e in entries:
                kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
            kind_summary = ", ".join(f"{k}={n}" for k, n in sorted(kinds.items()))
            lines.append(f"## {session}")
            lines.append(f"_{kind_summary}_")
            lines.append("")
            for e in entries[-12:]:
                lines.append(f"- `{e['kind']}` {e.get('title', '')}")
            lines.append("")
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text("\n".join(lines), encoding="utf-8")


class SessionHarvester:
    """Crawl local Claude state into a RecoveryLedger."""

    def __init__(
        self,
        claude_home: Path = DEFAULT_CLAUDE_HOME,
        out_root: Path = DEFAULT_OUT_ROOT,
        projects: list[str] | None = None,
    ):
        self.claude_home = Path(claude_home)
        self.projects = projects
        self.ledger = RecoveryLedger(Path(out_root))

    # ------------------------------------------------------------ sources

    def _transcript_files(self) -> list[Path]:
        projects_root = self.claude_home / "projects"
        if not projects_root.exists():
            return []
        dirs = (
            [projects_root / p for p in self.projects]
            if self.projects
            else [d for d in projects_root.iterdir() if d.is_dir()]
        )
        files: list[Path] = []
        for d in dirs:
            files.extend(sorted(d.glob("*.jsonl")))
        return files

    def _plan_files(self) -> list[Path]:
        plans = self.claude_home / "plans"
        if not plans.exists():
            return []
        return sorted(plans.glob("*.md"))

    # ------------------------------------------------------------ harvest

    def harvest(self, dry_run: bool = False) -> HarvestStats:
        stats = HarvestStats()
        offsets = self.ledger.load_offsets()

        for path in self._transcript_files():
            self._harvest_transcript(path, offsets, stats, dry_run)
        for path in self._plan_files():
            self._harvest_plan_file(path, stats, dry_run)

        if not dry_run:
            self.ledger.save_offsets(offsets)
            self.ledger.rebuild_index()
        return stats

    def _harvest_transcript(
        self,
        path: Path,
        offsets: dict[str, dict],
        stats: HarvestStats,
        dry_run: bool,
    ) -> None:
        key = str(path)
        state = offsets.get(key, {})
        size = path.stat().st_size
        start_line = int(state.get("lines", 0))
        if size < int(state.get("size", 0)):
            start_line = 0  # rewritten/truncated file: re-read fully
        stats.files_scanned += 1

        session = path.stem
        # tool_use id -> name attribution must see the WHOLE file even when
        # resuming from an offset, so results always find their tool names.
        tool_names: dict[str, str] = {}
        lineno = 0
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for raw in f:
                    lineno += 1
                    process = lineno > start_line
                    if not (process or '"tool_use"' in raw):
                        continue
                    try:
                        obj = json.loads(raw)
                    except Exception:
                        continue
                    if not process:
                        # prefix pass: only refresh tool_use attribution
                        for c in _content_items(obj):
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                tool_names[c.get("id", "")] = c.get("name", "")
                        continue
                    stats.lines_parsed += 1
                    ts = obj.get("timestamp") or ""
                    for kind, title, body in _iter_transcript_values(
                        obj, lineno, tool_names
                    ):
                        entry = {
                            "id": _entry_id(session, kind, str(lineno), body[:512]),
                            "ts": ts,
                            "session": session,
                            "kind": kind,
                            "title": title,
                            "body": body,
                            "source": f"{path.name}:{lineno}",
                        }
                        if dry_run:
                            stats.count(kind, entry["id"] not in self.ledger._seen_ids)
                        else:
                            stats.count(kind, self.ledger.append(entry))
        except OSError as exc:
            logger.warning("unreadable transcript %s: %s", path, exc)
            return

        if not dry_run:
            offsets[key] = {"lines": lineno, "size": size}

    def _harvest_plan_file(self, path: Path, stats: HarvestStats, dry_run: bool) -> None:
        stats.files_scanned += 1
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("unreadable plan file %s: %s", path, exc)
            return
        digest = hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()[:12]
        entry = {
            "id": _entry_id("plans", path.name, digest),
            "ts": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat(timespec="seconds"),
            "session": "plans",
            "kind": "plan_file",
            "title": path.stem[:160],
            "body": body,
            "source": path.name,
        }
        if dry_run:
            stats.count("plan_file", entry["id"] not in self.ledger._seen_ids)
        else:
            stats.count("plan_file", self.ledger.append(entry))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--claude-home", type=Path, default=DEFAULT_CLAUDE_HOME)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument(
        "--project",
        action="append",
        default=None,
        help="project dir name under <claude-home>/projects (repeatable; default all)",
    )
    ap.add_argument("--dry-run", action="store_true", help="count, write nothing")
    args = ap.parse_args(argv)

    harvester = SessionHarvester(
        claude_home=args.claude_home, out_root=args.out, projects=args.project
    )
    stats = harvester.harvest(dry_run=args.dry_run)
    print(
        f"scanned {stats.files_scanned} files, parsed {stats.lines_parsed} new lines"
    )
    print(
        f"entries: +{stats.entries_new} new, {stats.entries_skipped} already present"
    )
    for kind, n in sorted(stats.by_kind.items()):
        print(f"  {kind}: +{n}")
    if not args.dry_run:
        print(f"ledger: {harvester.ledger.ledger_path}")
        print(f"index:  {harvester.ledger.index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
