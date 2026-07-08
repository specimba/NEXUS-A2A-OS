import os
import re
from pathlib import Path

archivist_dir = Path("C:/Users/speci.000/Downloads/ARCHIVIST")
image_names = [
    "ASMRtempLLM",
    "DARWINflow",
    "HERMESnewSTORE",
    "LLMdevHallicReasons",
    "SCIflow",
    "Visual ID workflow",
    "llm_data_preparation_survey_overview",
    "recurring-LLM_MAS"
]

results = {}

for f in archivist_dir.rglob("*"):
    if f.is_file() and f.suffix in (".md", ".txt", ".json", ".py", ".yaml", ".yml"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for name in image_names:
                if name.lower() in content.lower():
                    # Find matching lines
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if name.lower() in line.lower():
                            if name not in results:
                                results[name] = []
                            results[name].append((f.name, i, line.strip()))
        except Exception as e:
            pass

for name, matches in results.items():
    print(f"\n=== Mentions of {name} ({len(matches)} matches) ===")
    # Print first 10 matches
    for filename, line_num, text in matches[:10]:
        print(f"  {filename}:{line_num} -> {text[:150]}")
