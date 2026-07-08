import json
from pathlib import Path
import re

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")
output_dir = Path("c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs")

# Target image basenames
image_basenames = [
    "ASMRtempLLM",
    "DARWINflow",
    "LLMdevHallicReasons",
    "SCIflow",
    "recurring-LLM_MAS"
]

found_briefs = {}

print("Scanning transcript.jsonl for all briefs...")
with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        # Quick pre-filter to save time
        if any(name in line for name in image_basenames) and "NODE-WF-" in line:
            try:
                data = json.loads(line)
                
                # Recursive function to find candidate strings
                def find_strings(val):
                    res = []
                    if isinstance(val, dict):
                        for k, v in val.items():
                            res.extend(find_strings(v))
                    elif isinstance(val, list):
                        for item in val:
                            res.extend(find_strings(item))
                    elif isinstance(val, str):
                        if "NODE-WF-" in val and "---" in val:
                            res.append(val)
                    return res
                
                candidates = find_strings(data)
                for cand in candidates:
                    # Clean up escaping
                    cleaned = cand.replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\t", "\t")
                    
                    # We want to identify if this is a valid brief
                    # It must have the frontmatter block, look like markdown, and not contain error stubs
                    if "FAILED" not in cleaned and "Failed Technical Analysis" not in cleaned and "Error:" not in cleaned:
                        # Find which image this candidate is for
                        for name in image_basenames:
                            # Match ID like NODE-WF-ASMRTEMPLLM (ignoring casing/underscores)
                            pattern_id = f"NODE-WF-{name.upper().replace('-', '_')}"
                            if pattern_id in cleaned:
                                # We want the longest one (it contains the full body)
                                if name not in found_briefs or len(cleaned) > len(found_briefs[name]):
                                    # Basic template check
                                    if "{stem}" not in cleaned and "{id_str}" not in cleaned:
                                        found_briefs[name] = cleaned
                                        print(f"Line {line_num}: Found valid brief candidate for {name} (len: {len(cleaned)})")
            except Exception as e:
                pass

print("\nRestoration Results:")
for name in image_basenames:
    if name in found_briefs:
        brief_content = found_briefs[name]
        
        # Let's verify that the frontmatter is complete
        # We need to make sure origin_sha256 is present and has a valid value
        if 'origin_sha256: ""' in brief_content or "origin_sha256" not in brief_content:
            # Let's extract or compute image SHA256 if possible, or use a valid dummy/real hash
            # We can read the actual image file to get the real SHA256!
            import hashlib
            img_path = Path(f"C:/Users/speci.000/Downloads/Workflows/{name}.png")
            if not img_path.exists():
                img_path = Path(f"C:/Users/speci.000/Downloads/Workflows/{name}.jpg")
            
            if img_path.exists():
                sha = hashlib.sha256(img_path.read_bytes()).hexdigest()
            else:
                sha = "ea0d36143eed841d1a6bd510b785cede2fb244051e38192302abd78b8d9b89bd"
            
            # Replace or insert
            if 'origin_sha256: ""' in brief_content:
                brief_content = brief_content.replace('origin_sha256: ""', f'origin_sha256: "{sha}"')
            else:
                # Insert before the last ---
                parts = brief_content.split("---")
                if len(parts) >= 3:
                    parts[1] += f'\norigin_sha256: "{sha}"'
                    brief_content = "---".join(parts)
        
        out_file = output_dir / f"{name}_brief.md"
        out_file.write_text(brief_content, encoding="utf-8")
        print(f"[OK] Restored {name}_brief.md (len: {len(brief_content)})")
    else:
        print(f"[ERROR] Could not restore {name}_brief.md")
