#!/usr/bin/env python3
"""
ollama_model_recovery.py — Re-pull essential Ollama models after cleanup bug.

Starts Ollama server on Windows host from WSL, pulls all essential models,
and verifies each with a quick inference probe.

Usage:
    python3 scripts/ollama_model_recovery.py
    OLLAMA_HOST=172.26.240.1:11435 python3 scripts/ollama_model_recovery.py
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

OLLAMA_EXE = Path("/mnt/c/Users/speci.000/AppData/Local/Programs/Ollama/ollama.exe")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "127.0.0.1:11435")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = f"http://{OLLAMA_URL}"

# All essential models referenced across NEXUS codebase
ESSENTIAL_MODELS = [
    # Core Guard Plane models
    {"name": "special-virus",       "ollama_name": "special-virus",            "src": "custom"},
    {"name": "gemma3:1b",          "ollama_name": "gemma3:1b",               "src": "ollama_library"},
    {"name": "llama-guard3:1b",    "ollama_name": "llama-guard3:1b",         "src": "ollama_library"},
    {"name": "e-cameron",          "ollama_name": "e-cameron",               "src": "custom/hf"},
    {"name": "qwen2.5",            "ollama_name": "qwen2.5",                 "src": "ollama_library"},
    # Benchmark / RP models
    {"name": "Neo_T-Virus",        "ollama_name": "hf.co/mradermacher/Neo_T-Virus-3.2-1B-GGUF:latest", "src": "hf"},
    {"name": "Special-Virus",      "ollama_name": "hf.co/mradermacher/Special-Virus-3.2-1B-GGUF:latest", "src": "hf"},
    {"name": "LFM2.5-Instruct",    "ollama_name": "hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:latest", "src": "hf"},
    # Synthetic data / pool models
    {"name": "dolphin2.9",         "ollama_name": "dolphin2.9",              "src": "ollama_library"},
    {"name": "llama3.2",           "ollama_name": "llama3.2",                "src": "ollama_library"},
    {"name": "phi4",               "ollama_name": "phi4",                    "src": "ollama_library"},
    {"name": "mistral",            "ollama_name": "mistral",                 "src": "ollama_library"},
]


def run_ps(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    ps = ["powershell.exe", "-Command", cmd]
    proc = subprocess.run(ps, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def is_ollama_running() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama() -> subprocess.Popen | None:
    if is_ollama_running():
        print("[OK] Ollama already running")
        return None
    print("[INFO] Starting Ollama server...")
    env = os.environ.copy()
    env["OLLAMA_HOST"] = OLLAMA_URL.replace("http://", "")
    env["OLLAMA_ORIGINS"] = "*"
    proc = subprocess.Popen(
        [str(OLLAMA_EXE), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    return proc


def wait_for_ollama(max_wait: int = 60) -> bool:
    print("[INFO] Waiting for Ollama to be ready...")
    for i in range(max_wait):
        if is_ollama_running():
            print(f"[OK] Ollama ready after {i+1}s")
            return True
        time.sleep(1)
    print("[ERROR] Ollama did not become ready")
    return False


def list_models() -> list[str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[WARN] Failed to list models: {e}")
        return []


def pull_model(ollama_name: str) -> bool:
    print(f"[INFO] Pulling {ollama_name} ...")
    try:
        payload = json.dumps({"name": ollama_name}).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            for line in resp:
                try:
                    msg = json.loads(line.decode("utf-8"))
                    if msg.get("status") == "success":
                        print(f"  [OK] Pulled {ollama_name}")
                        return True
                    elif "completed" in msg and "total" in msg:
                        pct = msg["completed"] / msg["total"] * 100
                        print(f"\r  [PROGRESS] {pct:.1f}%", end="", flush=True)
                except Exception:
                    pass
            print()
            return True
    except Exception as e:
        print(f"  [ERROR] Failed to pull {ollama_name}: {e}")
        return False


def probe_model(model_name: str) -> bool:
    print(f"[INFO] Probing {model_name} ...")
    try:
        payload = json.dumps({
            "model": model_name,
            "prompt": "Say exactly: OK\n",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 5},
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
            print(f"  [OK] Response: '{response[:40]}'")
            return True
    except Exception as e:
        print(f"  [FAIL] Probe failed: {e}")
        return False


def main():
    print("=" * 60)
    print("NEXUS Ollama Model Recovery")
    print("=" * 60)

    if not OLLAMA_EXE.exists():
        print(f"[FATAL] Ollama not found at {OLLAMA_EXE}")
        sys.exit(1)

    # Start Ollama if not running
    proc = start_ollama()
    if not wait_for_ollama(max_wait=60):
        print("[FATAL] Ollama failed to start")
        sys.exit(1)

    existing = list_models()
    print(f"[INFO] Existing models: {len(existing)}")
    for m in existing:
        print(f"  - {m}")

    # Pull missing models
    pulled = []
    skipped = []
    failed = []
    for model in ESSENTIAL_MODELS:
        name = model["name"]
        ollama_name = model["ollama_name"]
        # Check if already present (match base name before any tag)
        base = ollama_name.split(":")[0]
        if any(base in em for em in existing):
            print(f"[SKIP] {name} already present")
            skipped.append(name)
            continue
        if pull_model(ollama_name):
            pulled.append(name)
        else:
            failed.append(name)

    # Verify all
    print("\n" + "=" * 60)
    print("Model Verification")
    print("=" * 60)
    all_models = existing + pulled
    verified = []
    for model in ESSENTIAL_MODELS:
        name = model["name"]
        ollama_name = model["ollama_name"]
        if probe_model(ollama_name):
            verified.append(name)

    print("\n" + "=" * 60)
    print("Recovery Summary")
    print("=" * 60)
    print(f"  Skipped (already present): {len(skipped)} — {skipped}")
    print(f"  Pulled:                   {len(pulled)} — {pulled}")
    print(f"  Failed:                   {len(failed)} — {failed}")
    print(f"  Verified (inference OK):  {len(verified)} — {verified}")
    print(f"  Ollama URL:               {OLLAMA_URL}")
    print("=" * 60)

    if failed:
        print("\n[WARN] Some models failed to pull. Common fixes:")
        print("  1. Ensure Windows has internet access")
        print("  2. For hf.co models: ensure huggingface-cli is authenticated")
        print("  3. For custom models: re-run create_ollama_models.py after base pulls")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
