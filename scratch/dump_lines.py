import json
from pathlib import Path

transcript_path = Path("C:/Users/speci.000/.gemini/antigravity/brain/ccbebc95-504e-4833-a31a-25e97e24dacd/.system_generated/logs/transcript.jsonl")
output_path = Path("c:/Users/speci.000/Documents/NEXUS/scratch/dumped_lines.txt")

lines_to_dump = list(range(20290, 20830))
dumped = []

with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        if line_num in lines_to_dump:
            dumped.append(f"=== Line {line_num} (len: {len(line)}) ===\n{line}\n")

output_path.write_text("\n".join(dumped), encoding="utf-8")
print(f"Dumped lines to {output_path}")
