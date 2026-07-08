import json
import os
import hashlib

# CANARY: 60f859d037bdb37730ef8af224fdcbea
ERNIE_DIR = "C:\\Users\\speci.000\\Documents\\NEXUS\\datasets\\ernie"
CACHE_PATH = os.path.join(ERNIE_DIR, "ollama_cache.json")
BENIGN_PATH = os.path.join(ERNIE_DIR, "benign_corpus_100.jsonl")

if not os.path.exists(CACHE_PATH):
    print("Cache not found.")
    exit(1)

with open(CACHE_PATH, "r", encoding="utf-8") as fh:
    cache = json.load(fh)

benign_prompts = []
if os.path.exists(BENIGN_PATH):
    with open(BENIGN_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                p = rec.get("prompt", "") or rec.get("text") or rec.get("input") or ""
                if p:
                    benign_prompts.append(p)

print(f"Loaded {len(benign_prompts)} benign prompts.")
print("\nFalse Positives (Benign queries marked UNSAFE):")
count = 0
for prompt in benign_prompts:
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if h in cache:
        res = cache[h]
        if res.get('verdict') == 'unsafe':
            print(f"\n[{count+1}] Prompt: {repr(prompt[:120])}...")
            print(f"  Predicted query_type: {res.get('query_type')}")
            print(f"  Confidence: {res.get('confidence')}")
            print(f"  Model used: {res.get('model_used')}")
            print(f"  Prompt used: {res.get('prompt_used')}")
            print(f"  Raw response: {res.get('raw_response')}")
            count += 1

print(f"\nTotal False Positives: {count}")
