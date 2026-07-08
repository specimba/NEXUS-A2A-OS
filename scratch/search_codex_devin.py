import os
from pathlib import Path

folders = [
    Path("C:/Users/speci.000/Documents/Codex"),
    Path("C:/Users/speci.000/Documents/DEVIN"),
    Path("C:/Users/speci.000/Documents/NEO"),
    Path("C:/Users/speci.000/Documents/NEO agent"),
    Path("C:/Users/speci.000/Documents/_tmp_AgentsofAgent_v1")
]

print("Searching other agent folders...")
for folder in folders:
    if folder.exists():
        for p in folder.rglob("*_brief.md"):
            print(f"Found: {p} (size: {p.stat().st_size} bytes)")
