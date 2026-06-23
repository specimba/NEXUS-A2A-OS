"""nexusctl/model_sync.py - Unified CLI Model Provider Sync.

Synchronizes live model + provider state into every supported CLI's config:
  - opencode      (~/.config/opencode/opencode.json)
  - mimo          (~/.config/mimocode/mimocode.jsonc)
  - kilo          (~/.local/share/kilo/auth.json)
  - cline (VS Code)  (~/.AppData/Roaming/Code/User/settings.json)
  - hermes        (~/.AppData/Local/hermes/config.yaml)
  - nexusctl      (prints summary)

Sources of truth:
  - God Mode Proxy  /v1/models   (port 7357)  - live models + lanes
  - Node ModelRelay /v1/models   (port 7350)  - all discovered models
  - ~/.modelrelay.json                          - provider endpoints + keys

Run:
    python nexusctl/model_sync.py            # sync all CLIs
    python nexusctl/model_sync.py --refresh  # force refresh upstream cache first
    python nexusctl/model_sync.py --dry-run  # preview only
    python nexusctl/model_sync.py --list     # show CLI inventory + reachability
    python nexusctl/model_sync.py --install-schedule  # 1-hour Windows scheduled task
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HOME = Path(os.path.expanduser("~"))
GOD_PROXY_URL = "http://127.0.0.1:7357"
NODE_RELAY_URL = "http://127.0.0.1:7350"
MODELRELAY_CONFIG = HOME / ".modelrelay.json"

CLI_TARGETS = [
    {
        "id": "opencode",
        "name": "OpenCode",
        "version_cmd": ["opencode", "--version"],
        "config_path": HOME / ".config" / "opencode" / "opencode.json",
        "config_format": "json",
        "schema": "https://opencode.ai/config.json",
    },
    {
        "id": "mimo",
        "name": "MiMo CLI",
        "version_cmd": ["mimo", "--version"],
        "config_path": HOME / ".config" / "mimocode" / "mimocode.jsonc",
        "config_format": "jsonc",
        "schema": "https://opencode.ai/config.json",
    },
    {
        "id": "kilo",
        "name": "Kilo Code",
        "version_cmd": ["kilo", "--version"],
        "config_path": HOME / ".local" / "share" / "kilo" / "auth.json",
        "config_format": "kilo-auth",
    },
    {
        "id": "cline",
        "name": "Cline (VS Code ext)",
        "version_cmd": ["code", "--list-extensions"],
        "config_path": HOME / "AppData" / "Roaming" / "Code" / "User" / "settings.json",
        "config_format": "vscode",
    },
    {
        "id": "hermes",
        "name": "Hermes Agent",
        "version_cmd": ["hermes", "--version"],
        "config_path": HOME / "AppData" / "Local" / "hermes" / "config.yaml",
        "config_format": "yaml",
    },
    {
        "id": "nexusctl",
        "name": "Nexus CLI (own)",
        "version_cmd": ["python", "nexusctl.py", "--help"],
        "config_path": HOME / ".config" / "nexusctl" / "model-sync-state.json",
        "config_format": "json",
    },
]


def _http_get_json(url: str, timeout: float = 8.0) -> dict[str, Any] | None:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if r.status < 300:
                return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    return None


def _http_post_json(url: str, body: dict | None = None, timeout: float = 8.0) -> dict[str, Any] | None:
    try:
        import urllib.request
        req = urllib.request.Request(
            url, data=json.dumps(body or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status < 300:
                return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    return None


def fetch_live_state(refresh: bool = False) -> dict[str, Any]:
    """Pull fresh provider/model state from God Mode Proxy + Node Relay + .modelrelay.json."""
    if refresh:
        _http_post_json(f"{GOD_PROXY_URL}/god/refresh")
    lanes_resp = _http_get_json(f"{GOD_PROXY_URL}/god/lanes") or {}
    models_resp = _http_get_json(f"{GOD_PROXY_URL}/v1/models") or {}
    node_models = _http_get_json(f"{NODE_RELAY_URL}/api/models") or {}

    mrelay_cfg: dict[str, Any] = {}
    if MODELRELAY_CONFIG.exists():
        try:
            mrelay_cfg = json.loads(MODELRELAY_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass

    up_lanes = []
    for lane in lanes_resp.get("lanes", []):
        up_lanes.append({
            "id": lane.get("alias"),
            "name": lane.get("description", lane.get("alias")),
            "pinned_provider": lane.get("pinned_provider"),
            "target": lane.get("target"),
        })

    up_models = []
    for m in node_models.get("models", []) or models_resp.get("data", []):
        if not isinstance(m, dict):
            continue
        # Only include UP models
        status = m.get("status")
        if status not in (None, "up", "online"):
            continue
        up_models.append({
            "id": m.get("modelId") or m.get("id"),
            "label": m.get("label") or m.get("display_name"),
            "provider": m.get("providerKey") or m.get("owned_by"),
            "status": status or "up",
            "intell": m.get("intell"),
            "latency_ms": m.get("avg") or m.get("latency_ms"),
            "ctx": m.get("ctx"),
        })

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lanes": up_lanes,
        "models": up_models,
        "modelrelay_config": mrelay_cfg,
        "god_proxy_alive": bool(lanes_resp),
        "node_relay_alive": bool(node_models),
    }


def _build_relay_provider_entries(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Returns an opencode-style provider dict for the relay + LongCat + InternAI + Baseten."""
    entries: dict[str, dict[str, Any]] = {}

    # 1. The NEXUS God Mode Relay — single entry exposing all lanes
    lanes = state.get("lanes", [])
    lane_models = {}
    for lane in lanes:
        lane_models[lane["id"]] = {"name": lane["name"]}
    # Add a direct passthrough too
    entries["nexus-god-relay"] = {
        "name": "NEXUS God Relay (12 lanes + auto-routing)",
        "npm": "@ai-sdk/openai-compatible",
        "options": {
            "baseURL": f"{NODE_RELAY_URL}/v1",
            "apiKey": "nexus-relay",
        },
        "models": lane_models,
    }

    # 2. LongCat direct provider
    mrelay = state.get("modelrelay_config", {})
    lc = mrelay.get("providers", {}).get("longcat")
    if lc:
        api_keys = mrelay.get("apiKeys", {})
        key = lc.get("api_key", api_keys.get("longcat", ""))
        models = {m: {"name": f"LongCat {m}"} for m in (lc.get("models") or ["LongCat-2.0-Preview"])}
        entries["longcat"] = {
            "name": "LongCat (direct)",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "baseURL": lc.get("baseUrl", "https://api.longcat.chat/openai/v1"),
                "apiKey": key,
            },
            "models": models,
        }

    # 3. InternAI direct provider
    intern = mrelay.get("providers", {}).get("internai")
    if intern:
        api_keys = mrelay.get("apiKeys", {})
        key = intern.get("api_key", api_keys.get("internai", ""))
        models = {m: {"name": f"Intern {m}"} for m in (intern.get("models") or ["intern-latest"])}
        entries["internai"] = {
            "name": "InternAI (direct)",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "baseURL": intern.get("baseUrl", "https://api.internai.com/v1"),
                "apiKey": key,
            },
            "models": models,
        }

    # 4. Baseten direct provider (premium)
    bt = mrelay.get("providers", {}).get("openai-compatible:baseten")
    if bt:
        api_keys = mrelay.get("apiKeys", {})
        key = bt.get("api_key", api_keys.get("openai-compatible:baseten", api_keys.get("baseten", "")))
        # Only include the frontier-class Baseten models (avoid noise)
        wanted = ["zai-org/GLM-5.2", "moonshotai/Kimi-K2.7-Code", "zai-org/GLM-5.1"]
        avail = [m for m in wanted if m in (bt.get("models") or [])]
        if avail:
            models = {m: {"name": f"Baseten {m.split('/')[-1]}"} for m in avail}
            entries["baseten"] = {
                "name": "Baseten (frontier — GLM 5.x, Kimi K2.7)",
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": bt.get("baseUrl", "https://inference.baseten.co/v1"),
                    "apiKey": key,
                    "authScheme": "Api-Key",
                },
                "models": models,
            }

    return entries


