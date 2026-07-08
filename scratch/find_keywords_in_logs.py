import os
from pathlib import Path

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")

keywords = [
    "ASMRtempLLM",
    "DARWINflow",
    "LLMdevHallicReasons",
    "SCIflow",
    "recurring-LLM_MAS"
]

print("Scanning for raw occurrences...")
with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        for kw in keywords:
            if kw in line:
                print(f"Line {line_num} contains '{kw}' (len: {len(line)})")
