import os
from pathlib import Path

docs_dir = Path("C:/Users/speci.000/Documents")

print("Searching recursively for *_brief.md under C:/Users/speci.000/Documents...")
for p in docs_dir.rglob("*_brief.md"):
    # Skip the active workspace to find if they exist elsewhere
    if "Documents/NEXUS/" not in p.as_posix():
        print(f"Found: {p} (size: {p.stat().st_size} bytes)")
