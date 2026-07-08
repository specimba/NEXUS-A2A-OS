import os
from pathlib import Path
import json

brain_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain")
image_basenames = ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]

print("Scanning all transcripts with simple match...")
for conv_path in brain_dir.iterdir():
    if conv_path.is_dir():
        trans_file = conv_path / ".system_generated/logs/transcript.jsonl"
        if trans_file.exists():
            with open(trans_file, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    # We just look for "id: NODE-WF-ASMRTEMPLLM" or similar in the raw line
                    for name in image_basenames:
                        target = f"id: NODE-WF-{name.upper().replace('-', '_')}"
                        if target in line:
                            print(f"[{conv_path.name}] Line {line_num} contains '{target}' (len={len(line)})")
