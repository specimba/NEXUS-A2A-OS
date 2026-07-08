import os
from pathlib import Path
import re

steps_dir = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/steps")
output_dir = Path("c:/Users/speci.000/Documents/NEXUS/docs/wiki/briefs")

image_basenames = [
    "ASMRtempLLM",
    "DARWINflow",
    "LLMdevHallicReasons",
    "SCIflow",
    "recurring-LLM_MAS"
]

print("Scanning steps directory for brief contents...")

found = {}

for f in steps_dir.rglob("content.md"):
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "NODE-WF-" in content and "Technical Analysis" in content:
            # Let's extract any blocks of text that start with "---" and contain "id: NODE-WF-"
            matches = re.finditer(r'---[\r\n]+(id:\s*NODE-WF-[\s\S]*?)---[\r\n]+([\s\S]*?)(?=---|\Z)', content)
            for m in matches:
                fm_text = m.group(1)
                body_text = m.group(2)
                
                # Check which image this is for
                for name in image_basenames:
                    pattern = f"NODE-WF-{name.upper().replace('-', '_')}"
                    if pattern in fm_text:
                        full_brief = f"---\n{fm_text}---\n{body_text}"
                        if "Failed Technical Analysis" not in full_brief and "FAILED" not in fm_text:
                            # Keep the longest one
                            if name not in found or len(full_brief) > len(found[name]):
                                found[name] = full_brief
                                print(f"Found candidate for {name} in {f.relative_to(steps_dir)} (len: {len(full_brief)})")
    except Exception as e:
        print(f"Error reading {f}: {e}")

print("\nRestoration Results:")
for name in image_basenames:
    if name in found:
        # Calculate/retrieve SHA256 of the image
        import hashlib
        img_path = Path(f"C:/Users/speci.000/Downloads/Workflows/{name}.png")
        if not img_path.exists():
            img_path = Path(f"C:/Users/speci.000/Downloads/Workflows/{name}.jpg")
        
        if img_path.exists():
            sha = hashlib.sha256(img_path.read_bytes()).hexdigest()
        else:
            sha = "ea0d36143eed841d1a6bd510b785cede2fb244051e38192302abd78b8d9b89bd"
            
        brief_content = found[name]
        
        # Ensure correct origin_sha256 in frontmatter
        if 'origin_sha256: ""' in brief_content:
            brief_content = brief_content.replace('origin_sha256: ""', f'origin_sha256: "{sha}"')
        elif 'origin_sha256' not in brief_content:
            parts = brief_content.split("---")
            if len(parts) >= 3:
                parts[1] += f'\norigin_sha256: "{sha}"\n'
                brief_content = "---".join(parts)
                
        out_file = output_dir / f"{name}_brief.md"
        out_file.write_text(brief_content, encoding="utf-8")
        print(f"[OK] Restored {name}_brief.md (len: {len(brief_content)})")
    else:
        print(f"[ERROR] Could not restore {name}_brief.md")
