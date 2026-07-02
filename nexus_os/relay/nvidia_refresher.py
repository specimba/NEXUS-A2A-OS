#!/usr/bin/env python3
"""
NEXUS OS — Dynamic NVIDIA Model Refresher
Handles NVIDIA models that are temporarily down (404) without deleting them.

Strategy:
  - Keep all NVIDIA models in config
  - Mark 404 models as "suspended" (skip daily pings, check weekly)
  - If model comes back online → move to active list
  - If stays down for 30 days → mark "deprecated" (keep for history)
  - Check suspended models every 7 days (not daily, to save API quota)

Usage:
  python nvidia_refresher.py --status      # Show suspended/deprecated lists
  python nvidia_refresher.py --check     # Check suspended models now
  python nvidia_refresher.py --restore-all # Restore all deprecated models to check queue
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

CONFIG_PATH = Path.home() / ".modelrelay.json"
SUSPEND_PATH = Path(__file__).parent / ".nvidia_suspended.json"
DEPRECATED_PATH = Path(__file__).parent / ".nvidia_deprecated.json"
# Hard-fail default: no committed key fallback. The previously hardcoded
# key was leaked in git history and must be rotated (audit 2026-07-02).
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/models"

# --- Data structures ---

class SuspendedModel:
    def __init__(self, model_id, first_suspended=None, last_checked=None, checks=0, status="suspended"):
        self.model_id = model_id
        self.first_suspended = first_suspended or datetime.now().isoformat()
        self.last_checked = last_checked or datetime.now().isoformat()
        self.checks = checks
        self.status = status  # suspended, deprecated, restored

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "first_suspended": self.first_suspended,
            "last_checked": self.last_checked,
            "checks": self.checks,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def days_suspended(self) -> int:
        first = datetime.fromisoformat(self.first_suspended)
        return (datetime.now() - first).days

    def days_since_check(self) -> int:
        last = datetime.fromisoformat(self.last_checked)
        return (datetime.now() - last).days


class NvidiaRefresher:
    def __init__(self):
        self.suspended = self._load_suspended()
        self.deprecated = self._load_deprecated()

    def _load_suspended(self) -> dict:
        if SUSPEND_PATH.exists():
            data = json.loads(SUSPEND_PATH.read_text())
            return {k: SuspendedModel.from_dict(v) for k, v in data.items()}
        return {}

    def _load_deprecated(self) -> dict:
        if DEPRECATED_PATH.exists():
            return json.loads(DEPRECATED_PATH.read_text())
        return {}

    def _save(self):
        SUSPEND_PATH.write_text(json.dumps({k: v.to_dict() for k, v in self.suspended.items()}, indent=2))
        DEPRECATED_PATH.write_text(json.dumps(self.deprecated, indent=2))

    def get_nvidia_models_from_config(self) -> list:
        """Get all NVIDIA model IDs from ModelRelay config."""
        if not CONFIG_PATH.exists():
            return []
        config = json.loads(CONFIG_PATH.read_text())
        providers = config.get("providers", {})
        nvidia = providers.get("nvidia", {})
        models = nvidia.get("models", nvidia.get("modelList", []))
        return [m for m in models if isinstance(m, str)]

    def check_model(self, model_id: str) -> dict:
        """Check if a single NVIDIA model is accessible."""
        if not NVIDIA_API_KEY:
            return {"status": "error", "model_id": model_id, "error": "NVIDIA_API_KEY not set (no committed fallback)"}
        url = f"https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Say OK."}],
            "max_tokens": 1,
            "temperature": 0.0,
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            if r.status_code == 200:
                return {"status": "up", "model_id": model_id, "response_time_ms": r.elapsed.total_seconds() * 1000}
            elif r.status_code == 404:
                return {"status": "down", "model_id": model_id, "error": "model not found (404)"}
            elif r.status_code == 429:
                return {"status": "rate_limited", "model_id": model_id, "error": "rate limited (429)"}
            else:
                return {"status": "error", "model_id": model_id, "http_code": r.status_code, "error": r.text[:200]}
        except requests.exceptions.Timeout:
            return {"status": "timeout", "model_id": model_id, "error": "timeout after 15s"}
        except Exception as e:
            return {"status": "error", "model_id": model_id, "error": str(e)}

    def check_all(self, force=False):
        """Check all suspended models. Skip if checked within 7 days unless forced."""
        to_check = []
        for mid, sm in self.suspended.items():
            if sm.status == "suspended" and (sm.days_since_check() >= 7 or force):
                to_check.append(mid)
            elif sm.status == "deprecated" and force:
                to_check.append(mid)

        if not to_check:
            print("No models to check. Use --force to check anyway.")
            return

        print(f"Checking {len(to_check)} models...")
        restored = []
        still_down = []
        newly_deprecated = []

        for mid in to_check:
            result = self.check_model(mid)
            sm = self.suspended[mid]
            sm.last_checked = datetime.now().isoformat()
            sm.checks += 1

            if result["status"] == "up":
                print(f"  ✅ {mid}: RESTORED (response: {result.get('response_time_ms', 0):.0f}ms)")
                restored.append(mid)
                sm.status = "restored"
            elif sm.days_suspended() >= 30 and sm.status == "suspended":
                print(f"  ⚠️ {mid}: Deprecated (down for {sm.days_suspended()} days)")
                newly_deprecated.append(mid)
                sm.status = "deprecated"
                self.deprecated[mid] = sm.to_dict()
                del self.suspended[mid]
            else:
                print(f"  ❌ {mid}: still down ({sm.days_suspended()} days, {sm.checks} checks)")
                still_down.append(mid)

        self._save()
        print(f"\nSummary: {len(restored)} restored, {len(still_down)} still down, {len(newly_deprecated)} deprecated")

    def suspend_model(self, model_id: str, reason: str = "404"):
        """Mark a model as suspended (called when health check returns 404)."""
        if model_id in self.suspended or model_id in self.deprecated:
            return
        sm = SuspendedModel(model_id)
        self.suspended[model_id] = sm
        self._save()
        print(f"Suspended {model_id} (reason: {reason})")

    def restore_model(self, model_id: str):
        """Restore a model from suspended/deprecated to active."""
        if model_id in self.suspended:
            del self.suspended[model_id]
        if model_id in self.deprecated:
            del self.deprecated[model_id]
        self._save()
        print(f"Restored {model_id} to active list")

    def status(self):
        """Print status of all suspended and deprecated models."""
        print("=" * 60)
        print("NVIDIA Model Refresher Status")
        print("=" * 60)
        print(f"\nSuspended models ({len(self.suspended)}):")
        for mid, sm in sorted(self.suspended.items(), key=lambda x: x[1].days_suspended(), reverse=True):
            print(f"  {mid:50s} | {sm.days_suspended():3d} days | {sm.checks:2d} checks | {sm.status}")

        print(f"\nDeprecated models ({len(self.deprecated)}):")
        for mid, info in sorted(self.deprecated.items(), key=lambda x: x[1].get("first_suspended", ""), reverse=True):
            days = (datetime.now() - datetime.fromisoformat(info["first_suspended"])).days
            print(f"  {mid:50s} | {days:3d} days | {info['checks']:2d} checks | deprecated")

        print(f"\nNext check: {7} days after last check for suspended models")
        print(f"Auto-deprecate after: 30 days of being down")


def main():
    parser = argparse.ArgumentParser(description="NVIDIA Dynamic Model Refresher")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--check", action="store_true", help="Check suspended models (7-day interval)")
    parser.add_argument("--force", action="store_true", help="Force check even if not due")
    parser.add_argument("--suspend", help="Manually suspend a model ID")
    parser.add_argument("--restore", help="Restore a model to active list")
    parser.add_argument("--restore-all", action="store_true", help="Restore all deprecated models")
    args = parser.parse_args()

    refresher = NvidiaRefresher()

    if args.status:
        refresher.status()
    elif args.check:
        refresher.check_all(force=args.force)
    elif args.suspend:
        refresher.suspend_model(args.suspend)
    elif args.restore:
        refresher.restore_model(args.restore)
    elif args.restore_all:
        for mid in list(refresher.deprecated.keys()):
            refresher.restore_model(mid)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
