"""nexusctl/model_sync.py - Unified CLI Model Provider Sync.

Synchronizes live model + provider state into every supported CLI's config:
  - opencode      (~/.config/opencode/opencode.json)
  - mimo          (~/.config/mimocode/mimocode.jsonc)
  - kilo          (~/.local/share/kilo/auth.json)
  - pi            (~/.pi/agent/models.json)
  - cline           (repo-local .cline/mcp.json only; inference remains user-owned)
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
import copy
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

HOME = Path(os.path.expanduser("~"))
REPO_ROOT = Path(__file__).resolve().parent.parent
GOD_PROXY_URL = "http://127.0.0.1:7357"
NODE_RELAY_URL = "http://127.0.0.1:7350"
MODELRELAY_CONFIG = HOME / ".modelrelay.json"
MODEL_ARENA_URL = "http://127.0.0.1:7356"
CLINE_PROJECT_MCP_CONFIG = REPO_ROOT / ".cline" / "mcp.json"
CLINE_INFERENCE_REQUIREMENTS = (
    "openai_compatible_base_url",
    "bearer",
    "model_id",
)
HERMES_RELAY_KEY_ENV = "NEXUS_MODELRELAY_API_KEY"
# Hermes' GLM lock is an exact NVIDIA offer, not the ambiguous canonical alias.
# A bare ``glm-5.2`` intentionally fans out across every logical provider
# offer in ModelRelay, which made an NVIDIA denial look like a silent model
# substitution to the caller.
HERMES_PRIMARY_MODEL = "nvidia/z-ai/glm-5.2"
HERMES_LEGACY_PRIMARY_MODEL_IDS = frozenset(
    {
        "glm-5.2",
        "z-ai/glm-5.2",
        HERMES_PRIMARY_MODEL,
    }
)
# ``nexus-resilient`` is the relay's explicit, fresh-health-only fallback
# alias.  It is deliberately separate from the GLM-5.2 primary lock and
# fails closed when no independently healthy fallback exists.
HERMES_FALLBACK_MODEL = "nexus-resilient"
HERMES_LEGACY_MANAGED_FALLBACK_MODEL = "labs-leanstral-1-5-1"
HERMES_AUXILIARY_TITLE_MODEL = HERMES_FALLBACK_MODEL
HERMES_REQUIRED_MODELS = (HERMES_PRIMARY_MODEL, HERMES_FALLBACK_MODEL)
HERMES_API_MAX_RETRIES = 1
HERMES_MANAGED_START = "# === nexusctl model-sync providers (managed) ==="
HERMES_MANAGED_END = "# === end nexusctl managed ==="
PI_RELAY_PROVIDER_ID = "nexus-modelrelay"
PI_LEGACY_RELAY_DEFAULT = "http://127.0.0.1:7352/v1"
PI_RELAY_DEFAULT = f"{NODE_RELAY_URL}/v1"

# Inventory-only WSL probes.  These entries intentionally have no config path:
# a binary on PATH is not evidence of an active or safe-to-sync configuration.
WSL_READ_ONLY_CLI_SPECS: tuple[dict[str, str], ...] = (
    {"id": "opencode", "name": "OpenCode", "binary": "opencode", "config_format": "json"},
    {"id": "mimo", "name": "MiMo CLI", "binary": "mimo", "config_format": "jsonc"},
    {"id": "kilo", "name": "Kilo Code", "binary": "kilo", "config_format": "kilo-auth"},
    {"id": "pi", "name": "Pi Coding Agent", "binary": "pi", "config_format": "pi-models-json"},
)
_WSL_CLI_DISCOVERY_SCRIPT = """\
for nexus_cli in opencode mimo kilo pi; do
    nexus_path="$(command -v "$nexus_cli" 2>/dev/null || true)"
    if [ -n "$nexus_path" ]; then
        printf '%s\\tinstalled\\t%s\\n' "$nexus_cli" "$nexus_path"
    else
        printf '%s\\tnot_installed\\t\\n' "$nexus_cli"
    fi
done
"""

# Explicit current partner contracts.  They deliberately mirror the staged
# endpoint records created by ``scripts/reconcile_partner_modelrelay.py``.
# A legacy top-level ``longcat``/``internai`` record is historical adapter
# data, not evidence that the Node relay endpoint is active or that a model is
# still valid for client projection.
PARTNER_SYNC_CONTRACTS: dict[str, dict[str, str]] = {
    "longcat": {
        "endpoint_key": "openai-compatible:longcat",
        "base_url": "https://api.longcat.chat/openai/v1",
        "model_id": "LongCat-2.0",
        "name": "LongCat (direct)",
        "model_label_prefix": "LongCat",
    },
    "internai": {
        "endpoint_key": "openai-compatible:internai",
        "base_url": "https://chat.intern-ai.org.cn/api/v1",
        "model_id": "intern-latest",
        "name": "InternAI (direct)",
        "model_label_prefix": "Intern",
    },
}


def load_modelrelay_bearer(
    token_env: str = HERMES_RELAY_KEY_ENV,
    *,
    environ: Mapping[str, str] | None = None,
    token_path: Path | None = None,
) -> str:
    """Load the relay bearer from environment or the launcher's private file.

    The value is returned only to in-process probes and is never included in
    sync results, command arguments, or generated Hermes configuration.
    """
    env = os.environ if environ is None else environ
    direct = str(env.get(token_env, "") or "").strip()
    if direct:
        return direct
    configured = str(env.get("NEXUS_MODELRELAY_TOKEN_PATH", "") or "").strip()
    path = token_path or (
        Path(configured) if configured else HOME / ".nexus" / "secrets" / "modelrelay_bearer.token"
    )
    try:
        if not path.is_file() or path.stat().st_size > 4096:
            return ""
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def classify_cli_binary(path: str | os.PathLike[str] | None) -> str:
    """Classify a CLI binary without trying to execute it cross-platform."""
    value = str(path or "").strip()
    if not value:
        return "missing"
    suffix = Path(value).suffix.lower()
    if suffix == ".exe":
        return "windows-exe"
    if suffix == ".cmd":
        return "windows-cmd"
    if suffix == ".bat":
        return "windows-bat"
    if suffix == ".ps1":
        return "powershell-script"
    if value.startswith("/"):
        return "linux-native"
    return "native"


def _valid_ip(candidate: str) -> str | None:
    try:
        return str(ipaddress.ip_address(candidate.strip()))
    except ValueError:
        return None


def resolve_wsl_windows_gateway(
    distro: str = "Ubuntu",
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> str | None:
    """Resolve the current Windows host address from inside a WSL distro.

    WSL2 gateway addresses are not stable across restarts. Prefer the default
    route and retain /etc/resolv.conf only as a compatibility fallback.
    """
    commands = (
        ["wsl.exe", "-d", distro, "--", "ip", "route", "show", "default"],
        ["wsl.exe", "-d", distro, "--", "cat", "/etc/resolv.conf"],
    )
    for index, command in enumerate(commands):
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if getattr(result, "returncode", 1) != 0:
            continue
        output = str(getattr(result, "stdout", "") or "")
        pattern = r"\bvia\s+(\S+)" if index == 0 else r"^nameserver\s+(\S+)"
        match = re.search(pattern, output, flags=re.MULTILINE)
        if match:
            parsed = _valid_ip(match.group(1))
            if parsed:
                return parsed
    return None


def _wsl_unc_path(distro: str, posix_path: str) -> Path:
    components = [part for part in posix_path.strip().split("/") if part]
    return Path("\\\\wsl.localhost\\" + distro + "\\" + "\\".join(components))


def _wsl_inventory_row(
    spec: Mapping[str, str],
    *,
    distro: str,
    binary_installed: bool | None,
    binary_path: str | None,
    binary_status: str,
    discovery_status: str,
    discovery_reason: str | None,
) -> dict[str, Any]:
    """Build an observation-only WSL inventory row without config claims."""
    return {
        "id": f"{spec['id']}-wsl",
        "source_id": spec["id"],
        "name": f"{spec['name']} (WSL)",
        "instance": "wsl",
        "distro": distro,
        "binary_name": spec["binary"],
        "binary_path": binary_path,
        "binary_kind": (
            classify_cli_binary(binary_path)
            if binary_path
            else ("missing" if binary_installed is False else "unknown")
        ),
        "binary_installed": binary_installed,
        "binary_status": binary_status,
        "discovery_status": discovery_status,
        "discovery_reason": discovery_reason,
        "discovery_method": "wsl_read_only_command_v",
        "config_discovery_status": "not_attempted",
        "configuration_state": "not_inspected",
        "config_path": None,
        "config_format": spec["config_format"],
        "sync_supported": False,
    }


def _wsl_discovery_failure(
    specs: tuple[dict[str, str], ...],
    *,
    distro: str,
    status: str,
    reason: str,
) -> list[dict[str, Any]]:
    return [
        _wsl_inventory_row(
            spec,
            distro=distro,
            binary_installed=None,
            binary_path=None,
            binary_status="unknown",
            discovery_status=status,
            discovery_reason=reason,
        )
        for spec in specs
    ]


def discover_wsl_cli_inventory(
    *,
    distro: str = "Ubuntu",
    runner: Callable[..., Any] = subprocess.run,
    specs: tuple[dict[str, str], ...] = WSL_READ_ONLY_CLI_SPECS,
) -> list[dict[str, Any]]:
    """Safely observe WSL CLI binaries without opening profiles or configs.

    This deliberately uses ``sh -c`` through ``wsl.exe --exec`` so shell
    profiles are not loaded.  It calls only the POSIX ``command -v`` builtin;
    no private configuration path is probed, read, or inferred for syncing.
    """
    command = [
        "wsl.exe",
        "-d",
        distro,
        "--exec",
        "sh",
        "-c",
        _WSL_CLI_DISCOVERY_SCRIPT,
    ]
    try:
        result = runner(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return _wsl_discovery_failure(
            specs,
            distro=distro,
            status="unavailable",
            reason="wsl_command_unavailable",
        )

    if getattr(result, "returncode", 1) != 0:
        output = "\n".join(
            (
                str(getattr(result, "stdout", "") or ""),
                str(getattr(result, "stderr", "") or ""),
            )
        ).lower()
        if "e_accessdenied" in output or "accessdenied" in output:
            return _wsl_discovery_failure(
                specs,
                distro=distro,
                status="blocked",
                reason="wsl_service_access_denied",
            )
        return _wsl_discovery_failure(
            specs,
            distro=distro,
            status="unavailable",
            reason="wsl_command_failed",
        )

    records: dict[str, tuple[str, str]] = {}
    for raw_line in str(getattr(result, "stdout", "") or "").splitlines():
        fields = raw_line.split("\t", 2)
        if len(fields) != 3:
            continue
        binary, status, path = fields
        if status in {"installed", "not_installed"} and binary not in records:
            records[binary] = (status, path)

    rows: list[dict[str, Any]] = []
    for spec in specs:
        status_and_path = records.get(spec["binary"])
        if status_and_path is None:
            rows.append(
                _wsl_inventory_row(
                    spec,
                    distro=distro,
                    binary_installed=None,
                    binary_path=None,
                    binary_status="unknown",
                    discovery_status="invalid_response",
                    discovery_reason="wsl_discovery_incomplete",
                )
            )
            continue
        status, path = status_and_path
        installed = status == "installed" and bool(path)
        rows.append(
            _wsl_inventory_row(
                spec,
                distro=distro,
                binary_installed=installed,
                binary_path=path if installed else None,
                binary_status="installed" if installed else "not_installed",
                discovery_status="available",
                discovery_reason=None,
            )
        )
    return rows


def _windows_version_command(binary: str) -> list[str]:
    kind = classify_cli_binary(binary)
    if kind in {"windows-cmd", "windows-bat"}:
        return ["cmd.exe", "/d", "/c", binary, "--version"]
    if kind == "powershell-script":
        return ["powershell", "-NoProfile", "-File", binary, "--version"]
    return [binary, "--version"] if binary else ["hermes", "--version"]


def discover_hermes_targets(
    *,
    home: Path = HOME,
    distro: str = "Ubuntu",
    runner: Callable[..., Any] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> list[dict[str, Any]]:
    """Return separate Windows and WSL Hermes instances."""
    windows_candidates = (
        home / ".hermes" / "config.yaml",
        home / "AppData" / "Local" / "hermes" / "config.yaml",
    )
    windows_config = next((p for p in windows_candidates if p.exists()), windows_candidates[0])
    windows_binary = which("hermes") or ""
    targets: list[dict[str, Any]] = [
        {
            "id": "hermes",
            "name": "Hermes Agent (Windows)",
            "instance": "windows",
            "config_path": windows_config,
            "env_path": windows_config.parent / ".env",
            "config_format": "yaml",
            "binary_path": windows_binary,
            "binary_kind": classify_cli_binary(windows_binary),
            "version_cmd": _windows_version_command(windows_binary),
            "relay_base_url": f"{NODE_RELAY_URL}/v1",
            "key_env": HERMES_RELAY_KEY_ENV,
        }
    ]

    try:
        home_result = runner(
            ["wsl.exe", "-d", distro, "--", "printenv", "HOME"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        home_result = None
    wsl_home = ""
    discovery_source = "live"
    if home_result is not None and getattr(home_result, "returncode", 1) == 0:
        wsl_home = str(getattr(home_result, "stdout", "") or "").strip()
    if not wsl_home.startswith("/"):
        fallback_user = home.name.split(".", 1)[0]
        wsl_home = os.environ.get("NEXUS_WSL_HOME", f"/home/{fallback_user}").strip()
        discovery_source = "configured_fallback"
    if not wsl_home.startswith("/"):
        return targets

    try:
        binary_result = runner(
            ["wsl.exe", "-d", distro, "--", "which", "hermes"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        binary_result = None
    wsl_binary = ""
    if binary_result is not None and getattr(binary_result, "returncode", 1) == 0:
        wsl_binary = str(getattr(binary_result, "stdout", "") or "").strip()
    if not wsl_binary:
        wsl_binary = f"{wsl_home}/.local/bin/hermes"

    posix_config = f"{wsl_home}/.hermes/config.yaml"
    targets.append(
        {
            "id": "hermes-wsl",
            "name": f"Hermes Agent ({distro}/WSL)",
            "instance": "wsl",
            "distro": distro,
            "config_path": _wsl_unc_path(distro, posix_config),
            "config_path_posix": posix_config,
            "env_path_posix": f"{wsl_home}/.hermes/.env",
            "discovery_source": discovery_source,
            "config_format": "yaml",
            "binary_path": wsl_binary,
            "binary_kind": classify_cli_binary(wsl_binary),
            "version_cmd": ["wsl.exe", "-d", distro, "--", wsl_binary, "--version"],
            "key_env": HERMES_RELAY_KEY_ENV,
        }
    )
    return targets

_WSL_HTTP_PROBE = r"""
import json
import sys
import urllib.error
import urllib.request

