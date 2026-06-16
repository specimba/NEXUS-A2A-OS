#!/bin/sh
set -e

echo "=== NEXUS Sterile Lab Container ==="
echo "PID: $$"
echo "User: $(whoami)"
echo "Host: $(hostname)"
echo ""

# Validate isolation
echo "--- Isolation Checks ---"

# Check we can't see host processes
if [ -f /proc/1/cmdline ]; then
    CMD1=$(cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' || echo "UNREADABLE")
    echo "[CHECK] PID 1: $CMD1"
    if echo "$CMD1" | grep -qi "docker\|containerd\|systemd\|init"; then
        echo "  -> OK: Process space isolated"
    fi
fi

# Check no capabilities
if command -v capsh >/dev/null 2>&1; then
    echo "[CHECK] Capabilities: $(capsh --print 2>/dev/null | grep Current || echo 'capsh unavailable')"
fi

# Check network isolation
if command -v curl >/dev/null 2>&1; then
    echo "[WARN] curl is present - isolation may be compromised"
else
    echo "[CHECK] curl: ABSENT (good)"
fi
if command -v wget >/dev/null 2>&1; then
    echo "[WARN] wget is present - isolation may be compromised"
else
    echo "[CHECK] wget: ABSENT (good)"
fi
if command -v nc >/dev/null 2>&1; then
    echo "[WARN] netcat is present - isolation may be compromised"
else
    echo "[CHECK] netcat: ABSENT (good)"
fi
if command -v gcc >/dev/null 2>&1; then
    echo "[WARN] gcc is present - isolation may be compromised"
else
    echo "[CHECK] gcc: ABSENT (good)"
fi
if command -v python3 >/dev/null 2>&1; then
    echo "[CHECK] python3: $(python3 --version 2>&1)"
fi

# Check filesystem isolation
echo ""
echo "--- Filesystem ---"
echo "Read-only mount: /nexus/scripts"
echo "Writable mount:  /nexus/output"
echo "Input data:      /nexus/input"
echo ""

ls -la /nexus/ 2>/dev/null

# Check Ollama reachability
echo ""
echo "--- Ollama API Check ---"
for port in 11434 11435; do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://host.docker.internal:$port/api/tags', timeout=3)" 2>/dev/null; then
        echo "[OK] Ollama reachable at host.docker.internal:$port"
        break
    else
        echo "[INFO] No Ollama at host.docker.internal:$port"
    fi
done

echo ""
echo "=== Container ready ==="
echo ""

# Execute the command passed to the container
exec "$@"
