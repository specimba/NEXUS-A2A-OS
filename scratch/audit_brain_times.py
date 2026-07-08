import os
from pathlib import Path
import time

brain_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain")
for d in brain_dir.iterdir():
    if d.is_dir():
        print(f"Directory: {d.name} (Modified: {time.ctime(d.stat().st_mtime)})")