def _merge_provider_into_json(cfg: dict, entries: dict[str, dict]) -> dict:
    """For opencode/mimo (opencode.json-style config): merge provider entries preserving existing user providers."""
    providers = cfg.setdefault("provider", {})
    for pid, entry in entries.items():
        # Don't overwrite user customizations if they explicitly added it
        existing = providers.get(pid)
        if existing and existing.get("__user_protected__"):
            continue
        providers[pid] = entry
    return cfg


def sync_opencode(state: dict, target: dict, dry_run: bool) -> dict:
    path = Path(target["config_path"])
    cfg: dict[str, Any] = {}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    entries = _build_relay_provider_entries(state)
    new_cfg = _merge_provider_into_json(cfg, entries)
    # Set default model to auto-fastest lane if user hasn't picked one
    if not cfg.get("model"):
        new_cfg["model"] = "nexus-god-relay/auto-fastest"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "opencode", "path": str(path), "providers_added": list(entries), "dry_run": dry_run, "ok": True}


def sync_mimo(state: dict, target: dict, dry_run: bool) -> dict:
    # mimo uses the same schema as opencode, stored as jsonc (still JSON-valid)
    path = Path(target["config_path"])
    cfg: dict[str, Any] = {}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    entries = _build_relay_provider_entries(state)
    new_cfg = _merge_provider_into_json(cfg, entries)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "mimo", "path": str(path), "providers_added": list(entries), "dry_run": dry_run, "ok": True}