request = json.loads(sys.stdin.read())
headers = {"Accept": "application/json"}
token = request.get("token")
if token:
    headers["Authorization"] = "Bearer " + token
req = urllib.request.Request(request["url"], headers=headers)
try:
    with urllib.request.urlopen(req, timeout=float(request.get("timeout", 8.0))) as response:
        raw = response.read().decode("utf-8")
        payload = json.loads(raw) if raw else None
        print(json.dumps({"status": int(response.status), "payload": payload}))
except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = None
    print(json.dumps({"status": int(exc.code), "payload": payload}))
except Exception:
    print(json.dumps({"status": 0, "payload": None}))
"""

_WSL_CONFIG_IO = r"""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

request = json.loads(sys.stdin.read())
path = Path(str(request.get("path") or ""))
operation = request.get("operation")
try:
    if not path.is_absolute() or "\0" in str(path):
        raise ValueError("absolute path required")
    if path.is_symlink():
        raise ValueError("symlinked config rejected")
    if operation == "read":
        content = path.read_text(encoding="utf-8")
        print(json.dumps({"ok": True, "content": content}))
    elif operation == "write":
        content = str(request.get("content") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + ".nexus-sync.bak"))
        temp = path.with_name(f".{path.name}.nexus-sync-{os.getpid()}.tmp")
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            os.chmod(path, mode)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        print(json.dumps({"ok": True}))
    else:
        raise ValueError("unsupported operation")
except Exception as exc:
    print(json.dumps({"ok": False, "error": type(exc).__name__}))
"""


_WSL_HERMES_KEY_ENV_PROBE = r"""
import json
import re
import stat
import sys
from pathlib import Path

request = json.loads(sys.stdin.read())
name = str(request.get("name") or "")
path = Path(str(request.get("env_path") or ""))
result = {
    "ok": False,
    "reason": "target_key_env_unresolved",
    "source": None,
    "secure_permissions": None,
}
try:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        result["reason"] = "target_key_env_name_invalid"
    elif not path.is_absolute() or "\0" in str(path) or path.is_symlink():
        result["reason"] = "target_key_env_path_invalid"
    elif not path.is_file() or path.stat().st_size > 65536:
        result["reason"] = "target_key_env_unresolved"
    else:
        mode = stat.S_IMODE(path.stat().st_mode)
        result["secure_permissions"] = (mode & 0o077) == 0
        if not result["secure_permissions"]:
            result["reason"] = "target_key_env_permissions_insecure"
        else:
            matches = 0
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].lstrip()
                key, separator, value = line.partition("=")
                if separator and key.strip() == name and value.strip() not in {"", "''", '""'}:
                    matches += 1
            if matches == 1:
                result.update({"ok": True, "reason": "ready", "source": "hermes_env_file"})
            elif matches > 1:
                result["reason"] = "target_key_env_duplicate"
except Exception:
    result = {
        "ok": False,
        "reason": "target_key_env_probe_failed",
        "source": None,
        "secure_permissions": None,
    }
print(json.dumps(result))
"""


_WSL_HERMES_KEY_ENV_WRITE = r"""
import json
import os
import re
import stat
import sys
from pathlib import Path

