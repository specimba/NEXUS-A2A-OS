"""Quick syntax/import check for key modules."""

import py_compile
import sys

files = [
    "nexus_os/bridge/server.py",
    "nexus_os/bridge/cloudflare_bypass.py",
    "nexus_os/mcp/server.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK  {f}")
    except py_compile.PyCompileError as e:
        print(f"ERR {f}: {e}")
        errors.append((f, str(e)))

if errors:
    sys.exit(1)
print("\nAll files compile successfully.")
