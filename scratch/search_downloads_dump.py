import os
from pathlib import Path

dump_dir = Path("C:/Users/speci.000/Downloads/DOWNLOADSDUMP")
print("Searching DOWNLOADSDUMP...")
if dump_dir.exists():
    for p in dump_dir.rglob("*_brief.md"):
        print(f"Found: {p} (size: {p.stat().st_size} bytes)")
    for p in dump_dir.rglob("*"):
        if p.is_file() and any(name.lower() in p.name.lower() for name in ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]):
            print(f"Found keyword file: {p} (size: {p.stat().st_size} bytes)")
else:
    print("DOWNLOADSDUMP folder does not exist")
