import os
import re

directories = [
    r"C:\Users\speci.000\Downloads\NEXUSlogs",
    r"C:\Users\speci.000\Downloads\ARCHIVIST"
]

patterns = [
    r"\bfw_[a-zA-Z0-9]{22,40}\b", # Fireworks keys
    r"\bsk-or-v1-[a-fA-F0-9]{64}\b", # OpenRouter keys
    r"\bnvapi-[a-zA-Z0-9_-]{64,80}\b", # Nvidia keys
    r"\bcfat_[a-zA-Z0-9]{32,64}\b", # Cloudflare keys
    r"\bsk-[a-zA-Z0-9]{32,64}\b" # General sk- keys
]

compiled = [re.compile(p) for p in patterns]

found_keys = set()

for d in directories:
    if not os.path.exists(d):
        continue
    for root, dirs, files in os.walk(d):
        for file in files:
            if not file.endswith(".txt") and not file.endswith(".md") and not file.endswith(".json") and not file.endswith(".log"):
                continue
            fp = os.path.join(root, file)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for p in compiled:
                    for match in p.finditer(content):
                        found_keys.add(match.group(0))
            except Exception:
                pass

print(f"Total keys found: {len(found_keys)}")
for k in sorted(found_keys):
    masked = k[:6] + "..." + k[-4:] if len(k) > 10 else k
    print(f" - Found key: {masked} (length: {len(k)})")
    
# Write them to a temporary file in scratch so we can inspect/test them if needed
scratch_file = r"C:\Users\speci.000\.gemini\antigravity\brain\ca898454-93f5-4a06-8ed4-8442532aee22\scratch\keys_found.txt"
with open(scratch_file, "w", encoding="utf-8") as sf:
    for k in sorted(found_keys):
        sf.write(k + "\n")
