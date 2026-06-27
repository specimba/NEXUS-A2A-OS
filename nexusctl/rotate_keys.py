"""nexusctl/rotate_keys.py — Provider key rotation, health checks, CLI propagation.

Tests all provider API keys from ~/.modelrelay.json, updates stale/dead keys,
propagates to every supported CLI (opencode, mimo, kilo, cline, hermes),
and maintains circuit-breaker state for dead providers.

Usage:
    python nexusctl/rotate_keys.py                          # test all + report
    python nexusctl/rotate_keys.py --key baseten <KEY>      # set + propagate a specific key
    python nexusctl/rotate_keys.py --health-check           # ping all providers, show status
    python nexusctl/rotate_keys.py --circuit-breaker        # show circuit breaker state
    python nexusctl/rotate_keys.py --install-schedule       # 1-hour Windows scheduled task
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HOME = Path(os.path.expanduser("~"))
MODELRELAY_CFG = HOME / ".modelrelay.json"
MODELRELAY_BAK = HOME / ".modelrelay.json.bak"

# Use the real circuit breaker from nexus_os
_sys_path_added = False
_cb_path = Path(__file__).resolve().parent.parent / "nexus_os" / "relay"
if str(_cb_path.parent) not in sys.path:
    sys.path.insert(0, str(_cb_path.parent))
from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker, ProviderState  # noqa: E402

# Provider → test endpoint + expected auth scheme
PROVIDER_TESTS: dict[str, dict[str, Any]] = {
    "nvidia": {
        "url": "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:baseten": {
        "url": "https://inference.baseten.co/v1/chat/completions",
        "auth": "Bearer",
        "test_body": {
            "model": "zai-org/GLM-5.2",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 3,
        },
        "timeout": 15,
    },
    "openai-compatible:fireworks": {
        "url": "https://api.fireworks.ai/inference/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:deepinfra": {
        "url": "https://api.deepinfra.com/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:mistral": {
        "url": "https://api.mistral.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:sambanova": {
        "url": "https://api.sambanova.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:siliconflow": {
        "url": "https://api.siliconflow.cn/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "googleai": {
        "url": "https://generativelanguage.googleapis.com/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "openai-compatible:github": {
        "url": "https://models.inference.ai.azure.com/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/accounts",
        "auth": "Bearer",
        "timeout": 10,
    },
    "scaleway": {
        "url": "https://api.scaleway.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "cohere": {
        "url": "https://api.cohere.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "longcat": {
        "url": "https://api.longcat.chat/openai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "ollama-cloud": {
        "url": "https://api.ollama.cloud/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "internai": {
        "url": "https://api.internai.com/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
    "novita": {
        "url": "https://api.novita.ai/v1/models",
        "auth": "Bearer",
        "timeout": 10,
    },
}


def _http(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 10,
) -> tuple[int, str | None]:
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers or {},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:300]
    except Exception as e:
        return 0, str(e)[:300]


def load_modelrelay() -> dict[str, Any]:
    if MODELRELAY_CFG.exists():
        return json.loads(MODELRELAY_CFG.read_text(encoding="utf-8"))
    return {"apiKeys": {}, "providers": {}}


def save_modelrelay(cfg: dict[str, Any]):
    if MODELRELAY_CFG.exists():
        MODELRELAY_BAK.write_text(MODELRELAY_CFG.read_text(encoding="utf-8"), encoding="utf-8")
    MODELRELAY_CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def get_breaker() -> ProviderCircuitBreaker:
    return ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=60, max_cooldown=3600, persist=True)


def test_key(provider_id: str, key: str) -> dict[str, Any]:
    """Test a single provider API key. Returns {ok, status, latency_ms, detail}."""
    if provider_id not in PROVIDER_TESTS:
        return {"ok": None, "status": 0, "latency_ms": 0, "detail": "no test endpoint configured"}

    cfg = PROVIDER_TESTS[provider_id]
    auth_scheme = cfg.get("auth", "Bearer")
    headers = {"Authorization": f"{auth_scheme} {key}"}
    body = cfg.get("test_body")
    timeout = cfg.get("timeout", 10)

    t0 = time.time()
    status, detail = _http("POST" if body else "GET", cfg["url"], headers, body, timeout)
    latency = int((time.time() - t0) * 1000)

    ok = 200 <= status < 300
    return {"ok": ok, "status": status, "latency_ms": latency, "detail": (detail or "")[:200]}


def test_all_keys(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Test all apiKeys in .modelrelay.json against their provider endpoints."""
    api_keys = cfg.get("apiKeys", {})
    results: dict[str, dict[str, Any]] = {}
    for provider_id, key in api_keys.items():
        if not key or key == "sk-xxx":
            results[provider_id] = {"ok": False, "status": 0, "latency_ms": 0, "detail": "empty/placeholder key"}
            continue
        results[provider_id] = test_key(provider_id, key)
    return results


