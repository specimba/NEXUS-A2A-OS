"""Monitor Daemon — periodic Dream Cycle, health checks, and key rotation.

Runs a configurable- interval loop that:
  1. Dream Cycle consolidation (memory → A2A)
  2. Persistent trust memory consolidation
  3. Calibrated Hallucination Detector status
  4. MCP Gateway health (optional — import guard)
  5. Provider health check
  6. Key rotation health check (optional — import guard)
  7. Emit results to an A2A channel

CLI modes:
    python -m nexus_os.monitor_daemon --run-once
    python -m nexus_os.monitor_daemon --daemon --interval 15
    python -m nexus_os.monitor_daemon --install-schedule
    python -m nexus_os.monitor_daemon --status
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("nexus.monitor_daemon")

MONITOR_STATE_FILE = Path(os.path.expanduser("~")) / ".nexus" / "monitor_state.json"


class MonitorDaemon:
    """Periodic consolidation + health check + key rotation daemon."""

    def __init__(
        self,
        interval_minutes: int = 15,
        a2a_channel: str | None = None,
    ):
        self.interval_minutes = interval_minutes
        self.a2a_channel = a2a_channel
        self._last_run: dict[str, Any] | None = None
        self._state_file = MONITOR_STATE_FILE

    # ── individual checks ─────────────────────────────────────────

    def _run_dream_cycle(self) -> dict[str, Any]:
        try:
            from nexus_os.vault.dream_cycle import DreamCycle
            dc = DreamCycle(a2a_channel=self.a2a_channel)
            result = dc.consolidate()
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_trust_consolidation(self) -> dict[str, Any]:
        try:
            from nexus_os.vault.persistent_trust_memory import PersistentMemoryTracks
            ptm = PersistentMemoryTracks()
            result = ptm.consolidate(ttl_hours=72.0)
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_hallucination_check(self) -> dict[str, Any]:
        """Consume real LG verdicts from the relay and emit A2A alerts.

        Reads the verdicts JSONL the relay writes (P2-1 → P2-7 pipeline),
        surfaces recent high/medium-risk entries, and emits alerts on the
        A2A hallucination channel when a high-risk verdict is found.
        """
        try:
            from nexus_os.monitoring.calibrated_hallucination_detector import (
                CalibratedHallucinationDetector,
            )
            chd = CalibratedHallucinationDetector(a2a_channel=self.a2a_channel)
            stats = chd.get_stats()
            history = chd.get_calibration_history()[-5:]

            # P2-7: read real relay verdicts (was stats-only before this slice)
            verdicts = self._consume_relay_verdicts()
            alerts = [v for v in verdicts if v.get("risk_level") in ("high", "medium")]

            if alerts and self.a2a_channel:
                self._emit_hallucination_alerts(alerts)

            return {
                "ok": True,
                "result": {
                    "stats": stats,
                    "calibration_history": history,
                    "recent_verdicts": verdicts[-10:],
                    "alert_count": len(alerts),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _consume_relay_verdicts(self) -> list[dict]:
        """Tail new entries from the relay's hallucination verdicts JSONL.

        Offset-based: the relay owns the file (append + 512KB rotation);
        the daemon only remembers how far it has read, in a sidecar
        offset file. The previous read-then-truncate drain raced the
        relay's appends (verdicts written between read and truncate were
        lost) and fought its rotation rewrite. If the file shrank since
        the last read, a rotation happened — restart from zero (a few
        already-seen lines may repeat; alerts are capped per cycle).
        """
        verdicts_path = Path.home() / ".nexus" / "hallucination_verdicts.jsonl"
        offset_path = Path.home() / ".nexus" / "hallucination_verdicts.offset"
        if not verdicts_path.exists():
            return []
        try:
            try:
                offset = int(offset_path.read_text(encoding="utf-8").strip() or 0)
            except (OSError, ValueError):
                offset = 0
            size = verdicts_path.stat().st_size
            if size < offset:
                offset = 0  # relay rotated the file
            if size == offset:
                return []
            with open(verdicts_path, "r", encoding="utf-8") as f:
                f.seek(offset)
                chunk = f.read()
                new_offset = f.tell()
            verdicts = []
            for line in chunk.splitlines():
                line = line.strip()
                if line:
                    try:
                        verdicts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            offset_path.write_text(str(new_offset), encoding="utf-8")
            return verdicts
        except Exception:
            return []

    def _emit_hallucination_alerts(self, alerts: list[dict]):
        """Emit high/medium-risk hallucination alerts to the A2A channel."""
        try:
            from nexus_os.bridge.a2a_channels import A2AChannelBus
            bus = A2AChannelBus()
            for alert in alerts[-5:]:  # cap at 5 per cycle
                bus.publish(
                    channel_id=self.a2a_channel,
                    sender="monitor_daemon",
                    message=json.dumps({
                        "type": "hallucination-alert",
                        "risk_level": alert.get("risk_level"),
                        "risk_score": alert.get("risk_score"),
                        "reasons": alert.get("reasons", []),
                        "ts": alert.get("ts"),
                        "model": alert.get("model"),
                    }),
                    topic="hallucination",
                )
        except Exception:
            logger.warning("Hallucination A2A alert emit failed", exc_info=True)

    def _run_mcp_gateway_check(self) -> dict[str, Any]:
        try:
            from nexus_os.security.mcp_gateway import MCPGateway
            gw = MCPGateway()
            stats = gw.get_stats()
            cb = gw.get_circuit_breaker_status()
            return {"ok": True, "result": {"stats": stats, "circuit_breaker": cb}}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "importable": False}

    def _run_provider_health_check(self) -> dict[str, Any]:
        try:
            from nexus_os.monitoring.provider_health import get_health_monitor
            health = get_health_monitor()
            status = health.get_status()
            return {"ok": True, "result": status}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_breaker_sync(self) -> dict[str, Any]:
        """P2-4 seam consumer: propagate relay dead-provider knowledge to
        the GMR circuit breaker. The relay server persists breaker state
        to ~/.modelrelay.circuit.json (RELAY_BREAKER_PERSIST); this check
        is the production caller sync_from_relay never had.
        """
        try:
            from nexus_os.gmr.circuit_breaker import AdaptiveCircuitBreaker
            breaker = AdaptiveCircuitBreaker()
            report = breaker.sync_from_relay()
            if report.get("synced") and report.get("dead_providers"):
                logger.warning(
                    "GMR breaker synced %d dead providers from relay state",
                    len(report["dead_providers"]),
                )
            return {"ok": True, "result": report}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_key_rotation_check(self) -> dict[str, Any]:
        try:
            from nexusctl.rotate_keys import cmd_health_check
            result = cmd_health_check()
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "importable": False}

    # ── full cycle ────────────────────────────────────────────────

    def run_once(self) -> dict[str, Any]:
        t0 = time.time()
        cycle_result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        checks = {
            "dream_cycle": self._run_dream_cycle,
            "trust_consolidation": self._run_trust_consolidation,
            "hallucination_detector": self._run_hallucination_check,
            "mcp_gateway": self._run_mcp_gateway_check,
            "provider_health": self._run_provider_health_check,
            "breaker_sync": self._run_breaker_sync,
            "key_rotation": self._run_key_rotation_check,
        }

        for name, fn in checks.items():
            cycle_result["checks"][name] = fn()

        elapsed = time.time() - t0
        cycle_result["elapsed_seconds"] = round(elapsed, 2)
        cycle_result["ok"] = all(c.get("ok") for c in cycle_result["checks"].values())

        self._last_run = cycle_result
        self._persist_state(cycle_result)
        self._emit_to_a2a(cycle_result)

        return cycle_result

    def get_status(self) -> dict[str, Any]:
        if self._last_run:
            return self._last_run
        return self._load_state() or {"ok": False, "message": "no runs yet"}

    # ── daemon loop ───────────────────────────────────────────────

    def run_daemon(self):
        logger.info(
            "Monitor Daemon starting (every %d min)",
            self.interval_minutes,
        )
        while True:
            result = self.run_once()
            logger.info("Monitor cycle: %s", json.dumps(result))
            time.sleep(self.interval_minutes * 60)

    # ── persistence ───────────────────────────────────────────────

    def _persist_state(self, state: dict[str, Any]):
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8",
            )
        except OSError:
            pass

    def _load_state(self) -> dict[str, Any] | None:
        try:
            if self._state_file.exists():
                return json.loads(self._state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
        return None

    # ── A2A emit ──────────────────────────────────────────────────

    def _emit_to_a2a(self, result: dict[str, Any]):
        if not self.a2a_channel:
            return
        try:
            from nexus_os.bridge.a2a_channels import A2AChannelBus
            bus = A2AChannelBus()
            summary = {
                "ok": result.get("ok"),
                "checks": {
                    k: {"ok": v.get("ok")} for k, v in result.get("checks", {}).items()
                },
                "elapsed_seconds": result.get("elapsed_seconds"),
            }
            bus.publish(
                channel_id=self.a2a_channel,
                sender="monitor_daemon",
                message=json.dumps(summary),
                topic="monitor-cycle",
            )
        except Exception:
            logger.warning("A2A emit failed", exc_info=True)


def install_monitor_schedule(interval_minutes: int = 15) -> dict:
    """Install a Windows Scheduled Task that runs --run-once every N minutes."""
    script = str(Path(__file__).resolve())
    python = sys.executable
    task_name = f"NexusMonitorDaemon"
    interval_ts = f"New-TimeSpan -Minutes {interval_minutes}"
    ps = (
        '$action = New-ScheduledTaskAction -Execute "' + python + '" '
        '-Argument "\\"' + script + ' --run-once\\""; '
        '$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) '
        f'-RepetitionInterval ({interval_ts}) '
        '-RepetitionDuration (New-TimeSpan -Days 365); '
        '$settings = New-ScheduledTaskSettingsSet '
        '-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; '
        'Register-ScheduledTask -TaskName "' + task_name + '" '
        '-Action $action -Trigger $trigger -Settings $settings '
        '-Description "Periodic NEXUS monitor: Dream Cycle, health checks, key rotation" -Force'
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
        ok = r.returncode == 0
        return {
            "installed": ok,
            "task_name": task_name,
            "interval_minutes": interval_minutes,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
        }
    except Exception as e:
        return {"installed": False, "error": str(e)}


def cli_main():
    ap = argparse.ArgumentParser(
        description="NEXUS Monitor Daemon — periodic Dream Cycle, health checks, key rotation",
    )
    ap.add_argument("--run-once", action="store_true", help="Run a single monitor cycle")
    ap.add_argument("--daemon", action="store_true", help="Run continuously every --interval minutes")
    ap.add_argument("--interval", type=int, default=15, help="Daemon interval in minutes (default 15)")
    ap.add_argument("--install-schedule", action="store_true", help="Install as Windows scheduled task")
    ap.add_argument("--status", action="store_true", help="Show last run results")
    ap.add_argument("--a2a-channel", default=None, help="A2A channel for emitting results")
    args = ap.parse_args()

    daemon = MonitorDaemon(
        interval_minutes=args.interval,
        a2a_channel=args.a2a_channel,
    )

    if args.install_schedule:
        result = install_monitor_schedule(interval_minutes=args.interval)
        print(json.dumps(result, indent=2))
        return

    if args.status:
        status = daemon.get_status()
        print(json.dumps(status, indent=2, default=str))
        return

    if args.daemon:
        daemon.run_daemon()
        return

    if args.run_once:
        result = daemon.run_once()
        print(json.dumps(result, indent=2, default=str))
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
