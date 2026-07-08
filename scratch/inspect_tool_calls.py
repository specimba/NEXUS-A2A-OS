import json
from pathlib import Path

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")

with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if idx == 20965:
            data = json.loads(line)
            print("Tool calls keys/details:")
            tcs = data.get("tool_calls", [])
            for tc in tcs:
                print(f"  Name: {tc.get('name')}")
                args = tc.get("args", {})
                print(f"  Args keys: {list(args.keys())}")
                # Print first 200 chars of CodeContent or ReplacementContent or targetContent
                for k, v in args.items():
                    print(f"    {k}: {str(v)[:200]}...")