def sync_kilo(state: dict, target: dict, dry_run: bool) -> dict:
    """kilo uses auth.json (credentials only). Add LongCat + Baseten credentials.
    The model list comes from kilo.db; if we add a custom API key, kilo will
    allow it as a custom OpenAI-compatible provider if the baseURL is also set."""
    path = Path(target["config_path"])
    cfg: dict[str, Any] = {}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    mrelay = state.get("modelrelay_config", {})
    api_keys = mrelay.get("apiKeys", {})
    providers = mrelay.get("providers", {})

    added = []
    # LongCat
    lc = providers.get("longcat")
    if lc:
        lc_key = lc.get("api_key", api_keys.get("longcat", ""))
        if lc_key:
            # Kilo expects provider ids to be lowercase without colons
            cfg["longcat"] = {"type": "api", "key": lc_key}
            added.append("longcat")
    # Baseten
    bt = providers.get("openai-compatible:baseten")
    if bt:
        bt_key = bt.get("api_key", api_keys.get("openai-compatible:baseten", api_keys.get("baseten", "")))
        if bt_key:
            cfg["baseten"] = {"type": "api", "key": bt_key}
            added.append("baseten")
    # InternAI
    intern = providers.get("internai")
    if intern:
        i_key = intern.get("api_key", api_keys.get("internai", ""))
        if i_key:
            cfg["internai"] = {"type": "api", "key": i_key}
            added.append("internai")
    # Keep modelrelaygod authenticated for the god-relay lane
    if "modelrelaygod" not in cfg:
        cfg["modelrelaygod"] = {"type": "api", "key": "nexus-relay"}
        added.append("modelrelaygod")

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "kilo", "path": str(path), "providers_added": added, "dry_run": dry_run, "ok": True}