request = json.loads(sys.stdin.read())
name = str(request.get("name") or "")
value = str(request.get("value") or "")
path = Path(str(request.get("env_path") or ""))
result = {
    "ok": False,
    "reason": "target_key_env_write_failed",
    "source": None,
    "secure_permissions": None,
    "changed": False,
}
temp = None
try:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        result["reason"] = "target_key_env_name_invalid"
    elif (
        not path.is_absolute()
        or "\0" in str(path)
        or path.is_symlink()
    ):
        result["reason"] = "target_key_env_path_invalid"
    elif (
        not value
        or len(value) > 4096
        or "\0" in value
        or "\r" in value
        or "\n" in value
    ):
        result["reason"] = "source_token_invalid"
    elif path.exists() and (not path.is_file() or path.stat().st_size > 65536):
        result["reason"] = "target_key_env_path_invalid"
    else:
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        retained = []
        for raw_line in original.splitlines():
            candidate = raw_line.strip()
            if candidate.startswith("export "):
                candidate = candidate[7:].lstrip()
            key, separator, _old_value = candidate.partition("=")
            if separator and key.strip() == name:
                continue
            retained.append(raw_line)
        retained.append(f"{name}={value}")
        content = "\n".join(retained).rstrip("\n") + "\n"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temp = path.with_name(f".{path.name}.nexus-key-{os.getpid()}.tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        temp = None
        os.chmod(path, 0o600)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        mode = stat.S_IMODE(path.stat().st_mode)
        result.update({
            "ok": True,
            "reason": "ready",
            "source": "hermes_env_file",
            "secure_permissions": (mode & 0o077) == 0,
            "changed": content != original,
        })
except Exception:
    result["reason"] = "target_key_env_write_failed"
finally:
    if temp is not None:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
print(json.dumps(result))
"""



def _wsl_config_request(
    distro: str,
    posix_path: str,
    *,
    operation: str,
    content: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Read/write a WSL config over stdin; config bytes never enter argv."""
    request = {"operation": operation, "path": posix_path}
    if content is not None:
        request["content"] = content
    command = ["wsl.exe", "-d", distro, "--exec", "python3", "-c", _WSL_CONFIG_IO]
    try:
        result = runner(
            command,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "error": "wsl_io_unavailable"}
    if getattr(result, "returncode", 1) != 0:
        diagnostic = "\n".join(
            (
                str(getattr(result, "stdout", "") or ""),
                str(getattr(result, "stderr", "") or ""),
            )
        ).replace("\x00", "").casefold()
        if (
            "e_access_denied" in diagnostic
            or "e_accessdenied" in diagnostic
            or "access is denied" in diagnostic
        ):
            return {"ok": False, "error": "wsl_access_denied"}
        return {"ok": False, "error": "wsl_io_failed"}
    try:
        decoded = json.loads(str(getattr(result, "stdout", "") or ""))
    except json.JSONDecodeError:
        return {"ok": False, "error": "wsl_io_invalid_response"}
    return decoded if isinstance(decoded, dict) else {"ok": False, "error": "wsl_io_invalid_response"}


def _dotenv_defines_key(path: Path, key_env: str) -> bool:
    """Return presence only; secret values never leave this helper."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            return False
        matches = 0
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, value = line.partition("=")
            if separator and name.strip() == key_env and value.strip() not in {"", "''", '""'}:
                matches += 1
        return matches == 1
    except OSError:
        return False


def probe_hermes_target_key_env(
    target: dict[str, Any],
    key_env: str,
    *,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Prove Hermes itself can resolve key_env without returning its value.

    The relay catalogue probe may use a Windows-side private bearer. That does
    not prove a detached WSL Hermes process can resolve the provider's
    key_env. WSL therefore checks Hermes' own private .env file and returns
    only typed presence/permission metadata. This function validates; it
    intentionally does not deliver or mutate secrets.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_env):
        return {
            "ok": False,
            "reason": "target_key_env_name_invalid",
            "source": None,
            "secure_permissions": None,
        }

    if target.get("instance") == "wsl":
        config_path = str(target.get("config_path_posix") or "").strip()
        env_path = str(target.get("env_path_posix") or "").strip()
        if not env_path and config_path.startswith("/"):
            env_path = str(Path(config_path).parent / ".env").replace("\\", "/")
        if not env_path.startswith("/"):
            return {
                "ok": False,
                "reason": "target_key_env_path_invalid",
                "source": None,
                "secure_permissions": None,
            }
        command = [
            "wsl.exe",
            "-d",
            str(target.get("distro") or "Ubuntu"),
            "--exec",
            "python3",
            "-c",
            _WSL_HERMES_KEY_ENV_PROBE,
        ]
        request = json.dumps({"name": key_env, "env_path": env_path})
        try:
            completed = runner(
                command,
                input=request,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            completed = None
        if completed is None or getattr(completed, "returncode", 1) != 0:
            return {
                "ok": False,
                "reason": "target_key_env_probe_failed",
                "source": None,
                "secure_permissions": None,
            }
        try:
            decoded = json.loads(str(getattr(completed, "stdout", "") or ""))
        except json.JSONDecodeError:
            decoded = None
        if not isinstance(decoded, dict):
            return {
                "ok": False,
                "reason": "target_key_env_probe_invalid_response",
                "source": None,
                "secure_permissions": None,
            }
        allowed_reasons = {
            "ready",
            "target_key_env_unresolved",
            "target_key_env_name_invalid",
            "target_key_env_path_invalid",
            "target_key_env_permissions_insecure",
            "target_key_env_duplicate",
            "target_key_env_probe_failed",
        }
        reason = str(decoded.get("reason") or "target_key_env_probe_failed")
        if reason not in allowed_reasons:
            reason = "target_key_env_probe_failed"
        source = "hermes_env_file" if decoded.get("source") == "hermes_env_file" else None
        return {
            "ok": bool(decoded.get("ok")) and reason == "ready" and source is not None,
            "reason": reason,
            "source": source,
            "secure_permissions": (
                bool(decoded.get("secure_permissions"))
                if decoded.get("secure_permissions") is not None
                else None
            ),
        }

    env = os.environ if environ is None else environ
    if str(env.get(key_env, "") or "").strip():
        return {
            "ok": True,
            "reason": "ready",
            "source": "process_env",
            "secure_permissions": None,
        }
    config_path = Path(target.get("config_path") or "")
    env_path = Path(target.get("env_path") or config_path.parent / ".env")
    if _dotenv_defines_key(env_path, key_env):
        return {
            "ok": True,
            "reason": "ready",
            "source": "hermes_env_file",
            "secure_permissions": None,
        }
    return {
        "ok": False,
        "reason": "target_key_env_unresolved",
        "source": None,
        "secure_permissions": None,
    }


def _hermes_target_env_path(target: dict[str, Any]) -> str:
    if target.get("instance") == "wsl":
        explicit = str(target.get("env_path_posix") or "").strip()
        if explicit:
            return explicit
        config_path = str(target.get("config_path_posix") or "").strip()
        if config_path.startswith("/") and "/" in config_path:
            return config_path.rsplit("/", 1)[0] + "/.env"
        return ""
    explicit = target.get("env_path")
    if explicit:
        return str(explicit)
    config_path = Path(target.get("config_path") or "")
    return str(config_path.parent / ".env") if str(config_path) else ""


def _replace_dotenv_key(original: str, key_env: str, value: str) -> str:
    retained: list[str] = []
    for raw_line in original.splitlines():
        candidate = raw_line.strip()
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        name, separator, _old_value = candidate.partition("=")
        if separator and name.strip() == key_env:
            continue
        retained.append(raw_line)
    retained.append(f"{key_env}={value}")
    return "\n".join(retained).rstrip("\n") + "\n"


def provision_hermes_target_key_env(
    target: dict[str, Any],
    key_env: str = HERMES_RELAY_KEY_ENV,
    *,
    token: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Atomically provision one Hermes key_env without exposing its value.

    This is deliberately opt-in at the CLI. The secret is transported only in
    subprocess stdin, never argv, generated config, logs, or return payloads.
    """
    value = token if token is not None else load_modelrelay_bearer(key_env)
    if (
        not value
        or len(value) > 4096
        or any(character in value for character in ("\0", "\r", "\n"))
    ):
        return {
            "ok": False,
            "reason": "source_token_missing" if not value else "source_token_invalid",
            "source": None,
            "secure_permissions": None,
            "changed": False,
        }
    env_path = _hermes_target_env_path(target)
    if target.get("instance") == "wsl":
        if not env_path.startswith("/"):
            return {
                "ok": False,
                "reason": "target_key_env_path_invalid",
                "source": None,
                "secure_permissions": None,
                "changed": False,
            }
        command = [
            "wsl.exe",
            "-d",
            str(target.get("distro") or "Ubuntu"),
            "--exec",
            "python3",
            "-c",
            _WSL_HERMES_KEY_ENV_WRITE,
        ]
        try:
            completed = runner(
                command,
                input=json.dumps({"name": key_env, "value": value, "env_path": env_path}),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            decoded = (
                json.loads(str(getattr(completed, "stdout", "") or ""))
                if getattr(completed, "returncode", 1) == 0
                else None
            )
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            decoded = None
        if not isinstance(decoded, dict):
            return {
                "ok": False,
                "reason": "target_key_env_write_failed",
                "source": None,
                "secure_permissions": None,
                "changed": False,
            }
        return {
            "ok": bool(decoded.get("ok")),
            "reason": str(decoded.get("reason") or "target_key_env_write_failed"),
            "source": "hermes_env_file" if decoded.get("source") == "hermes_env_file" else None,
            "secure_permissions": decoded.get("secure_permissions"),
            "changed": bool(decoded.get("changed")),
        }

    path = Path(env_path)
    try:
        if path.is_symlink() or (
            path.exists()
            and (not path.is_file() or path.stat().st_size > 65536)
        ):
            raise ValueError("unsafe env path")
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        content = _replace_dotenv_key(original, key_env, value)
        _atomic_text_write(path, content)
        return {
            "ok": True,
            "reason": "ready",
            "source": "hermes_env_file",
            "secure_permissions": None,
            "changed": content != original,
        }
    except (OSError, ValueError):
        return {
            "ok": False,
            "reason": "target_key_env_write_failed",
            "source": None,
            "secure_permissions": None,
            "changed": False,
        }


def _default_http_json_request(
    url: str,
    token: str | None,
    timeout: float,
) -> tuple[int, dict[str, Any] | None]:
    import urllib.error
    import urllib.request

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return int(response.status), payload if isinstance(payload, dict) else None
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw else None
        except (OSError, json.JSONDecodeError):
            payload = None
        return int(exc.code), payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return 0, None


def _wsl_http_json_request(
    distro: str,
    url: str,
    *,
    token: str | None,
    timeout: float = 8.0,
    runner: Callable[..., Any] = subprocess.run,
) -> tuple[int, dict[str, Any] | None]:
    """Run an HTTP probe inside WSL without putting the bearer in argv."""
    body = json.dumps({"url": url, "token": token, "timeout": timeout})
    command = ["wsl.exe", "-d", distro, "--exec", "python3", "-c", _WSL_HTTP_PROBE]
    try:
        result = runner(
            command,
            input=body,
            capture_output=True,
            text=True,
            timeout=max(5.0, timeout + 3.0),
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0, None
    if getattr(result, "returncode", 1) != 0:
        return 0, None
    try:
        decoded = json.loads(str(getattr(result, "stdout", "") or ""))
    except json.JSONDecodeError:
        return 0, None
    status = int(decoded.get("status") or 0)
    payload = decoded.get("payload")
    return status, payload if isinstance(payload, dict) else None


def _modelrelay_models_url(base_url: str) -> str:
    clean = str(base_url or "").strip().rstrip("/")
    if clean.endswith("/models"):
        return clean
    if clean.endswith("/v1"):
        return clean + "/models"
    return clean + "/v1/models"


def _project_modelrelay_models(payload: dict[str, Any] | None) -> list[str]:
    projected: list[str] = []
    seen: set[str] = set()
    for item in (payload or {}).get("data", []):
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id or model_id.lower() in seen:
            continue
        seen.add(model_id.lower())
        projected.append(model_id)
    return projected


def _model_requirement_present(required: str, models: list[str] | set[str]) -> bool:
    """Match an exact route ID; provider-qualified IDs are distinct offers."""
    required_key = str(required or "").strip().lower()
    if not required_key:
        return False
    return any(str(model or "").strip().lower() == required_key for model in models)


def probe_modelrelay_v1(
    base_url: str,
    *,
    token_env: str = HERMES_RELAY_KEY_ENV,
    required_models: tuple[str, ...] = HERMES_REQUIRED_MODELS,
    environ: Mapping[str, str] | None = None,
    requester: Callable[[str, str | None, float], tuple[int, dict[str, Any] | None]] = _default_http_json_request,
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Prove bearer enforcement and return a safe explicit model projection."""
    env = os.environ if environ is None else environ
    token = str(env.get(token_env, "") or "").strip()
    url = _modelrelay_models_url(base_url)

    anonymous_status, anonymous_payload = requester(url, None, timeout)
    auth_enforced = anonymous_status in {401, 403}
    authenticated_status: int | None = None
    authenticated_payload: dict[str, Any] | None = None
    if auth_enforced and token:
        authenticated_status, authenticated_payload = requester(url, token, timeout)

    source_payload = (
        authenticated_payload
        if authenticated_status == 200
        else anonymous_payload if anonymous_status == 200 else None
    )
    models = _project_modelrelay_models(source_payload)
    missing = [
        model for model in required_models
        if not _model_requirement_present(model, models)
    ]

    if anonymous_status == 200:
        reason = "anonymous_catalog_accessible"
    elif not auth_enforced:
        reason = "anonymous_auth_challenge_missing"
    elif not token:
        reason = "relay_token_missing"
    elif authenticated_status != 200:
        reason = "authenticated_catalog_probe_failed"
    elif not models:
        reason = "authenticated_catalog_empty"
    elif missing:
        reason = "required_models_missing"
    else:
        reason = "ready"

    return {
        "ok": reason == "ready",
        "reason": reason,
        "auth_enforced": auth_enforced,
        "anonymous_status": anonymous_status,
        "authenticated_status": authenticated_status,
        "models": models,
        "model_count": len(models),
        "required_models": list(required_models),
        "missing_required_models": missing,
        "token_env": token_env,
        "url": url,
    }


def _resolve_hermes_relay_base_url(target: dict[str, Any]) -> str | None:
    explicit = str(target.get("relay_base_url") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    if target.get("instance") == "wsl":
        gateway = resolve_wsl_windows_gateway(str(target.get("distro") or "Ubuntu"))
        return f"http://{gateway}:7350/v1" if gateway else None
    return f"{NODE_RELAY_URL}/v1"


def probe_modelrelay_for_target(
    target: dict[str, Any],
    base_url: str,
    *,
    required_models: tuple[str, ...] = HERMES_REQUIRED_MODELS,
) -> dict[str, Any]:
    token_env = str(target.get("key_env") or HERMES_RELAY_KEY_ENV)
    token = load_modelrelay_bearer(token_env)
    probe_environ = {token_env: token} if token else {}
    if target.get("instance") == "wsl":
        distro = str(target.get("distro") or "Ubuntu")

        def requester(url: str, token: str | None, timeout: float):
            return _wsl_http_json_request(distro, url, token=token, timeout=timeout)

        return probe_modelrelay_v1(
            base_url,
            token_env=token_env,
            required_models=required_models,
            environ=probe_environ,
            requester=requester,
        )
    return probe_modelrelay_v1(
        base_url,
        token_env=token_env,
        required_models=required_models,
        environ=probe_environ,
    )
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
        "id": "pi",
        "name": "Pi Coding Agent",
        "version_cmd": ["pi", "--version"],
        "config_path": HOME / ".pi" / "agent" / "models.json",
        "settings_path": HOME / ".pi" / "agent" / "settings.json",
        "extension_path": HOME / ".pi" / "agent" / "extensions" / "nexus-modelrelay-mirror.ts",
        "config_format": "pi-models-json",
        "schema": "https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md",
    },
    {
        "id": "cline",
        "name": "Cline (VS Code ext)",
        "version_cmd": ["code", "--list-extensions"],
        "config_path": CLINE_PROJECT_MCP_CONFIG,
        "config_format": "cline-project-mcp-contract",
        "config_scope": "repository",
        "inference_configuration": "user_owned",
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


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _finite_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed == parsed else 0.0


def _client_health_state(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in {"healthy", "up", "online"}:
        return "healthy"
    if value == "stale":
        return "stale"
    if value in {"rate_limited", "rate-limited", "throttled"}:
        return "rate_limited"
    if value in {"unavailable", "timeout", "down", "noauth", "disabled"}:
        return "unavailable"
    return "unverified"


def _client_model_rank(model: Mapping[str, Any]) -> tuple[int, float, int]:
    health_rank = {
        "healthy": 5,
        "stale": 4,
        "unverified": 3,
        "rate_limited": 2,
        "unavailable": 1,
    }.get(str(model.get("health") or ""), 0)
    return (
        health_rank,
        _finite_float(model.get("quality")),
        _positive_int(model.get("context_tokens")) or 0,
    )


def _project_arena_client_models(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Project only arena-approved chat routes for client configuration.

    The raw relay `/v1/models` feed deliberately exposes aliases and internal
    offers. Clients must receive one canonical CLI ID per eligible offer, not
    image/embedding records or a stale duplicate inventory.
    """
    candidates: dict[str, dict[str, Any]] = {}
    records = payload.get("models", []) if isinstance(payload, Mapping) else []
    for card in records if isinstance(records, list) else []:
        if not isinstance(card, Mapping):
            continue
        routing = card.get("routing") if isinstance(card.get("routing"), Mapping) else {}
        if not routing.get("cli_visible") or routing.get("eligible") is False:
            continue
        route_id = str(routing.get("cli_route_id") or "").strip()
        if not route_id:
            continue
        health = card.get("health") if isinstance(card.get("health"), Mapping) else {}
        registry = card.get("registry") if isinstance(card.get("registry"), Mapping) else {}
        runtime = card.get("runtime") if isinstance(card.get("runtime"), Mapping) else {}
        benchmarks = card.get("benchmarks") if isinstance(card.get("benchmarks"), Mapping) else {}
        dimensions = benchmarks.get("dimensions") if isinstance(benchmarks.get("dimensions"), Mapping) else {}
        capabilities = registry.get("capabilities") if isinstance(registry.get("capabilities"), Mapping) else {}
        candidate = {
            "id": route_id,
            "label": str(card.get("label") or route_id),
            "provider": str(card.get("provider_key") or "relay"),
            "health": _client_health_state(health.get("state") or health.get("raw_status")),
            "status": str(health.get("raw_status") or health.get("state") or "unverified"),
            "context_tokens": _positive_int(registry.get("context_tokens")),
            "max_output_tokens": _positive_int(registry.get("max_output_tokens")),
            "capabilities": dict(capabilities),
            "quality": _finite_float(dimensions.get("quality")),
            "free": registry.get("free"),
            "last_checked_at": health.get("last_checked_at"),
            "source": "arena",
            "runtime_context": runtime.get("context"),
        }
        existing = candidates.get(route_id)
        if existing is None or _client_model_rank(candidate) > _client_model_rank(existing):
            candidates[route_id] = candidate
    return sorted(
        candidates.values(),
        key=lambda item: (-_client_model_rank(item)[0], -_client_model_rank(item)[1], item["label"].lower(), item["id"]),
    )


def _project_client_manifest_models(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Validate the versioned 7356 CLI manifest before configuring clients.

    The manifest is intentionally narrower than `/api/model-cards`: it has one
    canonical route per CLI ID and no provider credentials, raw errors, or
    catalogue aliases.  Do not accept a similarly shaped arbitrary payload;
    the source marker and schema version prevent accidental fallback to a
    stale/static dashboard response.
    """
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        return []
    contract = payload.get("contract") if isinstance(payload.get("contract"), Mapping) else {}
    if contract.get("source") != "nexus-model-arena-live-projection":
        return []
    candidates: dict[str, dict[str, Any]] = {}
    records = payload.get("models", [])
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        route_id = str(record.get("id") or "").strip()
        if not route_id or route_id == "auto-fastest":
            continue
        health_payload = record.get("health") if isinstance(record.get("health"), Mapping) else {}
        benchmark_payload = record.get("benchmarks") if isinstance(record.get("benchmarks"), Mapping) else {}
        dimensions = benchmark_payload.get("dimensions") if isinstance(benchmark_payload.get("dimensions"), Mapping) else {}
        capabilities = record.get("capabilities") if isinstance(record.get("capabilities"), Mapping) else {}
        evidence_backed = benchmark_payload.get("status") == "evidence_backed"
        candidate = {
            "id": route_id,
            "label": str(record.get("label") or route_id),
            "provider": str(record.get("provider") or "relay"),
            "health": _client_health_state(health_payload.get("state")),
            "status": str(health_payload.get("state") or "unverified"),
            "context_tokens": _positive_int(record.get("context_tokens")),
            "max_output_tokens": _positive_int(record.get("max_output_tokens")),
            "capabilities": dict(capabilities),
            "quality": _finite_float(dimensions.get("quality")) if evidence_backed else 0.0,
            "free": record.get("free") if isinstance(record.get("free"), bool) else None,
            "last_checked_at": health_payload.get("last_checked_at"),
            "source": "client_manifest",
            "runtime_context": None,
        }
        existing = candidates.get(route_id)
        if existing is None or _client_model_rank(candidate) > _client_model_rank(existing):
            candidates[route_id] = candidate
    return sorted(
        candidates.values(),
        key=lambda item: (-_client_model_rank(item)[0], -_client_model_rank(item)[1], item["label"].lower(), item["id"]),
    )


def _project_relay_client_models(
    relay_payload: Mapping[str, Any] | None,
    node_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Fallback only when the arena projection is unavailable.

    It keeps the standard relay catalogue reachable without inventing health
    evidence; the arena projection above remains the preferred client manifest.
    """
    node_rows = node_payload.get("models", []) if isinstance(node_payload, Mapping) else []
    status_by_id: dict[str, Mapping[str, Any]] = {}
    for row in node_rows if isinstance(node_rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        model_id = str(row.get("modelId") or "").strip()
        provider = str(row.get("providerKey") or "").strip()
        if model_id:
            status_by_id.setdefault(model_id, row)
        if model_id and provider:
            status_by_id.setdefault(f"{provider}/{model_id}", row)

    records = relay_payload.get("data", []) if isinstance(relay_payload, Mapping) else []
    projected: dict[str, dict[str, Any]] = {}
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        route_id = str(record.get("id") or "").strip()
        if not route_id:
            continue
        source = status_by_id.get(route_id, {})
        raw_status = source.get("status") if isinstance(source, Mapping) else None
        candidate = {
            "id": route_id,
            "label": str(record.get("name") or route_id),
            "provider": str(source.get("providerKey") or record.get("owned_by") or "relay"),
            "health": _client_health_state(raw_status),
            "status": str(raw_status or "unverified"),
            "context_tokens": None,
            "max_output_tokens": None,
            "capabilities": {},
            "quality": 0.0,
            "free": None,
            "last_checked_at": None,
            "source": "relay_fallback",
            "runtime_context": None,
        }
        existing = projected.get(route_id)
        if existing is None or _client_model_rank(candidate) > _client_model_rank(existing):
            projected[route_id] = candidate
    return sorted(projected.values(), key=lambda item: item["id"])


def _curate_client_model_ids(state: Mapping[str, Any], relay_models: list[str]) -> list[str]:
    """Intersect an authenticated relay listing with the safe client manifest."""
    raw = [str(model).strip() for model in relay_models if str(model).strip()]
    source_models = state.get("models") if isinstance(state.get("models"), list) else []
    curated = {
        str(model.get("id") or "").strip()
        for model in source_models if isinstance(model, Mapping)
    }
    if not curated:
        return raw
    required = {"auto-fastest", *HERMES_REQUIRED_MODELS}
    selected = [model for model in raw if model in curated or model in required]
    return selected or raw


def fetch_live_state(refresh: bool = False) -> dict[str, Any]:
    """Pull fresh provider/model state from God Mode Proxy + Node Relay + .modelrelay.json."""
    if refresh:
        _http_post_json(f"{GOD_PROXY_URL}/god/refresh")
    lanes_resp = _http_get_json(f"{GOD_PROXY_URL}/god/lanes") or {}
    models_resp = _http_get_json(f"{GOD_PROXY_URL}/v1/models") or {}
    node_models = _http_get_json(f"{NODE_RELAY_URL}/api/models") or {}
    relay_models = _http_get_json(f"{NODE_RELAY_URL}/v1/models") or {}
    client_manifest = _http_get_json(f"{MODEL_ARENA_URL}/api/client-manifest") or {}

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

    client_models = _project_client_manifest_models(client_manifest)
    model_catalog_source = "client_manifest"
    arena_cards: dict[str, Any] = {}
    if not client_models:
        # Compatibility fallback for a rolling 7356 upgrade.  This request is
        # deliberately avoided on the normal manifest path to keep sync work
        # bounded and make one contract the client source of truth.
        arena_cards = _http_get_json(f"{MODEL_ARENA_URL}/api/model-cards") or {}
        client_models = _project_arena_client_models(arena_cards)
        model_catalog_source = "arena_cards_fallback"
    if not client_models:
        client_models = _project_relay_client_models(relay_models or models_resp, node_models)
        model_catalog_source = "relay_fallback"

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lanes": up_lanes,
        "models": client_models,
        "model_catalog_source": model_catalog_source,
        "arena_cards_alive": bool(client_manifest) or bool(arena_cards),
        "client_manifest_alive": bool(client_manifest),
        "modelrelay_config": mrelay_cfg,
        "god_proxy_alive": bool(lanes_resp) or bool(models_resp),
        "node_relay_alive": bool(node_models) or bool(relay_models),
    }


def _normalized_partner_base_url(value: object) -> str:
    return str(value or "").strip().rstrip("/")


def _active_partner_sync_endpoint(
    modelrelay_config: Mapping[str, Any] | None,
    partner: str,
) -> dict[str, str] | None:
    """Return one active canonical partner endpoint suitable for client sync.

    ModelRelay treats an OpenAI-compatible provider as enabled unless its
    record explicitly says ``enabled: false``.  We retain that runtime
    semantics, but require the reconciler's exact endpoint URL and model ID.
    In particular, models listed in legacy top-level provider records are not
    consulted, so a retired LongCat preview cannot re-enter client configs.
    """
    contract = PARTNER_SYNC_CONTRACTS.get(partner)
    if contract is None or not isinstance(modelrelay_config, Mapping):
        return None
    providers = modelrelay_config.get("providers")
    if not isinstance(providers, Mapping):
        return None
    endpoint_key = contract["endpoint_key"]
    endpoint = providers.get(endpoint_key)
    if not isinstance(endpoint, Mapping) or endpoint.get("enabled") is False:
        return None
    if _normalized_partner_base_url(endpoint.get("baseUrl")) != _normalized_partner_base_url(contract["base_url"]):
        return None
    if str(endpoint.get("modelId") or "").strip() != contract["model_id"]:
        return None

    api_keys = modelrelay_config.get("apiKeys")
    api_keys = api_keys if isinstance(api_keys, Mapping) else {}
    key = str(endpoint.get("api_key") or api_keys.get(endpoint_key) or "").strip()
    if not key:
        return None
    return {
        "endpoint_key": endpoint_key,
        "base_url": contract["base_url"],
        "model_id": contract["model_id"],
        "name": contract["name"],
        "model_label_prefix": contract["model_label_prefix"],
        "api_key": key,
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

    # 2. Partner direct providers.  Project only an active canonical
    # OpenAI-compatible endpoint, never a legacy top-level record.
    mrelay = state.get("modelrelay_config", {})
    for partner in PARTNER_SYNC_CONTRACTS:
        endpoint = _active_partner_sync_endpoint(mrelay, partner)
        if endpoint is None:
            continue
        model_id = endpoint["model_id"]
        entries[partner] = {
            "name": endpoint["name"],
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "baseURL": endpoint["base_url"],
                "apiKey": endpoint["api_key"],
            },
            "models": {model_id: {"name": f"{endpoint['model_label_prefix']} {model_id}"}},
        }

    # 4. NVIDIA NIM direct provider (serial governed active catalog)
    nv = mrelay.get("providers", {}).get("nvidia")
    if nv:
        api_keys = mrelay.get("apiKeys", {})
        key = nv.get("api_key", api_keys.get("nvidia", ""))
        nv_models = nv.get("models") or [
            "minimaxai/minimax-m3",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "qwen/qwen3.5-122b-a10b",
        ]
        models = {}
        for m in nv_models:
            mkey = m.split("/")[-1]
            models[m] = {"name": f"NVIDIA {mkey}"}
        entries["nvidia-nim"] = {
            "name": "NVIDIA NIM (serial active catalog; 8 RPM ceiling)",
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
        if pname in (
            "longcat",
            "internai",
            "nvidia",
            "openai-compatible:baseten",
            "openai-compatible:siliconflow",
            "ollama",
            *(contract["endpoint_key"] for contract in PARTNER_SYNC_CONTRACTS.values()),
        ):
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


def _atomic_text_write(path: Path, content: str) -> None:
    """Write a validated config without exposing a partially written file."""
    temp = path.with_name(f".{path.name}.nexus-sync-{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


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
    """kilo uses auth.json (credentials only). Add canonical partner + Baseten credentials.
    The model list comes from kilo.db; if we add a custom API key, kilo will
    allow it as a custom OpenAI-compatible provider if the baseURL is also set."""
    path = Path(target["config_path"])
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "kilo", "path": str(path), "ok": False, "reason": refuse}

    mrelay = state.get("modelrelay_config", {})
    providers = mrelay.get("providers", {})

    added = []
    # Partner credentials follow the same active endpoint contract as the
    # OpenCode/Mimo/Cline projections.  Do not revive credentials from legacy
    # provider records because that would make retired model IDs reachable.
    for partner in PARTNER_SYNC_CONTRACTS:
        endpoint = _active_partner_sync_endpoint(mrelay, partner)
        if endpoint is None:
            continue
        cfg[partner] = {"type": "api", "key": endpoint["api_key"]}
        added.append(partner)

    api_keys = mrelay.get("apiKeys", {})
    # Baseten
    bt = providers.get("openai-compatible:baseten")
    if bt:
        bt_key = bt.get("api_key", api_keys.get("openai-compatible:baseten", api_keys.get("baseten", "")))
        if bt_key:
            cfg["baseten"] = {"type": "api", "key": bt_key}
            added.append("baseten")
    # Keep modelrelaygod authenticated for the god-relay lane
    if "modelrelaygod" not in cfg:
        cfg["modelrelaygod"] = {"type": "api", "key": "nexus-relay"}
        added.append("modelrelaygod")

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup_before_write(path)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"target": "kilo", "path": str(path), "providers_added": added, "dry_run": dry_run, "ok": True}


def _pi_model_record(model: Mapping[str, Any]) -> dict[str, Any] | None:
    model_id = str(model.get("id") or "").strip()
    if not model_id:
        return None
    health = _client_health_state(model.get("health") or model.get("status"))
    provider = str(model.get("provider") or "relay")
    label = str(model.get("label") or model_id)
    context = _positive_int(model.get("context_tokens")) or 131_072
    max_tokens = _positive_int(model.get("max_output_tokens")) or min(8_192, context)
    capabilities = model.get("capabilities") if isinstance(model.get("capabilities"), Mapping) else {}
    return {
        "id": model_id,
        "name": f"{label} [{health}; {provider}]",
        "reasoning": bool(capabilities.get("thinking")),
        "input": ["text"],
        "contextWindow": context,
        "maxTokens": min(max_tokens, context),
        # Pi's price display cannot represent provider-side free/credit policy.
        # The relay remains the source of cost and quota telemetry.
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    }


def _build_pi_relay_models(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Render one curated, deduplicated Pi model list from the arena manifest."""
    rendered = [
        {
            "id": "auto-fastest",
            "name": "NEXUS Auto Fastest [governed router]",
            "reasoning": True,
            "input": ["text"],
            "contextWindow": 131_072,
            "maxTokens": 8_192,
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        }
    ]
    seen = {"auto-fastest"}
    for source in state.get("models", []) if isinstance(state.get("models"), list) else []:
        if not isinstance(source, Mapping):
            continue
        record = _pi_model_record(source)
        if record is None or record["id"] in seen:
            continue
        seen.add(record["id"])
        rendered.append(record)
    return rendered


def _sync_pi_mirror_extension(path: Path | None, dry_run: bool) -> dict[str, Any]:
    """Repair only the known stale 7352 default in Pi's managed mirror.

    The extension honours NEXUS_MODELRELAY_URL, so this targeted replacement
    retains a user override and avoids rewriting unrelated extension code.
    """
    if path is None or not path.exists():
        return {"ok": True, "state": "not_present"}
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "state": "unreadable", "reason": type(exc).__name__}
    if "NEXUS_MODELRELAY_URL" not in original:
        return {"ok": True, "state": "unmanaged"}
    if PI_LEGACY_RELAY_DEFAULT not in original:
        state = "already_current" if PI_RELAY_DEFAULT in original else "unmanaged"
        return {"ok": True, "state": state}
    candidate = original.replace(PI_LEGACY_RELAY_DEFAULT, PI_RELAY_DEFAULT)
    if dry_run:
        return {"ok": True, "state": "would_update"}
    try:
        _backup_before_write(path)
        _atomic_text_write(path, candidate)
    except OSError as exc:
        return {"ok": False, "state": "write_failed", "reason": type(exc).__name__}
    return {"ok": True, "state": "updated"}


def sync_pi(state: dict, target: dict, dry_run: bool) -> dict:
    """Synchronize Pi's OpenAI-compatible ModelRelay manifest safely.

    Pi officially reloads models.json from its /model UI. We preserve Pi's
    selected default in settings.json and replace only the NEXUS-managed
    provider with the arena's canonical CLI-visible chat routes.
    """
    path = Path(target["config_path"])
    cfg, refuse = _read_json_config_guarded(path)
    if cfg is None:
        return {"target": "pi", "path": str(path), "ok": False, "reason": refuse}
    providers = cfg.setdefault("providers", {})
    if not isinstance(providers, dict):
        return {"target": "pi", "path": str(path), "ok": False, "reason": "providers is not an object — refusing to overwrite"}
    existing = providers.get(PI_RELAY_PROVIDER_ID, {})
    if existing is not None and not isinstance(existing, dict):
        return {"target": "pi", "path": str(path), "ok": False, "reason": "Pi ModelRelay provider is not an object — refusing to overwrite"}
    existing = dict(existing or {})
    if existing.get("__user_protected__"):
        return {
            "target": "pi",
            "path": str(path),
            "ok": True,
            "reason": "user_protected",
            "providers_added": [],
            "dry_run": dry_run,
        }

    extension_path = target.get("extension_path")
    mirror = _sync_pi_mirror_extension(Path(extension_path) if extension_path else None, dry_run)
    if not mirror.get("ok"):
        return {
            "target": "pi",
            "path": str(path),
            "ok": False,
            "reason": "pi_mirror_extension_unwritable",
            "mirror_extension": mirror,
            "dry_run": dry_run,
        }

    compat = existing.get("compat") if isinstance(existing.get("compat"), dict) else {}
    merged_compat = dict(compat)
    merged_compat.setdefault("supportsDeveloperRole", False)
    merged_compat.setdefault("supportsReasoningEffort", False)
    merged_compat.setdefault("supportsUsageInStreaming", False)
    merged_compat.setdefault("maxTokensField", "max_tokens")
    api_key = str(existing.get("apiKey") or "").strip()
    if not api_key:
        api_key = "$NEXUS_MODELRELAY_API_KEY" if os.environ.get(HERMES_RELAY_KEY_ENV) else "nexus"
    provider = dict(existing)
    provider.update({
        "baseUrl": PI_RELAY_DEFAULT,
        "api": "openai-completions",
        "apiKey": api_key,
        "compat": merged_compat,
        "models": _build_pi_relay_models(state),
    })
    providers[PI_RELAY_PROVIDER_ID] = provider

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup_before_write(path)
        _atomic_text_write(path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    health_counts: dict[str, int] = {}
    for model in state.get("models", []) if isinstance(state.get("models"), list) else []:
        health = _client_health_state(model.get("health") if isinstance(model, Mapping) else None)
        health_counts[health] = health_counts.get(health, 0) + 1
    return {
        "target": "pi",
        "path": str(path),
        "ok": True,
        "providers_added": [PI_RELAY_PROVIDER_ID],
        "model_count": len(provider["models"]),
        "catalog_source": state.get("model_catalog_source"),
        "health_counts": health_counts,
        "mirror_extension": mirror,
        "dry_run": dry_run,
    }


def sync_cline(state: dict, target: dict, dry_run: bool) -> dict:
    """Report Cline's repo-local MCP contract without touching user inference settings.

    Cline owns its provider selection, OpenAI-compatible base URL, bearer, and
    model ID in its own settings/auth surface.  The old VS Code settings.json
    projection was neither an official provider schema nor evidence that Cline
    would use ModelRelay, so this handler must not read or write it.
    """
    del state, target
    contract_present = CLINE_PROJECT_MCP_CONFIG.is_file()
    inference = {
        "status": "not_inspected",
        "configuration_owner": "user",
        "requirements": list(CLINE_INFERENCE_REQUIREMENTS),
    }
    result = {
        "target": "cline",
        "path": str(CLINE_PROJECT_MCP_CONFIG),
        "mode": "project_mcp_contract_only",
        "providers_added": [],
        "mcp_contract": {
            "path": str(CLINE_PROJECT_MCP_CONFIG),
            "present": contract_present,
        },
        "inference": inference,
        "dry_run": dry_run,
        "ok": contract_present,
    }
    if not contract_present:
        result["reason"] = "repo-local .cline/mcp.json not found"
    return result


def _hermes_modelrelay_provider(
    base_url: str,
    key_env: str,
    models: list[str],
) -> dict[str, Any]:
    return {
        "name": "NEXUS ModelRelay",
        "base_url": base_url,
        "key_env": key_env,
        "transport": "openai_chat",
        "discover_models": False,
        "models": {model_id: {"name": model_id} for model_id in models},
    }


def _render_hermes_managed_block(provider: dict[str, Any]) -> str:
    import yaml

    body = yaml.safe_dump(
        {"modelrelay": provider},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip()
    indented = "\n".join(f"  {line}" if line else "" for line in body.splitlines())
    return (
        f"  {HERMES_MANAGED_START}\n"
        f"{indented}\n"
        f"  {HERMES_MANAGED_END}\n"
    )


def _remove_hermes_managed_block(original: str) -> str:
    pattern = re.compile(
        rf"(?ms)^[ \t]*{re.escape(HERMES_MANAGED_START)}[ \t]*\r?\n"
        rf".*?^[ \t]*{re.escape(HERMES_MANAGED_END)}[ \t]*(?:\r?\n)?"
    )
    return pattern.sub("", original)


def _replace_hermes_managed_block(original: str, managed_block: str) -> str:
    cleaned = _remove_hermes_managed_block(original)
    # Replace a pre-existing bare providers.modelrelay entry instead of
    # creating a duplicate YAML key whose stale value could win on parse.
    existing_child = re.compile(
        r"(?m)^  modelrelay:[^\r\n]*(?:\r?\n(?: {4,}[^\r\n]*|[ \t]*))*"
    )
    cleaned = existing_child.sub("", cleaned, count=1)
    empty_map = re.compile(r"(?m)^providers:[ \t]*\{[ \t]*\}[ \t]*$")
    if empty_map.search(cleaned):
        return empty_map.sub(
            "providers:\n" + managed_block.rstrip("\n"),
            cleaned,
            count=1,
        )
    block_parent = re.search(r"(?m)^providers:\s*(?:#.*)?(?:\r?\n|$)", cleaned)
    if block_parent:
        return cleaned[: block_parent.end()] + managed_block + cleaned[block_parent.end() :]
    return cleaned.rstrip() + "\n\nproviders:\n" + managed_block


def _hermes_uses_modelrelay(config: Mapping[str, Any]) -> bool:
    model = config.get("model")
    if isinstance(model, dict) and str(model.get("provider") or "").strip() == "modelrelay":
        return True
    return str(
        config.get("default_provider")
        or config.get("provider")
        or ""
    ).strip() == "modelrelay"


def _is_hermes_locked_glm_selection(value: Any) -> bool:
    """Recognize the managed GLM aliases eligible for exact-offer migration."""
    return str(value or "").strip().lower() in HERMES_LEGACY_PRIMARY_MODEL_IDS


def _replace_top_level_yaml_value(original: str, key: str, value: Any) -> str:
    """Replace one top-level YAML value while preserving unrelated text."""
    import yaml

    newline = "\r\n" if "\r\n" in original else "\n"
    rendered = yaml.safe_dump(
        {key: value},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).replace("\n", newline)
    lines = original.splitlines(keepends=True)
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(rf"^{re.escape(key)}\s*:", line)
        ),
        None,
    )
    if start is None:
        prefix = original.rstrip("\r\n")
        separator = newline * 2 if prefix else ""
        return prefix + separator + rendered
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if (
            not line.strip()
            or line.startswith((" ", "\t"))
            or re.match(r"^-(?:\s|$)", line)
        ):
            end += 1
            continue
        break
    return "".join(lines[:start]) + rendered + "".join(lines[end:])


def _managed_hermes_fallback(base_url: str) -> dict[str, str]:
    """Render the documented Hermes fallback-chain entry shape.

    Credentials belong to the named ``providers.modelrelay`` definition.  Hermes
    resolves that provider before attempting this entry, while fallback entries
    themselves only select the provider, model, and optional endpoint override.
    """
    return {
        "provider": "modelrelay",
        "model": HERMES_FALLBACK_MODEL,
        "base_url": base_url,
    }


def _is_nexusctl_managed_hermes_fallback(
    entry: Any,
    *,
    model_id: str,
) -> bool:
    """Recognize only the exact fallback shape emitted by this synchronizer.

    This lets the resilient-alias migration remove the prior managed
    Leanstral retry without deleting a user-authored fallback that carries
    additional intent or provider-specific options.
    """
    return (
        isinstance(entry, Mapping)
        and set(entry) == {"provider", "model", "base_url"}
        and str(entry.get("provider") or "") == "modelrelay"
        and str(entry.get("model") or "") == model_id
        and isinstance(entry.get("base_url"), str)
    )


def _is_any_nexusctl_managed_hermes_fallback(entry: Any) -> bool:
    return any(
        _is_nexusctl_managed_hermes_fallback(entry, model_id=model_id)
        for model_id in (
            HERMES_FALLBACK_MODEL,
            HERMES_LEGACY_MANAGED_FALLBACK_MODEL,
        )
    )


def _managed_hermes_auxiliary_title(
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pin cheap auxiliary work without discarding task-specific settings."""
    managed = copy.deepcopy(dict(existing or {}))
    # Credentials resolve exclusively through providers.modelrelay.  A title
    # route may retain task-specific options (for example max_tokens), but it
    # must never carry a second key environment pointer.
    managed.pop("key_env", None)
    managed["provider"] = "modelrelay"
    managed["model"] = HERMES_AUXILIARY_TITLE_MODEL
    return managed


def _reconcile_hermes_runtime_settings(
    original: str,
    base_url: str,
    key_env: str,
) -> tuple[str, bool]:
    """Repair active ModelRelay runtime arrows without touching other settings."""
    import yaml

    try:
        config = yaml.safe_load(original) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("top-level Hermes config must be a mapping")
    active = _hermes_uses_modelrelay(config)
    if not active:
        return original, False

    model = config.get("model")
    if not isinstance(model, dict):
        raise ValueError("active modelrelay model config must be a mapping")
    model = copy.deepcopy(model)
    model["base_url"] = base_url
    # Only migrate the historical GLM lock.  A user who selected another
    # ModelRelay model retains that explicit choice.
    if _is_hermes_locked_glm_selection(model.get("default")):
        model["default"] = HERMES_PRIMARY_MODEL

    agent = config.get("agent")
    if agent is None:
        agent = {}
    if not isinstance(agent, dict):
        raise ValueError("agent config must be a mapping")
    agent = copy.deepcopy(agent)
    agent["api_max_retries"] = HERMES_API_MAX_RETRIES

    fallbacks = config.get("fallback_providers")
    if fallbacks is None:
        fallbacks = []
    if not isinstance(fallbacks, list):
        raise ValueError("fallback_providers must be a list")
    retained = [
        copy.deepcopy(entry)
        for entry in fallbacks
        if not _is_any_nexusctl_managed_hermes_fallback(entry)
    ]
    fallbacks = [_managed_hermes_fallback(base_url), *retained]

    auxiliary = config.get("auxiliary")
    if auxiliary is None:
        auxiliary = {}
    if not isinstance(auxiliary, dict):
        raise ValueError("auxiliary config must be a mapping")
    auxiliary = copy.deepcopy(auxiliary)
    title_generation = auxiliary.get("title_generation")
    if title_generation is not None and not isinstance(title_generation, dict):
        raise ValueError("auxiliary.title_generation must be a mapping")
    auxiliary["title_generation"] = _managed_hermes_auxiliary_title(title_generation)

    candidate = _replace_top_level_yaml_value(original, "model", model)
    candidate = _replace_top_level_yaml_value(candidate, "agent", agent)
    candidate = _replace_top_level_yaml_value(candidate, "fallback_providers", fallbacks)
    candidate = _replace_top_level_yaml_value(candidate, "auxiliary", auxiliary)
    return candidate, True


def _normalized_hermes_for_validation(
    config: Mapping[str, Any],
    *,
    allow_managed_runtime: bool,
) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(config))
    normalized.pop("providers", None)
    if not allow_managed_runtime:
        return normalized
    model = normalized.get("model")
    if isinstance(model, dict):
        model.pop("base_url", None)
        # The managed GLM lock is deliberately migrated from the bare alias
        # to the exact NVIDIA route.  It is runtime wiring, not a user-setting
        # mutation for the preservation comparison below.
        if _is_hermes_locked_glm_selection(model.get("default")):
            model.pop("default", None)
    agent = normalized.get("agent")
    if isinstance(agent, dict):
        agent.pop("api_max_retries", None)
        if not agent:
            normalized.pop("agent", None)
    fallbacks = normalized.get("fallback_providers")
    if isinstance(fallbacks, list):
        residual = [
            entry
            for entry in fallbacks
            if not _is_any_nexusctl_managed_hermes_fallback(entry)
        ]
        if residual:
            normalized["fallback_providers"] = residual
        else:
            normalized.pop("fallback_providers", None)
    auxiliary = normalized.get("auxiliary")
    if isinstance(auxiliary, dict):
        title_generation = auxiliary.get("title_generation")
        if isinstance(title_generation, dict):
            title_generation.pop("provider", None)
            title_generation.pop("model", None)
            title_generation.pop("key_env", None)
            if not title_generation:
                auxiliary.pop("title_generation", None)
        if not auxiliary:
            normalized.pop("auxiliary", None)
    return normalized


def _validate_hermes_candidate(
    original: str,
    candidate: str,
    required_models: tuple[str, ...] = HERMES_REQUIRED_MODELS,
    *,
    expected_base_url: str | None = None,
    expected_key_env: str = HERMES_RELAY_KEY_ENV,
) -> str | None:
    import yaml

    try:
        before = yaml.safe_load(_remove_hermes_managed_block(original)) or {}
        after = yaml.safe_load(candidate) or {}
    except yaml.YAMLError as exc:
        return f"invalid YAML: {exc}"
    if not isinstance(before, dict) or not isinstance(after, dict):
        return "top-level Hermes config must be a mapping"
    managed_runtime = _hermes_uses_modelrelay(before) or _hermes_uses_modelrelay(after)
    before_nonproviders = _normalized_hermes_for_validation(
        before,
        allow_managed_runtime=managed_runtime,
    )
    after_nonproviders = _normalized_hermes_for_validation(
        after,
        allow_managed_runtime=managed_runtime,
    )
    if before_nonproviders != after_nonproviders:
        return "non-provider Hermes settings changed"
    providers = after.get("providers")
    if not isinstance(providers, dict):
        return "providers is not a mapping"
    relay = providers.get("modelrelay")
    if not isinstance(relay, dict):
        return "managed modelrelay provider missing"
    if "api_key" in relay:
        return "managed provider contains a plaintext api_key"
    if relay.get("key_env") != expected_key_env:
        return "managed provider key_env mismatch"
    if expected_base_url and relay.get("base_url") != expected_base_url:
        return "managed provider base_url mismatch"
    models = relay.get("models")
    if not isinstance(models, dict) or not models:
        return "managed provider model projection is empty"
    model_ids = [str(model) for model in models]
    if any(not _model_requirement_present(model, model_ids) for model in required_models):
        return "managed provider required model missing"
    if managed_runtime:
        model = after.get("model")
        if not isinstance(model, dict) or model.get("base_url") != expected_base_url:
            return "active modelrelay base_url mismatch"
        before_model = before.get("model")
        if (
            isinstance(before_model, dict)
            and _is_hermes_locked_glm_selection(before_model.get("default"))
            and model.get("default") != HERMES_PRIMARY_MODEL
        ):
            return "active modelrelay primary model mismatch"
        agent = after.get("agent")
        if (
            not isinstance(agent, dict)
            or agent.get("api_max_retries") != HERMES_API_MAX_RETRIES
        ):
            return "active modelrelay retry budget mismatch"
        fallbacks = after.get("fallback_providers")
        expected_fallback = _managed_hermes_fallback(str(expected_base_url or ""))
        if not isinstance(fallbacks, list) or expected_fallback not in fallbacks:
            return "active modelrelay fallback missing"
        if any(
            _is_nexusctl_managed_hermes_fallback(
                entry,
                model_id=HERMES_LEGACY_MANAGED_FALLBACK_MODEL,
            )
            for entry in fallbacks
        ):
            return "legacy managed Leanstral fallback retained"
        auxiliary = after.get("auxiliary")
        title_generation = (
            auxiliary.get("title_generation")
            if isinstance(auxiliary, dict)
            else None
        )
        if (
            not isinstance(title_generation, dict)
            or title_generation.get("provider") != "modelrelay"
            or title_generation.get("model") != HERMES_AUXILIARY_TITLE_MODEL
            or "key_env" in title_generation
        ):
            return "active modelrelay auxiliary title route missing"
    return None


def _read_hermes_config(target: dict[str, Any], path: Path) -> tuple[str | None, str | None]:
    if target.get("instance") == "wsl" and target.get("config_path_posix"):
        posix_path = str(target.get("config_path_posix") or "").strip()
        result = _wsl_config_request(
            str(target.get("distro") or "Ubuntu"),
            posix_path,
            operation="read",
        )
        content = result.get("content")
        if result.get("ok") and isinstance(content, str):
            return content, None
        return None, str(result.get("error") or "wsl_config_unreadable")
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"config_unreadable:{type(exc).__name__}"


def _write_hermes_config(target: dict[str, Any], path: Path, content: str) -> str | None:
    if target.get("instance") == "wsl" and target.get("config_path_posix"):
        result = _wsl_config_request(
            str(target.get("distro") or "Ubuntu"),
            str(target.get("config_path_posix") or ""),
            operation="write",
            content=content,
        )
        return None if result.get("ok") else str(result.get("error") or "wsl_write_failed")
    try:
        _backup_before_write(path)
        _atomic_text_write(path, content)
        return None
    except OSError as exc:
        return f"write_failed:{type(exc).__name__}"


def sync_hermes(state: dict, target: dict, dry_run: bool) -> dict:
    """Sync one Hermes instance only after an authenticated relay smoke."""
    target_id = str(target.get("id") or "hermes")
    instance = str(target.get("instance") or "windows")
    path = Path(target["config_path"])
    display_path = str(target.get("config_path_posix") or path) if instance == "wsl" else str(path)
    common = {
        "target": target_id,
        "instance": instance,
        "path": display_path,
        "providers_added": ["modelrelay"],
        "dry_run": dry_run,
        "written": False,
    }
    original, read_error = _read_hermes_config(target, path)
    if original is None:
        return {
            **common,
            "ok": False,
            "apply_ready": False,
            "reason": "hermes_config_unreadable",
            "read_error": read_error,
        }

    base_url = _resolve_hermes_relay_base_url(target)
    if not base_url:
        return {
            **common,
            "ok": False,
            "apply_ready": False,
            "reason": "wsl_windows_gateway_unresolved",
        }
    key_env = str(target.get("key_env") or HERMES_RELAY_KEY_ENV)
    target_key_probe = probe_hermes_target_key_env(target, key_env)
    probe = probe_modelrelay_for_target(target, base_url)
    raw_models = list(probe.get("models") or [])
    models = _curate_client_model_ids(state, raw_models)
    missing = [
        model for model in HERMES_REQUIRED_MODELS
        if not _model_requirement_present(model, models)
    ]
    provider = _hermes_modelrelay_provider(base_url, key_env, models)
    provider_preview = {key: value for key, value in provider.items() if key != "models"}
    provider_preview["models_count"] = len(models)
    provider_preview["models_sample"] = models[:10]
    relay_ready = bool(probe.get("ok")) and bool(models) and not missing
    apply_ready = relay_ready and bool(target_key_probe.get("ok"))
    if missing:
        readiness_reason = "required_models_missing"
    elif not relay_ready:
        readiness_reason = str(probe.get("reason") or "relay_probe_failed")
    elif not target_key_probe.get("ok"):
        readiness_reason = str(target_key_probe.get("reason") or "target_key_env_unresolved")
    else:
        readiness_reason = "ready"
    result = {
        **common,
        "ok": bool(dry_run),
        "apply_ready": apply_ready,
        "reason": readiness_reason,
        "relay_base_url": base_url,
        "auth_enforced": bool(probe.get("auth_enforced")),
        "anonymous_status": probe.get("anonymous_status"),
        "authenticated_status": probe.get("authenticated_status"),
        "models_projected": len(models),
        "models_discovered": len(raw_models),
        "model_catalog_source": state.get("model_catalog_source"),
        "target_key_resolved": bool(target_key_probe.get("ok")),
        "target_key_reason": target_key_probe.get("reason"),
        "target_key_source": target_key_probe.get("source"),
        "target_key_secure_permissions": target_key_probe.get("secure_permissions"),
        "required_models_present": not missing,
        "missing_required_models": missing,
        "provider_preview": provider_preview,
    }
    if not apply_ready:
        return result if dry_run else {**result, "ok": False}

    try:
        runtime_candidate, runtime_managed = _reconcile_hermes_runtime_settings(
            original,
            base_url,
            key_env,
        )
    except ValueError as exc:
        return {
            **result,
            "ok": bool(dry_run),
            "apply_ready": False,
            "reason": "candidate_validation_failed",
            "validation_error": str(exc),
        }
    managed_block = _render_hermes_managed_block(provider)
    candidate = _replace_hermes_managed_block(runtime_candidate, managed_block)
    validation_error = _validate_hermes_candidate(
        original,
        candidate,
        expected_base_url=base_url,
        expected_key_env=key_env,
    )
    result = {
        **result,
        "runtime_settings_managed": runtime_managed,
        "api_max_retries": HERMES_API_MAX_RETRIES if runtime_managed else None,
        "fallback_model": HERMES_FALLBACK_MODEL if runtime_managed else None,
        "auxiliary_title_model": HERMES_AUXILIARY_TITLE_MODEL if runtime_managed else None,
    }
    if validation_error:
        return {
            **result,
            "ok": bool(dry_run),
            "apply_ready": False,
            "reason": "candidate_validation_failed",
            "validation_error": validation_error,
        }
    if dry_run:
        return result

    write_error = _write_hermes_config(target, path, candidate)
    if write_error:
        return {
            **result,
            "ok": False,
            "reason": "write_failed",
            "write_error": write_error,
        }
    return {**result, "ok": True, "reason": "written", "written": True}


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
    "pi": sync_pi,
    "cline": sync_cline,
    "hermes": sync_hermes,
    "hermes-wsl": sync_hermes,
    "nexusctl": sync_nexusctl,
}


def resolved_cli_targets() -> list[dict[str, Any]]:
    """Replace the legacy single Hermes row with platform-specific targets."""
    hermes_targets = discover_hermes_targets()
    resolved: list[dict[str, Any]] = []
    for target in CLI_TARGETS:
        if target["id"] == "hermes":
            resolved.extend(hermes_targets)
        else:
            resolved.append(dict(target))
    return resolved


def list_cli_inventory(
    state: dict,
    *,
    targets: list[dict[str, Any]] | None = None,
    wsl_inventory: list[dict[str, Any]] | None = None,
) -> dict:
    """Show Windows targets plus read-only, non-syncable WSL observations."""
    inventory = []
    for target in targets or resolved_cli_targets():
        cfg_path = Path(target["config_path"])
        try:
            cfg_exists = cfg_path.exists()
        except OSError:
            cfg_exists = False
        alive = False
        try:
            r = subprocess.run(
                target["version_cmd"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            alive = r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            alive = False
        binary_path = str(target.get("binary_path") or "")
        inventory.append({
            "id": target["id"],
            "name": target["name"],
            "instance": target.get("instance") or "windows",
            "binary_installed": alive,
            "binary_path": binary_path or None,
            "binary_kind": target.get("binary_kind") or classify_cli_binary(binary_path),
            "config_path": str(cfg_path),
            "config_path_posix": target.get("config_path_posix"),
            "discovery_source": target.get("discovery_source"),
            "config_exists": cfg_exists,
            "config_format": target["config_format"],
        })
    inventory.extend(
        copy.deepcopy(
            discover_wsl_cli_inventory() if wsl_inventory is None else wsl_inventory
        )
    )
    return {
        "clis": inventory,
        "state": {
            "lanes": len(state.get("lanes", [])),
            "models": len(state.get("models", [])),
        },
    }


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
    target_choices = sorted({t["id"] for t in CLI_TARGETS} | {"hermes-wsl"})
    ap.add_argument("--only", choices=target_choices, help="Sync only this CLI")
    ap.add_argument("--install-schedule", action="store_true", help="Install the 1-hour Windows scheduled task")
    ap.add_argument("--log", help="Log file path")
    ap.add_argument(
        "--provision-hermes-key",
        action="store_true",
        help="Opt-in atomic delivery of the private relay bearer to one Hermes target",
    )
    args = ap.parse_args(argv)
    if args.provision_hermes_key and (
        args.dry_run or args.only not in {"hermes", "hermes-wsl"}
    ):
        print(json.dumps({
            "error": "--provision-hermes-key requires a non-dry-run --only hermes or hermes-wsl target",
        }, indent=2))
        return 2



    if args.install_schedule:
        result = install_hourly_schedule()
        print(json.dumps(result, indent=2))
        return 0 if result.get("installed") else 1

    state = fetch_live_state(refresh=args.refresh)
    auto_revive_attempted = False
    if not args.dry_run and not state["god_proxy_alive"] and not state["node_relay_alive"]:
        # Relays die after a PC restart; auto-revive once before giving up so that
        # `nexusctl model-sync` (and therefore Hermes + every CLI wiring) can proceed
        # even from a cold boot. A dry-run is intentionally excluded: it must
        # remain a safe planning/diagnosis operation with no service mutation.
        auto_revive_attempted = True
        revived = _auto_revive_relays()
        if revived:
            time.sleep(3)
            state = fetch_live_state(refresh=True)
    if not state["god_proxy_alive"] and not state["node_relay_alive"]:
        print(json.dumps({
            "error": "Neither God Mode Proxy (7357) nor Node ModelRelay (7350) reachable",
            "auto_revive_attempted": auto_revive_attempted,
            "dry_run": args.dry_run,
            "hint": "Start them with:  scripts\\revive_relay_ports.ps1  (or install: scripts\\install_nexus_autostart.ps1)",
        }, indent=2))
        return 2

    runtime_targets = resolved_cli_targets()
    if args.list:
        print(json.dumps(list_cli_inventory(state, targets=runtime_targets), indent=2))
        return 0

    if args.only == "hermes":
        targets = [
            target
            for target in runtime_targets
            if target["id"] in {"hermes", "hermes-wsl"}
        ]
    else:
        targets = [
            target
            for target in runtime_targets
            if args.only is None or target["id"] == args.only
        ]
    results = []
    for tgt in targets:
        handler = SYNC_HANDLERS.get(tgt["id"])
        if not handler:
            results.append({"target": tgt["id"], "ok": False, "reason": "no handler"})
            continue
        provisioning = None
        if args.provision_hermes_key:
            provisioning = provision_hermes_target_key_env(
                tgt,
                str(tgt.get("key_env") or HERMES_RELAY_KEY_ENV),
            )
            if not provisioning.get("ok"):
                results.append({
                    "target": tgt["id"],
                    "ok": False,
                    "reason": provisioning.get("reason"),
                    "credential_provisioning": provisioning,
                })
                continue
        try:
            r = handler(state, tgt, dry_run=args.dry_run)
            if provisioning is not None:
                r = {**r, "credential_provisioning": provisioning}
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
    return 0 if results and all(result.get("ok") for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
