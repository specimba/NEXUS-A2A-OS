import os, sys

root = r'C:\Users\speci.000\Documents\NEXUS'
SKIP_RECURSE = {'node_modules', '.git', 'tests_tmp', '__pycache__', '.venv', '.venv_adversarial', 'venv', '.next', '.ruff_cache', '.pytest_cache'}

def dir_size(path, depth=0):
    total = 0
    count = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_RECURSE and depth == 0:
                        total += 0
                        count += 0
                        continue
                    s, c = dir_size(entry.path, depth+1)
                    total += s
                    count += c
                elif entry.is_file(follow_symlinks=False):
                    try:
                        total += entry.stat().st_size
                        count += 1
                    except:
                        pass
    except:
        pass
    return total, count

results = []
entries = list(os.scandir(root))
entries.sort(key=lambda e: e.name)
for entry in entries:
    if not entry.is_dir():
        continue
    sz, cnt = dir_size(entry.path)
    results.append((entry.name, round(sz/(1024*1024), 1), cnt))

results.sort(key=lambda x: x[1], reverse=True)
print(f"{'Directory':<45} {'Size MB':>10} {'Files':>8}")
print("-" * 65)
for name, sz, fc in results:
    print(f"{name:<45} {sz:>10.1f} {fc:>8}")
