#!/usr/bin/env python3
# CANARY: cd590beb421487a227de2fbc0be4e573
"""
pull_benchmark_models.py — Pull and verify RP models for NEXUS BOUNCER benchmark.

Models to pull:
1. UmbrellaInc/Neo_T-Virus-3.2-1B (via mradermacher GGUF if available)
2. UmbrellaInc/Special-Virus-3.2-1B (via mradermacher GGUF if available)
3. LiquidAI/LFM2.5-1.2B-Instruct-GGUF

Usage:
    python3 scripts/pull_benchmark_models.py
"""
import json
import subprocess
import time
import urllib.request
import urllib.error
import sys
from pathlib import Path

OLLAMA_EXE = Path("/mnt/c/Users/speci.000/AppData/Local/Programs/Ollama/ollama.exe")
OLLAMA_URL = "http://127.0.0.1:11435"

# Models to pull — try Ollama library names first, fallback to hf.co/... GGUF
MODELS = [
    {
        "name": "Neo_T-Virus-3.2-1B",
        "ollama_name": "hf.co/mradermacher/Neo_T-Virus-3.2-1B-GGUF:latest",
        "fallback": None,
        "size_gb": 0.7,
    },
    {
        "name": "Special-Virus-3.2-1B",
        "ollama_name": "hf.co/mradermacher/Special-Virus-3.2-1B-GGUF:latest",
        "fallback": None,
        "size_gb": 0.7,
    },
    {
        "name": "LFM2.5-1.2B-Instruct",
        "ollama_name": "hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:latest",
        "fallback": None,
        "size_gb": 0.8,
    },
]


def run_powershell(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a PowerShell command and return (returncode, stdout, stderr)."""
    ps_cmd = ["powershell.exe", "-Command", cmd]
    proc = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def kill_ollama():
    """Kill any running ollama.exe processes."""
    print("[INFO] Killing existing ollama processes...")
    rc, out, err = run_powershell(
        "Stop-Process -Name ollama -Force -ErrorAction SilentlyContinue; "
        "Start-Sleep -Seconds 2; "
        "Write-Output 'Ollama processes stopped'",
        timeout=15
    )
    if rc != 0:
        print(f"[WARN] Could not stop ollama gracefully: {err.strip()}")
    else:
        print(f"[OK] {out.strip()}")


def start_ollama():
    """Start Ollama server on port 11435."""
    print("[INFO] Starting Ollama server on port 11435...")
    import os
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:11435"
    env["OLLAMA_ORIGINS"] = "*"
    proc = subprocess.Popen(
        [str(OLLAMA_EXE), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[INFO] Ollama serve PID: {proc.pid}")
    return proc


def wait_for_ollama(max_wait: int = 60) -> bool:
    """Wait for Ollama to be ready."""
    print("[INFO] Waiting for Ollama to be ready...")
    for i in range(max_wait):
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"[OK] Ollama ready after {i+1}s")
                    return True
        except Exception:
            pass
        time.sleep(1)
    print("[ERROR] Ollama did not become ready in time")
    return False


def list_models() -> list[str]:
    """List available Ollama models."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[ERROR] Failed to list models: {e}")
        return []


def pull_model(ollama_name: str) -> bool:
    """Pull a model via Ollama API."""
    print(f"[INFO] Pulling {ollama_name}...")
    try:
        payload = json.dumps({"name": ollama_name}).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            # The pull API streams progress lines
            for line in resp:
                try:
                    msg = json.loads(line.decode("utf-8"))
                    if msg.get("status") == "success":
                        print(f"[OK] Pulled {ollama_name}")
                        return True
                    elif "completed" in msg and "total" in msg:
                        pct = msg["completed"] / msg["total"] * 100
                        print(f"\r[PROGRESS] {pct:.1f}%", end="", flush=True)
                except Exception:
                    pass
            print()  # newline after progress
            return True
    except Exception as e:
        print(f"[ERROR] Failed to pull {ollama_name}: {e}")
        return False


def test_model(model_name: str) -> bool:
    """Quick probe to verify model produces output."""
    print(f"[INFO] Testing {model_name}...")
    try:
        payload = json.dumps({
            "model": model_name,
            "prompt": "Respond with exactly one word: SAFE or UNSAFE.\nUser: hello\n",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 10},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            response = data.get("response", "").strip()
            print(f"[OK] {model_name} response: '{response}'")
            return len(response) > 0
    except Exception as e:
        print(f"[ERROR] {model_name} test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("NEXUS Model Pull & Verify")
    print("=" * 60)

    # 1. Kill old ollama
    kill_ollama()

    # 2. Start fresh ollama
    ollama_proc = start_ollama()
    time.sleep(3)

    # 3. Wait for ready
    if not wait_for_ollama(max_wait=60):
        print("[FATAL] Could not start Ollama. Exiting.")
        sys.exit(1)

    # 4. Show existing models
    existing = list_models()
    if existing:
        print(f"[INFO] Existing models ({len(existing)}):")
        for m in existing:
            print(f"  - {m}")

    # 5. Pull each model
    pulled = []
    for model in MODELS:
        name = model["name"]
        ollama_name = model["ollama_name"]

        # Check if already pulled
        if any(ollama_name.split(":")[0] in m for m in existing):
            print(f"[SKIP] {name} already exists")
            pulled.append(ollama_name)
            continue

        if pull_model(ollama_name):
            pulled.append(ollama_name)
        else:
            print(f"[WARN] Could not pull {name}")

    # 6. Test each pulled model
    print("\n" + "=" * 60)
    print("Model Verification")
    print("=" * 60)
    for ollama_name in pulled:
        test_model(ollama_name)

    print("\n" + "=" * 60)
    print("Done. Ollama server still running.")
    print(f"  URL: {OLLAMA_URL}")
    print(f"  Models: {pulled}")
    print("=" * 60)


if __name__ == "__main__":
    main()