def sync_cline(state: dict, target: dict, dry_run: bool) -> dict:
    """cline is a VS Code extension. Its models config goes in VS Code settings.json
    under 'cline.allowedModels' and 'cline.apiProviders'."""
    path = Path(target["config_path"])
    if not path.exists():
        return {"target": "cline", "path": str(path), "ok": False, "reason": "VS Code settings.json not found"}
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}

    entries = _build_relay_provider_entries(state)
    # Cline stores provider configs as nested objects
    # We add our relay/longcat/internai/baseten under the "cline.apiProviders" namespace
    api_providers = cfg.setdefault("cline.apiProviders", {})
    added = []
    for pid, entry in entries.items():
        api_providers[pid] = {
            "name": entry["name"],
            "baseURL": entry["options"]["baseURL"],
            "apiKey": entry["options"].get("apiKey", ""),
            "authScheme": entry["options"].get("authScheme", "Bearer"),
            "models": list(entry.get("models", {}).keys()),
        }
        added.append(pid)

    if not dry_run:
        path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
    return {"target": "cline", "path": str(path), "providers_added": added, "dry_run": dry_run, "ok": True}


def sync_hermes(state: dict, target: dict, dry_run: bool) -> dict:
    """hermes uses YAML config. Add providers dict entries."""
    path = Path(target["config_path"])
    if not path.exists():
        return {"target": "hermes", "path": str(path), "ok": False, "reason": "hermes config.yaml not found"}

    entries = _build_relay_provider_entries(state)
    # Build a YAML-safe providers dict; we replace the providers block entirely
    # to avoid manual YAML surgery.
    yaml_lines = []
    yaml_lines.append("# === nexusctl model-sync providers (managed) ===")
    for pid, entry in entries.items():
        yaml_lines.append(f"{pid.replace('-', '_')}:")
        yaml_lines.append(f"  name: {entry['name']!r}")
        yaml_lines.append(f"  base_url: {entry['options']['baseURL']!r}")
        yaml_lines.append(f"  api_key: {entry['options'].get('apiKey', '')!r}")
        if entry["options"].get("authScheme") and entry["options"]["authScheme"] != "Bearer":
            yaml_lines.append(f"  auth_scheme: {entry['options']['authScheme']!r}")
        yaml_lines.append("  models:")
        for m_id, m_meta in entry.get("models", {}).items():
            yaml_lines.append(f"    {m_id!r}: {m_meta.get('name', m_id)!r}")
    yaml_blob = "\n".join(yaml_lines) + "\n# === end nexusctl managed ===\n"

    if not dry_run:
        # Read the existing config, replace the providers: {} block (or add it)
        original = path.read_text(encoding="utf-8")
        # Hermetic insertion: if a managed block exists, replace it; otherwise append after 'providers:' line
        if "# === nexusctl model-sync" in original:
            # Replace between markers
            pre, _, _ = original.partition("# === nexusctl model-sync providers")
            _, _, post = original.partition("# === end nexusctl managed ===\n")
            new_text = pre + yaml_blob + post
        else:
            # Find 'providers:' line and replace the empty {} with our block
            import re
            new_text = re.sub(
                r"^providers:\s*\{\s*\}$",
                yaml_blob.rstrip("\n"),
                original,
                count=1,
                flags=re.MULTILINE,
            )
            if new_text == original:
                # No providers: {} line, append
                new_text = original.rstrip() + "\n\n" + yaml_blob
        path.write_text(new_text, encoding="utf-8")

    return {"target": "hermes", "path": str(path), "providers_added": list(entries), "dry_run": dry_run, "ok": True}


def sync_nexusctl(state: dict, target: dict, dry_run: bool) -> dict:
    """Write a state JSON for our own CLI to know about the last sync."""
    path = Path(target["config_path"])
    summary = {
        "last_sync": state.get("timestamp"),
        "god_proxy_alive": state.get("god_proxy_alive"),
        "node_relay_alive": state.get("node_relay_alive"),
        "lanes_count": len(state.get("lanes", [])),
        "models_count": len(state.get("models", [])),
    }
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"target": "nexusctl", "path": str(path), "ok": True, "summary": summary, "dry_run": dry_run}


SYNC_HANDLERS = {
    "opencode": sync_opencode,
    "mimo": sync_mimo,
    "kilo": sync_kilo,
    "cline": sync_cline,
    "hermes": sync_hermes,
    "nexusctl": sync_nexusctl,
}


