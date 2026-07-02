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
    """Returns an opencode-style provider dict with lane aliases + direct model passthrough."""
    entries: dict[str, dict[str, Any]] = {}

    # 1. The NEXUS God Mode Relay — expose lanes + direct model names
    lanes = state.get("lanes", [])
    lane_models = {}
    for lane in lanes:
        lane_models[lane["id"]] = {"name": lane["name"]}

    # Add ALL discovered models as passthrough entries so users can
    # type "kimi-k2.6", "minimax-m3", "deepseek-v4-pro" etc. directly.
    for m in state.get("models", []):
        mid = m.get("id")
        if mid:
            label = m.get("label") or mid.split("/")[-1]
            provider = m.get("provider", "")
            mid_with_provider = f"{provider}/{mid}" if provider and not mid.startswith(f"{provider}/") else mid
            # Skip lane names (they're already above)
            if mid in lane_models or mid_with_provider in lane_models:
                continue
            lane_models[mid] = {"name": f"{label} ({provider})"}

    entries["nexus-god-relay"] = {
        "name": f"NEXUS God Relay ({len(lanes)} lanes + {len(state.get('models', []))} models)",
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

    # 4. NVIDIA NIM direct provider (Minimax M3, Kimi K2, Devstral 2, etc.)
    nv = mrelay.get("providers", {}).get("nvidia")
    if nv:
        api_keys = mrelay.get("apiKeys", {})
        key = nv.get("api_key", api_keys.get("nvidia", ""))
        nv_models = nv.get("models") or ["nvidia/minimax-m3", "nvidia/devstral-2-123b", "nvidia/kimi-k2-thinking"]
        NIM_THINKING = {"minimaxai/minimax-m3", "nvidia/minimax-m3", "moonshotai/kimi-k2-thinking", "nvidia/kimi-k2-thinking"}
        models = {}
        for m in nv_models:
            opts = {}
            if m in NIM_THINKING:
                opts = {"options": {"enable_thinking": True, "thinking_budget": 8192}}
            mkey = m.split("/")[-1]
            models[m] = {"name": f"NVIDIA {mkey}", **opts}
        entries["nvidia-nim"] = {
            "name": "NVIDIA NIM (Minimax M3, Devstral 2, Kimi K2, GLM-5 variants)",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "baseURL": nv.get("baseUrl", "https://integrate.api.nvidia.com/v1"),
                "apiKey": key,
            },
            "models": models,
        }

    # 5. SiliconFlow direct (GLM-5, DeepSeek V4, Kimi K2, MiniMax, Qwen3)
    sf = mrelay.get("providers", {}).get("openai-compatible:siliconflow")
    if sf and sf.get("_status") != "DEAD":
        api_keys = mrelay.get("apiKeys", {})
        key = sf.get("api_key", api_keys.get("openai-compatible:siliconflow", ""))
        sf_models_list = sf.get("models", [])
        THINKING_MODELS = {
            "zai-org/GLM-5.1", "zai-org/GLM-5", "moonshotai/Kimi-K2-Thinking",
            "deepseek-ai/DeepSeek-V3.1", "deepseek-ai/DeepSeek-V3.2",
            "deepseek-ai/DeepSeek-V3.2-Exp", "tencent/Hunyuan-A13B-Instruct",
        }
        sf_models = {}
        for m in sf_models_list:
            opts = {}
            if m in THINKING_MODELS:
                opts = {"options": {"enable_thinking": True, "thinking_budget": 8192}}
            sf_models[m] = {"name": f"SF {m.split('/')[-1]}", **opts}
        if sf_models:
            entries["siliconflow"] = {
                "name": f"SiliconFlow ({len(sf_models)} models — free tier)",
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": sf.get("baseUrl", "https://api.siliconflow.com/v1"),
                    "apiKey": key,
                },
                "models": sf_models,
            }

    # 6. Generic fallback providers from .modelrelay.json
    for pname, pcfg in mrelay.get("providers", {}).items():
        if pname in ("longcat", "internai", "nvidia", "openai-compatible:baseten", "openai-compatible:siliconflow", "ollama"):
            continue  # already handled above or not useful as direct
        if not isinstance(pcfg, dict):
            continue
        base_url = pcfg.get("baseUrl")
        pmodels = pcfg.get("models")
        if not base_url or not pmodels:
            continue
        api_keys = mrelay.get("apiKeys", {})
        key = pcfg.get("api_key", api_keys.get(pname, ""))
        display_name = pcfg.get("name", pname)
        models = {m: {"name": f"{display_name.split('/')[-1]} {m.split('/')[-1]}"} for m in pmodels}
        safe_id = pname.replace(":", "-").replace("/", "-").replace(".", "-")
        entries[f"direct-{safe_id}"] = {
            "name": f"{display_name} (direct)",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "baseURL": base_url,
                "apiKey": key,
            },
            "models": models,
        }

    # 7. Baseten direct (policy changes — GLM-5.2 may be gone, flagging status)
    bt = mrelay.get("providers", {}).get("openai-compatible:baseten")
    if bt:
        api_keys = mrelay.get("apiKeys", {})
        key = bt.get("api_key", api_keys.get("openai-compatible:baseten", api_keys.get("baseten", "")))
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
                },
                "models": models,
            }
        else:
            # GLM-5.x no longer available — flag for replacement
            entries["baseten"] = {
                "name": "Baseten (deprecated — policy change, models unavail)",
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": bt.get("baseUrl", "https://inference.baseten.co/v1"),
                    "apiKey": key,
                },
                "models": {},
            }

    # 8. GLM-5.2 fallback alternatives: NVIDIA NIM may have GLM-5 variants,
    # SiliconFlow has GLM-5-9B, LongCat has GLM-5-Flash.
    # These are already picked up via the generic fallback loop above
    # if configured in .modelrelay.json.

    return entries


