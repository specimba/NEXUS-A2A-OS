import os
import json
from pathlib import Path

brain_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain")
image_basenames = ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]

print("Scanning all transcripts for source_sha256 or source_sha...")

for conv_dir in brain_dir.iterdir():
    if conv_dir.is_dir():
        trans_file = conv_dir / ".system_generated/logs/transcript.jsonl"
        if trans_file.exists():
            print(f"Scanning {conv_dir.name}...")
            with open(trans_file, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if "source_sha" in line or "source_sha256" in line:
                        for name in image_basenames:
                            if name.lower() in line.lower():
                                print(f"  Line {line_num} contains '{name}' and 'source_sha'! len={len(line)}")
                                try:
                                    data = json.loads(line)
                                    # Recursive search
                                    def find_strings(val):
                                        res = []
                                        if isinstance(val, dict):
                                            for k, v in val.items():
                                                res.extend(find_strings(v))
                                        elif isinstance(val, list):
                                            for item in val:
                                                res.extend(find_strings(item))
                                        elif isinstance(val, str):
                                            if "source_sha" in val and "---" in val:
                                                res.append(val)
                                        return res
                                    
                                    candidates = find_strings(data)
                                    for c in candidates:
                                        cleaned = c.replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\t", "\t")
                                        if "Technical Analysis" in cleaned and "FAILED" not in cleaned:
                                            print(f"    -> Found brief candidate! len={len(cleaned)}")
                                            out_path = Path(f"c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs/{name}_brief.md")
                                            out_path.write_text(cleaned, encoding="utf-8")
                                            print(f"    [RESTORED] {name}_brief.md")
                                except Exception as e:
                                    print(f"    Parse error: {e}")
print("Scan done!")
