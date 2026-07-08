import os
from pathlib import Path

dg_dir = Path("C:/Users/speci.000/Documents/DoppelGround")
print("Searching DoppelGround...")
if dg_dir.exists():
    for p in dg_dir.rglob("*_brief.md"):
        print(f"Found: {p} (size: {p.stat().st_size} bytes)")
else:
    print("DoppelGround folder does not exist")
