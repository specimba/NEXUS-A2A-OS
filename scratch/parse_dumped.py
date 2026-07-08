import re
import json

with open("scratch/dumped_lines.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for blocks of text starting with "---" and id: NODE-WF
# We'll search for anything that looks like a markdown frontmatter and body
matches = re.finditer(r'---\\n(id:\s*NODE-WF-[\s\S]*?)\\n---\\n([\s\S]*?)(?=\\n---\\n|\\n"|\n===|\Z)', content)

for idx, match in enumerate(matches, 1):
    frontmatter = match.group(1).replace("\\n", "\n").replace('\\"', '"')
    body = match.group(2).replace("\\n", "\n").replace('\\"', '"')
    print(f"Match {idx}:")
    print(frontmatter[:200])
    print("-" * 40)
    
    # Extract file name or id
    id_match = re.search(r'id:\s*(\S+)', frontmatter)
    if id_match:
        node_id = id_match.group(1).strip()
        filename = f"{node_id.replace('NODE-WF-', '').replace('_FAILED', '')}_brief.md"
        # Check if this looks like a valid brief (contains # Technical Analysis)
        if "Failed Technical Analysis" not in body and "Failed Technical Brief" not in frontmatter:
            out_content = f"---\n{frontmatter}\n---\n\n{body}"
            # Ensure origin_sha256 is present, if not add a placeholder
            if "origin_sha256" not in out_content:
                # Add origin_sha256 to frontmatter
                lines = frontmatter.splitlines()
                lines.insert(-1, 'origin_sha256: "placeholder"')
                frontmatter_new = "\n".join(lines)
                out_content = f"---\n{frontmatter_new}\n---\n\n{body}"
            
            with open(f"docs/wiki/briefs/{filename}", "w", encoding="utf-8") as out_f:
                out_f.write(out_content)
            print(f"Restored to docs/wiki/briefs/{filename}")
