#!/usr/bin/env python3
"""
NEXUS OS — Smart Ping Controller (Phase 1)
Demand-driven health check interval management for ModelRelay.

Monitors user activity on NEXUS ports and dynamically adjusts ModelRelay
ping intervals to conserve API quotas and GPU cycles.

State machine:
  ACTIVE (15 min pings) → COOLDOWN (60 min) → SLEEP (4 hours)
  User activity or manual refresh immediately returns to ACTIVE.

Usage:
  python smart_ping.py              # Run in foreground
  python smart_ping.py --daemon     # Run as background service
  python smart_ping.py --status     # Show current state
  python smart_ping.py --refresh    # Force immediate refresh
"""

import sys
import time
import json
import psutil
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

# --- Configuration ---
CONFIG_PATH = Path.home() / ".modelrelay.json"
STATE_PATH = Path(__file__).parent / ".smart_ping_state.json"
LOG_PATH = Path(__file__).parent / "smart_ping.log"

# Ports to monitor for user activity
MONITORED_PORTS = [7352, 7356, 7357]  # ModelRelay, Dashboard, God Mode Proxy

# State transition timeouts (seconds)
ACTIVE_TIMEOUT = 30 * 60      # 30 min → COOLDOWN
COOLDOWN_TIMEOUT = 2 * 60 * 60  # 2 hours → SLEEP

# Interval mapping (seconds) per state and tier
INTERVALS = {
    "ACTIVE": {
        "tier1": 30 * 60,    # 30 min (problematic providers)
        "tier2": 15 * 60,    # 15 min (rate-limited)
        "tier3": 5 * 60,     # 5 min (healthy)
        "ollama": 60 * 60,   # 60 min (local GPU)
    },
    "COOLDOWN": {
        "tier1": 2 * 60 * 60,   # 2 hours
        "tier2": 1 * 60 * 60,   # 1 hour
        "tier3": 15 * 60,       # 15 min
        "ollama": 4 * 60 * 60,  # 4 hours
    },
    "SLEEP": {
        "tier1": 8 * 60 * 60,   # 8 hours
        "tier2": 4 * 60 * 60,   # 4 hours
        "tier3": 1 * 60 * 60,   # 1 hour
        "ollama": 8 * 60 * 60,  # 8 hours
    },
}

# Provider tier classification
PROVIDER_TIERS = {
    "tier1": ["google-ai", "cerebras", "nvidia"],  # Problematic/down providers
    "tier2": ["github-models", "openrouter", "scaleway"],  # Rate-limited
    "tier3": ["mistral", "cloudflare", "groq", "fireworks", "deepinfra", "siliconflow", "sambanova"],  # Healthy
    "ollama": ["ollama"],  # Local GPU
}


@dataclass
class State:
    state: str = "ACTIVE"
    last_activity: float = 0.0
    last_ping_update: float = 0.0
    checks_avoided: int = 0
    total_checks: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "State":
        return cls(**d)

    def save(self):
        STATE_PATH.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls) -> "State":
        if STATE_PATH.exists():
            return cls.from_dict(json.loads(STATE_PATH.read_text()))
        return cls()


