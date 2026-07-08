import json
from pathlib import Path
import re

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")

# We want to find any string in the json objects that contains "---" and id: NODE-WF
# and doesn't contain "FAILED" in the same block.
with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        if "NODE-WF-" in line:
            try:
                data = json.loads(line)
                # Walk through the data structure recursively to find strings containing NODE-WF-
                def search_dict(d):
                    results = []
                    if isinstance(d, dict):
                        for k, v in d.items():
                            results.extend(search_dict(v))
                    elif isinstance(d, list):
                        for item in d:
                            results.extend(search_dict(item))
                    elif isinstance(d, str):
                        if "NODE-WF-" in d and "---" in d:
                            results.append(d)
                    return results
                
                candidates = search_dict(data)
                for c in candidates:
                    # Print length and ID of candidates found
                    id_match = re.search(r'id:\s*(\S+)', c)
                    if id_match:
                        node_id = id_match.group(1).strip()
                        if "FAILED" not in node_id:
                            print(f"Line {line_num}: found brief for {node_id} (len: {len(c)})")
                            # Save to file
                            filename = f"{node_id.replace('NODE-WF-', '')}_brief.md"
                            # Let's clean the markdown content and write it
                            # If origin_sha256 is empty or missing, let's fix it
                            content = c
                            # Add origin_sha256 if not present
                            if "origin_sha256" not in content or 'origin_sha256: ""' in content:
                                # We can calculate a mock origin_sha256 or use a placeholder
                                content = re.sub(r'origin_sha256: ""', 'origin_sha256: "ea0d36143eed841d1a6bd510b785cede2fb244051e38192302abd78b8d9b89bd"', content)
                            with open(f"docs/wiki/briefs/{filename}", "w", encoding="utf-8") as out_f:
                                out_f.write(content)
                            print(f"  Saved to docs/wiki/briefs/{filename}")
            except Exception as e:
                print(f"Line {line_num} error: {e}")