def _read_json_config_guarded(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load a config file we intend to rewrite, refusing anything we can't round-trip.

    Returns (cfg, None) when the file is missing (fresh start) or strict JSON.
    Returns (None, reason) when the file exists but a json.dumps rewrite would
    destroy it — unparseable, JSONC with comments, or a non-object top level.
    Callers MUST skip the write in that case: a sync tool never trades the
    user's config for its own output.
    """
    if not path.exists():
        return {}, None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"unreadable ({e}) — refusing to overwrite"
    try:
        cfg = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"not strict JSON (comments or trailing commas?) — refusing to overwrite: {e}"
    if not isinstance(cfg, dict):
        return None, "top-level value is not an object — refusing to overwrite"
    return cfg, None


def _backup_before_write(path: Path) -> None:
    """Keep a rolling <name>.nexus-sync.bak of the pre-write bytes."""
    if path.exists():
        path.with_name(path.name + ".nexus-sync.bak").write_bytes(path.read_bytes())


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
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "opencode", "path": str(path), "ok": False, "reason": refuse}
    entries = _build_relay_provider_entries(state)
    new_cfg = _merge_provider_into_json(cfg, entries)
    # Set default model to auto-fastest lane if user hasn't picked one
    if not cfg.get("model"):
        new_cfg["model"] = "nexus-god-relay/auto-fastest"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup_before_write(path)
        path.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "opencode", "path": str(path), "providers_added": list(entries), "dry_run": dry_run, "ok": True}


def sync_mimo(state: dict, target: dict, dry_run: bool) -> dict:
    # mimo uses the same schema as opencode, stored as jsonc (still JSON-valid)
    path = Path(target["config_path"])
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "mimo", "path": str(path), "ok": False, "reason": refuse}
    entries = _build_relay_provider_entries(state)
    new_cfg = _merge_provider_into_json(cfg, entries)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup_before_write(path)
        path.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "mimo", "path": str(path), "providers_added": list(entries), "dry_run": dry_run, "ok": True}


def sync_kilo(state: dict, target: dict, dry_run: bool) -> dict:
    """kilo uses auth.json (credentials only). Add LongCat + Baseten credentials.
    The model list comes from kilo.db; if we add a custom API key, kilo will
    allow it as a custom OpenAI-compatible provider if the baseURL is also set."""
    path = Path(target["config_path"])
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "kilo", "path": str(path), "ok": False, "reason": refuse}

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
        _backup_before_write(path)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "kilo", "path": str(path), "providers_added": added, "dry_run": dry_run, "ok": True}


def sync_cline(state: dict, target: dict, dry_run: bool) -> dict:
    """cline is a VS Code extension. Its models config goes in VS Code settings.json
    under 'cline.allowedModels' and 'cline.apiProviders'."""
    path = Path(target["config_path"])
    if not path.exists():
        return {"target": "cline", "path": str(path), "ok": False, "reason": "VS Code settings.json not found"}
    # VS Code settings.json is JSONC — comments are normal. A json.dumps
    # rewrite of a failed parse would replace the user's entire settings
    # with just our block, so the guard hard-fails instead.
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "cline", "path": str(path), "ok": False, "reason": refuse}

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
        _backup_before_write(path)
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
        _backup_before_write(path)
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


def _auto_revive_relays() -> bool:
    """Best-effort one-shot revive of the NEXUS relay ports.

    Called when model-sync finds both relays dead (typical right after a PC
    restart). Tries the canonical Windows revive script, falls back to the
    individual Node + Python relay launchers. Returns True if at least one
    core relay came up. Never raises — sync must stay resilient.
    """
    root = Path(__file__).resolve().parent.parent
    revive_all = root / "scripts" / "revive_relay_ports.ps1"
    start_node = root / "scripts" / "start_node_relay.ps1"
    py_relay_bat = root / "scripts" / "start_python_relay_7355.bat"
    python = root / ".venv" / "Scripts" / "python.exe"
    ran_something = False

    def _try(cmd: list[str], timeout: int = 20) -> bool:
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return True
        except Exception:
            return False

    if sys.platform == "win32":
        if revive_all.exists():
            ran = _try([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(revive_all),
            ], timeout=45)
            ran_something = ran
        if start_node.exists() and not _port_alive(7350, "/"):
            _try(["powershell", "-NoProfile", "-File", str(start_node)], timeout=15)
            ran_something = True
        if py_relay_bat.exists() and not _port_alive(7355, "/health"):
            subprocess.Popen(["cmd.exe", "/c", "start", "/min", "cmd", "/c", str(py_relay_bat)],
                             cwd=str(root))
            ran_something = True
        if python.exists() and not _port_alive(7357, "/health"):
            subprocess.Popen([str(python), "-m", "nexus_os.relay.god_mode_proxy"], cwd=str(root))
            ran_something = True
        if ran_something:
            time.sleep(4)
    return _port_alive(7350, "/") or _port_alive(7357, "/health")


def _port_alive(port: int, path: str = "/health", timeout: int = 2) -> bool:
    import urllib.request
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(f"http://127.0.0.1:{port}{path}"), timeout=timeout)
        return r.status < 400
    except Exception:
        return False


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
        # Relays die after a PC restart; auto-revive once before giving up so that
        # `nexusctl model-sync` (and therefore Hermes + every CLI wiring) can proceed
        # even from a cold boot. This is the root fix for "Hermes cannot wire relay".
        revived = _auto_revive_relays()
        if revived:
            time.sleep(3)
            state = fetch_live_state(refresh=True)
    if not state["god_proxy_alive"] and not state["node_relay_alive"]:
        print(json.dumps({
            "error": "Neither God Mode Proxy (7357) nor Node ModelRelay (7350) reachable",
            "auto_revive_attempted": True,
            "hint": "Start them with:  scripts\\revive_relay_ports.ps1  (or install: scripts\\install_nexus_autostart.ps1)",
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
