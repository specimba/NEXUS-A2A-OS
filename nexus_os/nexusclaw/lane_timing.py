"""Per-agent lane response timing — rolling medians for adaptive wait budgets."""
from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENTS_PATH = REPO_ROOT / "NEXUSlogs" / "lane_timing" / "events.jsonl"

# Future roster hooks (browser + API lanes)
KNOWN_AGENTS = frozenset(
    {
        "grok",
        "zo",
        "chatgpt",
        "meta_muse_spark",
        "glm_5_2",
        "kimi_2_6",
        "apodex_deep",
        "alphaxiv_browser",
    }
)

TASK_CLASSES = frozenset(
    {
        "smoke",
        "handoff",
        "nudge",
        "coding",
        "deep_search",
        "audit",
        "paper_review",
        "general",
    }
)

DEFAULT_BASELINE_SEC: dict[tuple[str, str], float] = {
    ("grok", "smoke"): 90.0,
    ("grok", "handoff"): 120.0,
    ("grok", "nudge"): 45.0,
    ("grok", "deep_search"): 240.0,
    ("zo", "handoff"): 600.0,
    ("zo", "smoke"): 300.0,
    ("zo", "coding"): 900.0,
    ("chatgpt", "audit"): 180.0,
    ("chatgpt", "handoff"): 120.0,
    ("chatgpt", "smoke"): 90.0,
}


@dataclass(frozen=True)
class LaneTimingEvent:
    ts: str
    agent_id: str
    task_class: str
    status: str  # RESPONSE_READY | TIMEOUT
    elapsed_sec: float
    poll_count: int
    required: str = ""
    poll_interval_sec: float = 4.0
    notes: str = ""

    def normalized_agent(self) -> str:
        a = self.agent_id.lower().replace(".", "_").replace("-", "_")
        for key in ("grok", "zo", "chatgpt"):
            if key in a:
                return key
        return a


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(event: LaneTimingEvent, path: Path = DEFAULT_EVENTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(event), ensure_ascii=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_events(path: Path = DEFAULT_EVENTS_PATH, limit: int = 5000) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def median_elapsed(
    agent_id: str,
    task_class: str,
    *,
    path: Path = DEFAULT_EVENTS_PATH,
    only_ready: bool = True,
    window: int = 40,
) -> float | None:
    agent = agent_id.lower()
    tc = task_class.lower()
    rows = load_events(path)
    samples: list[float] = []
    for row in reversed(rows):
        if str(row.get("agent_id", "")).lower() != agent and agent not in str(row.get("agent_id", "")).lower():
            continue
        if str(row.get("task_class", "")).lower() != tc:
            continue
        if only_ready and str(row.get("status", "")) != "RESPONSE_READY":
            continue
        try:
            samples.append(float(row["elapsed_sec"]))
        except (KeyError, TypeError, ValueError):
            continue
        if len(samples) >= window:
            break
    if len(samples) < 2:
        return None
    return float(statistics.median(samples))


def suggest_max_wait_sec(
    agent_id: str,
    task_class: str,
    *,
    path: Path = DEFAULT_EVENTS_PATH,
    multiplier: float = 1.35,
    floor_sec: float = 60.0,
    ceiling_sec: float = 1800.0,
) -> float:
    agent = agent_id.lower()
    if "grok" in agent:
        agent = "grok"
    elif "zo" in agent:
        agent = "zo"
    elif "chatgpt" in agent:
        agent = "chatgpt"
    tc = task_class.lower()
    med = median_elapsed(agent, tc, path=path)
    base = DEFAULT_BASELINE_SEC.get((agent, tc)) or DEFAULT_BASELINE_SEC.get((agent, "general")) or 180.0
    target = (med * multiplier) if med is not None else base
    return max(floor_sec, min(ceiling_sec, target))


def record_from_wait_json(payload: dict[str, Any], task_class: str = "general") -> LaneTimingEvent:
    ev = LaneTimingEvent(
        ts=_utc_now(),
        agent_id=str(payload.get("agentId") or "unknown"),
        task_class=task_class,
        status=str(payload.get("status") or "UNKNOWN"),
        elapsed_sec=float(payload.get("elapsedSec") or 0),
        poll_count=int(payload.get("pollCount") or 0),
        required=str(payload.get("required") or ""),
    )
    append_event(ev)
    return ev