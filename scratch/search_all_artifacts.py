import os
from pathlib import Path

brain_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain")
print("Searching for brief files in all conversation folders...")

for conv_dir in brain_dir.iterdir():
    if conv_dir.is_dir():
        # Check in the root of the conversation and in any artifacts/scratch subfolders
        for p in conv_dir.rglob("*.md"):
            if "brief" in p.name.lower() or any(img_name.lower() in p.name.lower() for img_name in ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]):
                print(f"Found: {p} (size: {p.stat().st_size} bytes)")
