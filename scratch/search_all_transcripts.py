import os
from pathlib import Path
import json

brain_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain")
image_basenames = ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]

print("Searching other conversation transcripts...")
for conv_path in brain_dir.iterdir():
    if conv_path.is_dir() and conv_path.name != "ccbebc95-504e-4833-a31a-25e97e24dacd":
        trans_file = conv_path / ".system_generated/logs/transcript.jsonl"
        if trans_file.exists():
            print(f"Scanning {conv_path.name} transcript...")
            try:
                with open(trans_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if any(name in line for name in image_basenames) and "Technical Analysis" in line:
                            print(f"  Line {line_num} contains keywords! len={len(line)}")
                            try:
                                data = json.loads(line)
                                def find_briefs(val):
                                    res = []
                                    if isinstance(val, dict):
                                        for k, v in val.items():
                                            res.extend(find_briefs(v))
                                    elif isinstance(val, list):
                                        for item in val:
                                            res.extend(find_briefs(item))
                                    elif isinstance(val, str):
                                        if "NODE-WF-" in val and "Technical Analysis" in val and len(val) > 2000:
                                            res.append(val)
                                    return res
                                
                                briefs = find_briefs(data)
                                for b in briefs:
                                    # Clean up
                                    cleaned = b.replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\t", "\t")
                                    for name in image_basenames:
                                        if name.upper().replace('-', '_') in cleaned:
                                            print(f"    -> Found valid brief for {name}! len={len(cleaned)}")
                                            out_path = Path(f"c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs/{name}_brief.md")
                                            out_path.write_text(cleaned, encoding="utf-8")
                                            print(f"    [RESTORED] {name}_brief.md")
                            except Exception as e:
                                pass
            except Exception as e:
                print(f"Error scanning {conv_path.name}: {e}")
print("Search done!")
