import os
from pathlib import Path

base_dir = Path("C:/Users/speci.000/Downloads/ARCHIVIST")
folders = ["doppelground_full_pack_v2", "twave_v3_scaffold_unpacked", "foundry_datasets", "1505", "DERDDRE", "GROKsharedfolderNEXUSproject-01"]

print("Searching ARCHIVIST subfolders...")
for f in folders:
    p = base_dir / f
    if p.exists():
        for path in p.rglob("*_brief.md"):
            print(f"Found: {path} (size: {path.stat().st_size} bytes)")
