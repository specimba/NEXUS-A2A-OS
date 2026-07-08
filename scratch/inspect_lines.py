from pathlib import Path
import json

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")

lines_to_inspect = [20965]

for l in lines_to_inspect:
    print(f"\n=== Line {l} ===")
    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, 1):
            if idx == l:
                try:
                    data = json.loads(line)
                    print(f"Keys: {list(data.keys())}")
                    print(f"Type: {data.get('type')}")
                    print(f"Content length: {len(str(data.get('content')))}")
                    print(str(data.get('content'))[:1000])
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    print(line[:1000])