def list_cli_inventory(state: dict) -> dict:
    """Show which CLIs are installed, what they reach, and which are missing config."""
    inventory = []
    for target in CLI_TARGETS:
        cfg_path = Path(target["config_path"])
        cfg_exists = cfg_path.exists()
        alive = False
        try:
            r = subprocess.run(
                target["version_cmd"], capture_output=True, text=True, timeout=3,
            )
            alive = r.returncode == 0
        except Exception:
            alive = False
        inventory.append({
            "id": target["id"],
            "name": target["name"],
            "binary_installed": alive,
            "config_path": str(cfg_path),
            "config_exists": cfg_exists,
            "config_format": target["config_format"],
        })
    return {"clis": inventory, "state": {"lanes": len(state.get("lanes", [])), "models": len(state.get("models", []))}}


def install_hourly_schedule() -> dict:
    """Install a Windows Scheduled Task that runs model-sync every hour."""
    script = str(Path(__file__).resolve())
    python = sys.executable
    # RepetitionDuration of 366 days is the upper safe bound for Task Scheduler
    ps = (
        '$action = New-ScheduledTaskAction -Execute "' + python + '" '
        '-Argument "\\"' + script + '\\" --refresh"; '
        '$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) '
        '-RepetitionInterval (New-TimeSpan -Hours 1) '
        '-RepetitionDuration (New-TimeSpan -Days 365); '
        '$settings = New-ScheduledTaskSettingsSet '
        '-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; '
        'Register-ScheduledTask -TaskName "NexusModelSync" '
        '-Action $action -Trigger $trigger -Settings $settings '
        '-Description "Hourly NEXUS model provider refresh for all CLIs" -Force'
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
        ok = r.returncode == 0
        return {"installed": ok, "task_name": "NexusModelSync", "interval_hours": 1,
                "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"installed": False, "error": str(e)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="NEXUS CLI model provider sync")
    ap.add_argument("--refresh", action="store_true", help="Force refresh upstream cache first")
    ap.add_argument("--dry-run", action="store_true", help="Don't write any files, just report what would change")
    ap.add_argument("--list", action="store_true", help="List CLI inventory and reachability")
    ap.add_argument("--only", choices=[t["id"] for t in CLI_TARGETS], help="Sync only this CLI")
    ap.add_argument("--install-schedule", action="store_true", help="Install the 1-hour Windows scheduled task")
    ap.add_argument("--log", help="Log file path")
    args = ap.parse_args(argv)

    if args.install_schedule:
        result = install_hourly_schedule()
        print(json.dumps(result, indent=2))
        return 0 if result.get("installed") else 1

    state = fetch_live_state(refresh=args.refresh)
    if not state["god_proxy_alive"] and not state["node_relay_alive"]:
        print(json.dumps({
            "error": "Neither God Mode Proxy (7357) nor Node ModelRelay (7350) reachable",
            "hint": "Start them with:  scripts\\start_node_relay.ps1  and  python -m nexus_os.relay.god_mode_proxy",
        }, indent=2))
        return 2

    if args.list:
        print(json.dumps(list_cli_inventory(state), indent=2))
        return 0

    targets = [t for t in CLI_TARGETS if (args.only is None or t["id"] == args.only)]
    results = []
    for tgt in targets:
        handler = SYNC_HANDLERS.get(tgt["id"])
        if not handler:
            results.append({"target": tgt["id"], "ok": False, "reason": "no handler"})
            continue
        try:
            r = handler(state, tgt, dry_run=args.dry_run)
            results.append(r)
        except Exception as e:
            results.append({"target": tgt["id"], "ok": False, "error": str(e)})

    summary = {
        "timestamp": state["timestamp"],
        "god_proxy_alive": state["god_proxy_alive"],
        "node_relay_alive": state["node_relay_alive"],
        "lanes_synced": len(state["lanes"]),
        "models_seen": len(state["models"]),
        "dry_run": args.dry_run,
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.log:
        try:
            Path(args.log).parent.mkdir(parents=True, exist_ok=True)
            with open(args.log, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
