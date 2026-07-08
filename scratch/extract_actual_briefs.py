import json
from pathlib import Path
import re

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")

# Target image names
image_basenames = [
    "ASMRtempLLM",
    "DARWINflow",
    "LLMdevHallicReasons",
    "SCIflow",
    "recurring-LLM_MAS"
]

print("Scanning for actual generated text in log file...")
with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        # Quick filter
        if any(name in line for name in image_basenames) and "Technical Analysis" in line:
            # Let's see if this is a large chunk of text
            print(f"Line {line_num}: len={len(line)}")
            # Try to see if there is a match for the brief structure
            # A brief will contain the frontmatter and a lot of markdown
            try:
                data = json.loads(line)
                
                # Recursive search for markdown briefs
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
                    cleaned = b.replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\t", "\t")
                    # Check if it has the required fields
                    for name in image_basenames:
                        if name.upper().replace('-', '_') in cleaned:
                            print(f"  -> Found valid brief for {name}! len={len(cleaned)}")
                            # Let's save it to a file
                            out_path = Path(f"c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs/{name}_brief.md")
                            out_path.write_text(cleaned, encoding="utf-8")
                            print(f"  [SAVED] {name}_brief.md")
            except Exception as e:
                print(f"  Line {line_num} parse error: {e}")
