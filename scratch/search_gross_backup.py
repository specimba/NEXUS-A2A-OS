import os
from pathlib import Path

backup_dir = Path("C:/Users/speci.000/Documents/NEXUS_gross_backup")
print("Searching NEXUS_gross_backup...")
if backup_dir.exists():
    for p in backup_dir.rglob("*_brief.md"):
        print(f"Found: {p} (size: {p.stat().st_size} bytes)")
else:
    print("NEXUS_gross_backup does not exist")
