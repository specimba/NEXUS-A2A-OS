"""Policy core for the NEXUS external browser-AI director.

This module is intentionally side-effect free. CDP, MCP, and provider clients
feed observations into it; tests prove the expensive parts are gated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_MEMORY_PATH = Path.home() / ".nexus" / "browser_ai_supervisor_memory.jsonl"


BRIDGE_TOOL_MAP: dict[str, str] = {
    "ping": "connectivity_probe",
    "registry_debug": "tool_inventory_probe",
    "http_diagnostic": "governed_public_http_probe",
    "task_add": "single_bounded_task_proposal",
}

SETUP_BLOCKERS = {
    "cdp_missing",
    "cdp_wrong_target",
    "auth_missing",
    "bridge_not_listening",
    "bridge_wrong_version",
}

RETRYABLE_BRIDGE_ERRORS = {
    "bridge_timeout",
    "bridge_503",
    "bridge_busy",
    "runtime_evaluate_timeout",
}

ACTIONS = {
    "NOOP_UNCHANGED",
    "WAITING_MODEL",
    "CONTINUE_SENT",
    "ARTIFACT_CAPTURED",
    "BLOCKED_SETUP",
    "RETRY_LATER",
    "ESCALATE_CODEX",
}


@dataclass(frozen=True)
class DirectorConfig:
    source_id: str = "grok-project-nexus"
    provider_cooldown_seconds: int = 20 * 60
    max_provider_calls_per_hour: int = 3
    allowed_providers: tuple[str, ...] = ("internai", "longcat")


@dataclass(frozen=True)
class SourceProfile:
    """Cadence and control policy for one browser-AI source."""

    source_id: str
    cadence_seconds: int
    requires_bridge: bool
    cdp_port: int | None = None
    url_hint: str = ""
    active: bool = True


SOURCE_PROFILES: dict[str, SourceProfile] = {
    "grok-project-nexus": SourceProfile(
        source_id="grok-project-nexus",
        cadence_seconds=10 * 60,
        requires_bridge=True,
        cdp_port=9224,
        url_hint="https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba",
    ),
    "zo-computer-nexus": SourceProfile(
        source_id="zo-computer-nexus",
        cadence_seconds=6 * 60 * 60,
        requires_bridge=False,
        url_hint="https://www.zo.computer/chats/pub_wEKDc2wQF0tGj1o0",
    ),
    "glm52-dashboard": SourceProfile(
        source_id="glm52-dashboard",
        cadence_seconds=6 * 60 * 60,
        requires_bridge=False,
        url_hint="https://chat.z.ai/c/47e59a42-06cb-442e-9b35-3e3d8d2b078f",
    ),
    "gpt-browser-mcp": SourceProfile(
        source_id="gpt-browser-mcp",
        cadence_seconds=6 * 60 * 60,
        requires_bridge=True,
    ),
}


@dataclass(frozen=True)
class MemoryEntry:
    run_id: str
    source_id: str
    started_at: str
    visible_fingerprint: str | None = None
    action: str | None = None
    provider: str = "none"
    provider_calls: int = 0
    blocker: str | None = None
    next_action: str | None = None
    completed_at: str | None = None

    @classmethod
    def from_mapping(cls, item: Mapping[str, Any]) -> "MemoryEntry":
        return cls(
            run_id=str(item.get("run_id", "")),
            source_id=str(item.get("source_id", "")),
            started_at=str(item.get("started_at", "")),
            visible_fingerprint=item.get("visible_fingerprint"),
            action=item.get("action"),
            provider=str(item.get("provider", "none")),
            provider_calls=int(item.get("provider_calls", 0) or 0),
            blocker=item.get("blocker"),
            next_action=item.get("next_action"),
            completed_at=item.get("completed_at"),
        )

@dataclass(frozen=True)
class CycleObservation:
    cdp_status: str
    bridge_status: str = "skipped"
    visible_marker: str = ""
    visible_tail: str = ""
    model_generating: bool = False
    new_artifact_name: str | None = None
    error_code: str | None = None
    requires_bridge: bool = False


@dataclass(frozen=True)
class ProviderWindow:
    calls_last_hour: int = 0
    last_provider_call_at: str | None = None


@dataclass(frozen=True)
class DirectorDecision:
    action: str
    reason: str
    provider_allowed: bool = False
    provider: str = "none"
    bridge_tools: tuple[str, ...] = ()
    codex_escalation: bool = False

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"invalid director action: {self.action}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_fingerprint(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def read_memory_tail(path: Path, limit: int = 20) -> list[MemoryEntry]:
    if not path.exists():
        return []
    rows: list[MemoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        if not line.strip():
            continue
        rows.append(MemoryEntry.from_mapping(json.loads(line)))
    return rows


def provider_window_from_memory(entries: list[MemoryEntry], now: str, *, seconds: int = 3600) -> ProviderWindow:
    try:
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError:
        return ProviderWindow(calls_last_hour=0)

    calls = 0
    last_call_at: str | None = None
    last_call_dt: datetime | None = None
    for entry in entries:
        if entry.provider == "none" or entry.provider_calls <= 0:
            continue
        try:
            started = datetime.fromisoformat(entry.started_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (current - started).total_seconds() <= seconds:
            calls += entry.provider_calls
            if last_call_dt is None or started > last_call_dt:
                last_call_dt = started
                last_call_at = entry.started_at
    return ProviderWindow(calls_last_hour=calls, last_provider_call_at=last_call_at)


def append_memory(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n")


def profile_for_source(source_id: str) -> SourceProfile:
    """Return the configured source profile or a safe 6-hour advisory default."""

    return SOURCE_PROFILES.get(
        source_id,
        SourceProfile(source_id=source_id, cadence_seconds=6 * 60 * 60, requires_bridge=False, active=False),
    )


def cadence_elapsed(entries: list[MemoryEntry | Mapping[str, Any]], now: str, profile: SourceProfile) -> bool:
    """Whether a source is allowed to run based on its last completed record."""

    if not profile.active:
        return False
    if not entries:
        return True
    latest = entries[-1]
    if isinstance(latest, MemoryEntry):
        last = latest.completed_at or latest.started_at
    else:
        last = str(latest.get("completed_at") or latest.get("started_at") or "")
    try:
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
        previous = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (current - previous).total_seconds() >= profile.cadence_seconds


def classify_bridge_status(status: str) -> tuple[str, str | None]:
    """Map observed bridge status to director status and optional error code."""

    normalized = status.strip().lower()
    if normalized in {"ok", "healthy", "live"}:
        return "ok", None
    if normalized in {"missing", "tool_missing"}:
        return "down", "bridge_tool_missing"
    if normalized in {"down", "not_listening"}:
        return "down", "bridge_not_listening"
    if normalized in {"timeout", "busy", "503", "unavailable"}:
        return "retry", "bridge_timeout" if normalized == "timeout" else "bridge_busy"
    if normalized in {"skipped", ""}:
        return "skipped", None
    return "unhealthy", "bridge_wrong_version"


def observation_from_probe(
    probe: Mapping[str, Any],
    *,
    bridge_status: str = "skipped",
    requires_bridge: bool = False,
) -> CycleObservation:
    status = str(probe.get("status", "")).upper()
    if status in {"NOTIFY_SETUP_REQUIRED", "BLOCKED"}:
        return CycleObservation(
            cdp_status="error",
            bridge_status=bridge_status,
            error_code="cdp_missing" if status == "NOTIFY_SETUP_REQUIRED" else "cdp_wrong_target",
            requires_bridge=requires_bridge,
        )

    state = probe.get("state") if isinstance(probe.get("state"), Mapping) else {}
    tail = str(state.get("tailText") or state.get("visibleTail") or "")
    buttons = state.get("buttons") if isinstance(state.get("buttons"), list) else []
    button_labels = " ".join(str(item.get("label") or item.get("text") or "") for item in buttons if isinstance(item, Mapping))
    target = probe.get("target") if isinstance(probe.get("target"), Mapping) else {}
    marker = str(state.get("title") or target.get("title") or "")
    marker = f"{marker}|{button_labels[-1000:]}"

    text_blob = f"{tail}\n{button_labels}".lower()
    model_generating = any(token in text_blob for token in ("thinking", "generating", "stop generating"))
    ready_input = any(
        isinstance(item, Mapping) and str(item.get("aria") or item.get("placeholder") or "").lower().find("ask grok") >= 0
        for item in (state.get("inputs") if isinstance(state.get("inputs"), list) else [])
    )
    if ready_input and "submit" in text_blob:
        model_generating = False

    artifact_match = re.search(r"\b([A-Za-z][A-Za-z0-9_]{8,80}_v\d+)\b", tail)
    artifact_name = artifact_match.group(1) if artifact_match else None

    return CycleObservation(
        cdp_status="ok" if status == "READY" else "error",
        bridge_status=bridge_status,
        visible_marker=marker,
        visible_tail=tail,
        model_generating=model_generating,
        new_artifact_name=artifact_name,
        requires_bridge=requires_bridge,
    )


def classify_setup_or_retry(error_code: str | None) -> str | None:
    if error_code in SETUP_BLOCKERS:
        return "BLOCKED_SETUP"
    if error_code in RETRYABLE_BRIDGE_ERRORS:
        return "RETRY_LATER"
    return None


def provider_in_cooldown(now: str, window: ProviderWindow, cooldown_seconds: int) -> bool:
    if not window.last_provider_call_at:
        return False
    try:
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
        previous = datetime.fromisoformat(window.last_provider_call_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (current - previous).total_seconds() < cooldown_seconds


def grok_connector_tools_missing(tail: str) -> bool:
    """Detect a Grok-side custom connector that is absent or lacks NEXUS tools."""

    lowered = tail.lower()
    if "blocked_tool_not_visible" not in lowered:
        return False
    return any(tool not in lowered for tool in ("ping", "registry_debug", "http_diagnostic", "task_add"))

def choose_provider(observation: CycleObservation, config: DirectorConfig) -> str:
    if observation.new_artifact_name:
        return "internai"
    if len(observation.visible_tail) > 12000 and "longcat" in config.allowed_providers:
        return "longcat"
    return "internai"


def decide_cycle(
    observation: CycleObservation,
    *,
    previous_fingerprint: str | None,
    provider_window: ProviderWindow | None = None,
    now: str | None = None,
    config: DirectorConfig | None = None,
) -> DirectorDecision:
    config = config or DirectorConfig()
    provider_window = provider_window or ProviderWindow()
    now = now or utc_now()

    classified = classify_setup_or_retry(observation.error_code)
    if classified == "BLOCKED_SETUP":
        return DirectorDecision(
            action="BLOCKED_SETUP",
            reason=observation.error_code or "setup_blocker",
            codex_escalation=False,
        )
    if classified == "RETRY_LATER":
        return DirectorDecision(
            action="RETRY_LATER",
            reason=observation.error_code or "retryable_bridge_error",
            codex_escalation=False,
        )

    if observation.cdp_status != "ok":
        return DirectorDecision(action="BLOCKED_SETUP", reason="cdp_not_ok")

    if observation.requires_bridge and observation.bridge_status != "ok":
        reason = "bridge_not_listening" if observation.bridge_status == "down" else "bridge_unhealthy"
        return DirectorDecision(action="BLOCKED_SETUP", reason=reason)

    if observation.requires_bridge and grok_connector_tools_missing(observation.visible_tail):
        return DirectorDecision(
            action="BLOCKED_SETUP",
            reason="grok_connector_tools_missing",
            bridge_tools=tuple(BRIDGE_TOOL_MAP),
        )

    current_fingerprint = stable_fingerprint(
        observation.visible_marker,
        observation.visible_tail[-2048:],
        observation.new_artifact_name or "",
    )

    if previous_fingerprint == current_fingerprint:
        return DirectorDecision(action="NOOP_UNCHANGED", reason="visible_fingerprint_unchanged")

    if observation.model_generating:
        return DirectorDecision(action="WAITING_MODEL", reason="model_generation_in_progress")

    if provider_window.calls_last_hour >= config.max_provider_calls_per_hour:
        return DirectorDecision(action="RETRY_LATER", reason="provider_hourly_cap")

    if provider_in_cooldown(now, provider_window, config.provider_cooldown_seconds):
        return DirectorDecision(action="RETRY_LATER", reason="provider_cooldown")

    provider = choose_provider(observation, config)
    if provider not in config.allowed_providers:
        return DirectorDecision(action="ESCALATE_CODEX", reason="no_allowed_provider", codex_escalation=True)

    bridge_tools = ("ping", "registry_debug")
    if observation.requires_bridge:
        bridge_tools = bridge_tools + ("http_diagnostic",)
    if observation.new_artifact_name:
        bridge_tools = bridge_tools + ("task_add",)

    action = "ARTIFACT_CAPTURED" if observation.new_artifact_name else "CONTINUE_SENT"
    return DirectorDecision(
        action=action,
        reason="material_delta_requires_single_provider_eval",
        provider_allowed=True,
        provider=provider,
        bridge_tools=bridge_tools,
    )



def decide_source_run(
    *,
    source_id: str,
    entries: list[MemoryEntry],
    observation: CycleObservation,
    now: str | None = None,
    provider_window: ProviderWindow | None = None,
    config: DirectorConfig | None = None,
) -> DirectorDecision:
    """Source-aware wrapper around ``decide_cycle`` with cadence protection."""

    now = now or utc_now()
    profile = profile_for_source(source_id)
    if not cadence_elapsed(entries, now, profile):
        return DirectorDecision(action="NOOP_UNCHANGED", reason="cadence_not_elapsed")
    previous_fingerprint = None
    if entries:
        latest = entries[-1]
        if isinstance(latest, MemoryEntry):
            previous_fingerprint = latest.visible_fingerprint
        else:
            previous_fingerprint = latest.get("visible_fingerprint")
    return decide_cycle(
        observation,
        previous_fingerprint=previous_fingerprint,
        provider_window=provider_window,
        now=now,
        config=config or DirectorConfig(source_id=source_id),
    )

def build_outro_record(
    *,
    run_id: str,
    observation: CycleObservation,
    decision: DirectorDecision,
    source_id: str = "grok-project-nexus",
    started_at: str | None = None,
) -> dict[str, Any]:
    started_at = started_at or utc_now()
    return {
        "run_id": run_id,
        "schema": "nexus.browser_ai_supervisor.memory.v1",
        "source_id": source_id,
        "started_at": started_at,
        "completed_at": utc_now(),
        "visible_fingerprint": stable_fingerprint(
            observation.visible_marker,
            observation.visible_tail[-2048:],
            observation.new_artifact_name or "",
        ),
        "action": decision.action,
        "provider": decision.provider,
        "provider_calls": 1 if decision.provider_allowed else 0,
        "bridge_tools": list(decision.bridge_tools),
        "bridge_tool_map": {tool: BRIDGE_TOOL_MAP[tool] for tool in decision.bridge_tools},
        "blocker": decision.reason if decision.action in {"BLOCKED_SETUP", "RETRY_LATER"} else None,
        "next_action": decision.reason,
    }


class DirectorRunner:
    """Tiny injectable runner used by tests and future scheduler glue."""

    def __init__(
        self,
        memory_path: Path,
        observe: Callable[[], CycleObservation],
        provider_eval: Callable[[CycleObservation, str], Mapping[str, Any]],
        *,
        config: DirectorConfig | None = None,
    ) -> None:
        self.memory_path = memory_path
        self.observe = observe
        self.provider_eval = provider_eval
        self.config = config or DirectorConfig()

    def run_once(self, *, run_id: str, now: str | None = None, provider_window: ProviderWindow | None = None) -> dict[str, Any]:
        memory = read_memory_tail(self.memory_path, limit=1)
        observation = self.observe()
        decision = decide_source_run(
            source_id=self.config.source_id,
            entries=memory,
            observation=observation,
            provider_window=provider_window,
            now=now,
            config=self.config,
        )

        provider_result: Mapping[str, Any] | None = None
        if decision.provider_allowed:
            provider_result = self.provider_eval(observation, decision.provider)

        record = build_outro_record(
            run_id=run_id,
            observation=observation,
            decision=decision,
            source_id=self.config.source_id,
            started_at=now,
        )
        if provider_result is not None:
            record["provider_result_status"] = provider_result.get("status", "unknown")
        append_memory(self.memory_path, record)
        return record




def run_egress_probe(url: str, *, method: str = "HEAD", audit_id: str = "director-egress", operator: str = "director") -> dict[str, Any]:
    """Run a governed public egress probe through the existing 7354 bridge.

    This is only called by the wrapper/CLI when explicitly requested. Unit tests
    avoid live networking; the existing bridge tests cover relay behavior.
    """
    from nexus_os.bridge.browser_http_diagnostic import BrowserHTTPDiagnosticRelay

    relay = BrowserHTTPDiagnosticRelay(bridge_url="http://127.0.0.1:7354")
    return relay.execute_governed(url, method=method, audit_id=audit_id, operator=operator, dry_run=False)

def dry_provider_eval(observation: CycleObservation, provider: str) -> Mapping[str, Any]:
    return {
        "status": "dry_run",
        "provider": provider,
        "artifact": observation.new_artifact_name,
    }


def run_from_probe(
    *,
    probe_path: Path,
    memory_path: Path,
    run_id: str,
    bridge_status: str = "skipped",
    requires_bridge: bool = False,
    now: str | None = None,
    egress_url: str | None = None,
    egress_method: str = "HEAD",
) -> dict[str, Any]:
    now = now or utc_now()
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    entries = read_memory_tail(memory_path, limit=100)
    window = provider_window_from_memory(entries, now)
    observation = observation_from_probe(
        probe,
        bridge_status=bridge_status,
        requires_bridge=requires_bridge,
    )
    runner = DirectorRunner(
        memory_path,
        observe=lambda: observation,
        provider_eval=dry_provider_eval,
    )
    record = runner.run_once(run_id=run_id, now=now, provider_window=window)
    if egress_url and bridge_status == "ok":
        audit_id = f"director-egress-{run_id}"
        egress = run_egress_probe(egress_url, method=egress_method, audit_id=audit_id)
        record["egress_probe"] = {
            "url": egress_url,
            "method": egress_method.upper(),
            "audit_id": audit_id,
            "status_code": egress.get("status_code"),
            "access_result": egress.get("access_result"),
            "blocked": bool(egress.get("blocked")),
            "reason": egress.get("reason"),
        }
        egress_record = dict(record)
        egress_record["run_id"] = f"{run_id}-egress"
        egress_record["action"] = "EGRESS_PROBE_RECORDED"
        egress_record["provider"] = "none"
        egress_record["provider_calls"] = 0
        append_memory(memory_path, egress_record)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one NEXUS external browser-AI director policy cycle from a bounded probe JSON.")
    parser.add_argument("--probe-json", required=True, type=Path)
    parser.add_argument("--memory", type=Path, default=DEFAULT_MEMORY_PATH,
                        help=f"Path to JSONL memory file (default: {DEFAULT_MEMORY_PATH})")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bridge-status", default="skipped", choices=["ok", "down", "skipped", "unhealthy"])
    parser.add_argument("--requires-bridge", action="store_true")
    parser.add_argument("--now")
    parser.add_argument("--egress-url")
    parser.add_argument("--egress-method", default="HEAD", choices=["GET", "HEAD"])
    args = parser.parse_args(argv)

    record = run_from_probe(
        probe_path=args.probe_json,
        memory_path=args.memory,
        run_id=args.run_id,
        bridge_status=args.bridge_status,
        requires_bridge=args.requires_bridge,
        now=args.now,
        egress_url=args.egress_url,
        egress_method=args.egress_method,
    )
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))











