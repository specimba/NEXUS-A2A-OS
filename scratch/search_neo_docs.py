import os
from pathlib import Path

neo_dir = Path("C:/Users/speci.000/Documents/NEO agent")
print("Searching NEO agent for briefs...")
if neo_dir.exists():
    for p in neo_dir.rglob("*_brief.md"):
        print(f"Found: {p} (size: {p.stat().st_size} bytes)")
    
    # Check specifically for ASMRtempLLM or any briefs under docs
    for p in neo_dir.rglob("*"):
        if p.is_file() and any(name.lower() in p.name.lower() for name in ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]):
            print(f"Found keyword file: {p} (size: {p.stat().st_size} bytes)")
else:
    print("NEO agent folder does not exist")
