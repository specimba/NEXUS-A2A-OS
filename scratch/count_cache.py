import json
import os

# CANARY: afccab75452225bb494eaf0fd8f6a00a
CACHE_PATH = "C:\\Users\\speci.000\\Documents\\NEXUS\\datasets\\ernie\\ollama_cache.json"

if not os.path.exists(CACHE_PATH):
    print("Cache not found.")
    exit(0)

with open(CACHE_PATH, "r", encoding="utf-8") as fh:
    cache = json.load(fh)

total = len(cache)
benign_ernie = 0
benign_safe = 0
benign_unsafe = 0
other_cats = {}

for k, v in cache.items():
    qtype = v.get("query_type", "")
    verdict = v.get("verdict", "")
    if qtype == "benign_ernie_corpus":
        benign_ernie += 1
        if verdict == "safe":
            benign_safe += 1
        elif verdict == "unsafe":
            benign_unsafe += 1
    else:
        other_cats[qtype] = other_cats.get(qtype, 0) + 1

print(f"Total cached items: {total}")
print(f"Benign ERNIE corpus queries: {benign_ernie}")
print(f"  - SAFE (True Negatives): {benign_safe}")
print(f"  - UNSAFE (False Positives): {benign_unsafe}")
print("\nOther categories in cache:")
for cat, count in sorted(other_cats.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cat}: {count}")