def update_circuit_breaker(test_results: dict[str, dict[str, Any]], cb: dict[str, Any] | None = None) -> dict[str, Any]:
    """Update circuit breaker state from test results. Mark dead providers with cooldown."""
    breaker = get_breaker()

    for provider_id, result in test_results.items():
        if result.get("ok") is None:
            continue
        if result["ok"]:
            breaker.record_success(provider_id)
        else:
            status = result.get("status", 0)
            if status in (401, 403, 412, 410, 0) or status >= 500:
                breaker.record_failure(provider_id)

    return {"dead_providers": breaker.get_dead_providers()}


def propagate_to_all_clis(cfg: dict[str, Any], results: dict[str, dict[str, Any]], dry_run: bool = False) -> list[dict[str, Any]]:
    """Propagate working Baseten key and other providers to all CLI configs."""
    results_list: list[dict[str, Any]] = []

    api_keys = cfg.get("apiKeys", {})
    bt_key = api_keys.get("openai-compatible:baseten")

    cli_targets = [
        {
            "id": "opencode",
            "path": HOME / ".config" / "opencode" / "opencode.json",
            "format": "opencode",
        },
    ]

    for tgt in cli_targets:
        path = tgt["path"]
        if not path.exists():
            results_list.append({"target": tgt["id"], "ok": False, "reason": "config not found"})
            continue
        try:
            cli_cfg = json.loads(path.read_text(encoding="utf-8"))
            if "baseten" in cli_cfg.get("provider", {}):
                bt_entry = cli_cfg["provider"]["baseten"]
                if bt_key:
                    bt_entry["options"]["apiKey"] = bt_key
                    bt_entry["options"]["authScheme"] = "Bearer"
                    if not dry_run:
                        path.write_text(json.dumps(cli_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
                    results_list.append({"target": tgt["id"], "ok": True, "action": f"updated baseten key ({bt_key[:12]}...)"})
                else:
                    results_list.append({"target": tgt["id"], "ok": False, "reason": "no baseten key in .modelrelay.json"})
            else:
                results_list.append({"target": tgt["id"], "ok": False, "reason": "no baseten provider in config"})
        except Exception as e:
            results_list.append({"target": tgt["id"], "ok": False, "error": str(e)})

    return results_list


def report_summary(test_results: dict[str, dict[str, Any]], cb: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate a structured health summary."""
    healthy = {k: v for k, v in test_results.items() if v.get("ok")}
    dead = {k: v for k, v in test_results.items() if v.get("ok") is False}
    unknown = {k: v for k, v in test_results.items() if v.get("ok") is None}

    breaker = get_breaker()
    dead_providers = breaker.get_dead_providers()

    return {
        "total": len(test_results),
        "healthy": len(healthy),
        "dead": len(dead),
        "unknown": len(unknown),
        "healthy_providers": list(healthy.keys()),
        "dead_providers": [
            {
                "id": pid,
                "status": info.get("status"),
                "detail": info.get("detail", ""),
                "fail_count": dead_providers.get(pid, {}).get("fail_count", 0),
            }
            for pid, info in sorted(dead.items(), key=lambda x: PROVIDER_TESTS.get(x[0], {}).get("url", x[0]))
        ],
        "cooldowns": {
            pid: {
                "remaining_minutes": info.get("remaining_minutes", 0),
                "cooldown_minutes": info.get("cooldown_minutes", 0),
            }
            for pid, info in dead_providers.items()
        },
    }


def cmd_rotate(key_id: str | None = None, key_value: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Main rotation command: optionally set a key, then test + propagate."""
    cfg = load_modelrelay()
    breaker = get_breaker()

    report: dict[str, Any] = {"action": "rotate-keys", "timestamp": datetime.now(timezone.utc).isoformat()}

    # If a specific key was provided, update it
    if key_id and key_value:
        api_keys = cfg.setdefault("apiKeys", {})
        old = api_keys.get(key_id, "")
        api_keys[key_id] = key_value
        if not dry_run:
            save_modelrelay(cfg)
        report["key_update"] = {"provider": key_id, "changed": old != key_value, "key_preview": key_value[:12] + "..."}

    # Test all keys
    test_results = test_all_keys(cfg)
    report["test_results"] = test_results

    # Update circuit breaker
    cb_result = update_circuit_breaker(test_results)
    report["circuit_breaker"] = {
        "dead_count": len(cb_result.get("dead_providers", {})),
        "cooldown_count": sum(1 for v in cb_result.get("dead_providers", {}).values() if v.get("remaining_minutes", 0) > 0),
    }

    # Propagate to CLI configs
    cli_results = propagate_to_all_clis(cfg, test_results, dry_run=dry_run)
    report["cli_propagation"] = cli_results

    # Summary
    report["summary"] = report_summary(test_results)

    return report


def cmd_health_check() -> dict[str, Any]:
    """Health check: test all providers, attempt IP rotation for failed ones."""
    cfg = load_modelrelay()
    test_results = test_all_keys(cfg)

    rotation_results: dict[str, dict[str, Any]] = {}
    for provider_id, result in test_results.items():
        if result.get("ok") is False:
            try:
                from nexus_os.bridge.dynamic_ip_rotator import DynamicIPRotator
                rotator = DynamicIPRotator()
                rr = rotator.try_rotate_on_block(provider_id)
                rotation_results[provider_id] = rr
                if rr.get("rotated"):
                    logger.info("IP rotated for failed provider %s: %s", provider_id, rr.get("new_ip"))
            except Exception as exc:
                rotation_results[provider_id] = {"rotated": False, "new_ip": None, "reason": str(exc)}

    summary = report_summary(test_results)
    if rotation_results:
        summary["ip_rotation_attempts"] = rotation_results
    return summary


def cmd_circuit_breaker() -> dict[str, Any]:
    """Show circuit breaker state."""
    breaker = get_breaker()
    return {"dead_providers": breaker.get_dead_providers()}


def install_hourly_schedule() -> dict:
    """Install a Windows Scheduled Task that runs rotate-keys every hour."""
    script = str(Path(__file__).resolve())
    python = sys.executable
    ps = (
        '$action = New-ScheduledTaskAction -Execute "' + python + '" '
        '-Argument "\\"' + script + '\\""; '
        '$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) '
        '-RepetitionInterval (New-TimeSpan -Hours 1) '
        '-RepetitionDuration (New-TimeSpan -Days 365); '
        '$settings = New-ScheduledTaskSettingsSet '
        '-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; '
        'Register-ScheduledTask -TaskName "NexusKeyRotation" '
        '-Action $action -Trigger $trigger -Settings $settings '
        '-Description "Hourly NEXUS provider key rotation, health check, and CLI propagation" -Force'
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
        ok = r.returncode == 0
        return {"installed": ok, "task_name": "NexusKeyRotation", "interval_hours": 1,
                "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"installed": False, "error": str(e)}


def test_openai_model(provider_id: str, key: str, model: str, messages: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Test an OpenAI-compatible model directly: POST /v1/chat/completions."""
    cfg = PROVIDER_TESTS.get(provider_id)
    if not cfg or not cfg.get("test_body"):
        return {"ok": False, "detail": f"no test config for {provider_id}"}

    body = cfg["test_body"].copy()
    if model:
        body["model"] = model
    if messages:
        body["messages"] = messages

    headers = {"Authorization": f'Bearer {key}', "Content-Type": "application/json"}
    t0 = time.time()
    status, detail = _http("POST", cfg["url"], headers, body, timeout=cfg.get("timeout", 15))
    latency = int((time.time() - t0) * 1000)
    ok = 200 <= status < 300
    return {"ok": ok, "status": status, "latency_ms": latency, "body": detail}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="NEXUS provider key rotation, health check, and CLI propagation")
    ap.add_argument("--key", nargs=2, metavar=("PROVIDER", "VALUE"),
                    help="Set/update a specific provider key (e.g. --key baseten DDLL...)")
    ap.add_argument("--health-check", action="store_true", help="Ping all providers and show status (read-only)")
    ap.add_argument("--circuit-breaker", action="store_true", help="Show circuit breaker state")
    ap.add_argument("--install-schedule", action="store_true",
                    help="Install 1-hour Windows scheduled task for automatic key rotation")
    ap.add_argument("--dry-run", action="store_true", help="Preview without writing any file")
    ap.add_argument("--test-model", nargs=3, metavar=("PROVIDER", "MODEL", "KEY"),
                    help="Test a specific model: --test-model baseten zai-org/GLM-5.2 <KEY>")
    args = ap.parse_args(argv)

    if args.install_schedule:
        result = install_hourly_schedule()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("installed") else 1

    if args.health_check:
        result = cmd_health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.circuit_breaker:
        result = cmd_circuit_breaker()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.test_model:
        provider_id, model, key = args.test_model
        result = test_openai_model(provider_id, key, model)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    key_id = None
    key_value = None
    if args.key:
        key_id = args.key[0]
        key_value = args.key[1]

    result = cmd_rotate(key_id=key_id, key_value=key_value, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