class SmartPingController:
    def __init__(self):
        self.state = State.load()
        self.state.last_activity = time.time()
        self.running = True
        self._setup_signal_handlers()
        self.log("Smart Ping Controller initialized")
        self.log(f"Initial state: {self.state.state}")

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self.log(f"Received signal {signum}, shutting down...")
        self.running = False
        self.state.save()

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")

    def check_activity(self) -> bool:
        """Detect active connections on monitored ports."""
        active = False
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == psutil.CONN_ESTABLISHED and conn.laddr:
                    if conn.laddr.port in MONITORED_PORTS:
                        # Exclude connections from our own monitoring
                        if conn.raddr and conn.raddr.port not in MONITORED_PORTS:
                            active = True
                            break
                elif conn.status == psutil.CONN_LISTEN and conn.laddr:
                    if conn.laddr.port in MONITORED_PORTS:
                        # Check if anyone is connected to this listening port
                        active = True
                        break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        return active

    def check_api_activity(self) -> bool:
        """Check for recent API access log entries or HTTP requests."""
        # Check if any process is making HTTP requests to our ports
        try:
            for proc in psutil.process_iter(["pid", "name", "connections"]):
                try:
                    for conn in proc.connections():
                        if conn.status == psutil.CONN_ESTABLISHED:
                            if conn.raddr and conn.raddr.port in MONITORED_PORTS:
                                return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return False

    def record_activity(self, source: str = "auto"):
        """Record user activity and transition to ACTIVE if needed."""
        old_state = self.state.state
        self.state.last_activity = time.time()
        if old_state != "ACTIVE":
            self.state.state = "ACTIVE"
            self.update_relay_intervals()
            self.log(f"State transition: {old_state} → ACTIVE (source: {source})")
            self.state.save()
        elif time.time() - self.state.last_ping_update > 300:  # Update every 5 min even in ACTIVE
            self.update_relay_intervals()

    def check_idle_timeout(self):
        """Check if idle timeout has been reached and transition states."""
        idle = time.time() - self.state.last_activity
        old_state = self.state.state

        if old_state == "ACTIVE" and idle > ACTIVE_TIMEOUT:
            self.state.state = "COOLDOWN"
            self.update_relay_intervals()
            self.log(f"State transition: ACTIVE → COOLDOWN (idle: {self._fmt_duration(idle)})")
            self.state.save()
        elif old_state == "COOLDOWN" and idle > COOLDOWN_TIMEOUT:
            self.state.state = "SLEEP"
            self.update_relay_intervals()
            self.log(f"State transition: COOLDOWN → SLEEP (idle: {self._fmt_duration(idle)})")
            self.state.save()

    def update_relay_intervals(self):
        """Update ModelRelay config with state-appropriate intervals."""
        if not CONFIG_PATH.exists():
            self.log(f"WARNING: Config not found at {CONFIG_PATH}")
            return

        try:
            config = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError as e:
            self.log(f"ERROR: Failed to parse config: {e}")
            return

        intervals = INTERVALS[self.state.state]
        updated = 0

        for provider in config.get("providers", []):
            name = provider.get("name", "").lower()
            tier = self._get_provider_tier(name)
            new_interval = intervals.get(tier, intervals["tier3"])

            if provider.get("pingInterval") != new_interval:
                provider["pingInterval"] = new_interval
                updated += 1

        # Also update default interval if present
        if config.get("defaultPingInterval"):
            config["defaultPingInterval"] = intervals["tier3"]

        if updated > 0:
            CONFIG_PATH.write_text(json.dumps(config, indent=2))
            self.state.last_ping_update = time.time()
            self.log(f"Updated {updated} providers to {self.state.state} intervals")

    def _get_provider_tier(self, name: str) -> str:
        """Classify provider into tier based on name."""
        for tier, providers in PROVIDER_TIERS.items():
            for p in providers:
                if p in name:
                    return tier
        return "tier3"  # Default to healthy tier

    def _fmt_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        else:
            return f"{seconds/3600:.1f}h"

    def get_next_ping_time(self) -> Optional[datetime]:
        """Calculate next scheduled ping time."""
        if not self.state.last_ping_update:
            return None
        intervals = INTERVALS[self.state.state]
        min_interval = min(intervals.values())
        return datetime.fromtimestamp(self.state.last_ping_update + min_interval)

    def run(self):
        """Main monitoring loop."""
        self.log("Starting monitoring loop...")
        self.update_relay_intervals()  # Initial update

        while self.running:
            try:
                # Check for user activity
                if self.check_activity() or self.check_api_activity():
                    self.record_activity("network")

                # Check idle timeouts
                self.check_idle_timeout()

                # Sleep for 1 minute between checks
                time.sleep(60)

            except Exception as e:
                self.log(f"ERROR in main loop: {e}")
                time.sleep(60)

        self.log("Shutdown complete")
        self.state.save()

    def force_refresh(self):
        """Force immediate transition to ACTIVE and refresh."""
        self.record_activity("manual_refresh")
        self.log("Manual refresh triggered - all providers set to ACTIVE intervals")
        return self.state.to_dict()

    def get_status(self) -> dict:
        """Get current controller status."""
        idle = time.time() - self.state.last_activity
        next_ping = self.get_next_ping_time()
        return {
            "state": self.state.state,
            "idle_time": self._fmt_duration(idle),
            "next_ping": next_ping.isoformat() if next_ping else None,
            "checks_avoided": self.state.checks_avoided,
            "total_checks": self.state.total_checks,
            "monitored_ports": MONITORED_PORTS,
            "config_path": str(CONFIG_PATH),
        }


def main():
    parser = argparse.ArgumentParser(description="NEXUS Smart Ping Controller")
    parser.add_argument("--daemon", action="store_true", help="Run as background service")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--refresh", action="store_true", help="Force immediate refresh")
    parser.add_argument("--force-sleep", action="store_true", help="Force SLEEP mode (for testing)")
    args = parser.parse_args()

    controller = SmartPingController()

    if args.status:
        status = controller.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.refresh:
        result = controller.force_refresh()
        print(json.dumps(result, indent=2))
        return

    if args.force_sleep:
        controller.state.state = "SLEEP"
        controller.state.last_activity = time.time() - (8 * 60 * 60)  # 8 hours ago
        controller.update_relay_intervals()
        controller.state.save()
        print("Forced SLEEP mode - intervals set to 4-8 hours")
        return

    if args.daemon:
        print("Starting Smart Ping Controller in daemon mode...")
        print(f"Log file: {LOG_PATH}")
        print(f"State file: {STATE_PATH}")
        print(f"Monitoring ports: {MONITORED_PORTS}")
        print("Press Ctrl+C to stop")
        controller.run()
    else:
        print("Starting Smart Ping Controller in foreground mode...")
        print(f"Log file: {LOG_PATH}")
        print(f"State file: {STATE_PATH}")
        print(f"Monitoring ports: {MONITORED_PORTS}")
        print("Press Ctrl+C to stop")
        controller.run()


if __name__ == "__main__":
    main()
