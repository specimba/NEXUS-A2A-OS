with open('nexus_os/security/meta_attack_detector.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where a function ends by looking for dedents to 8 spaces or less after line 714
for i, line in enumerate(lines[713:1137], start=714):
    if not line.strip() or line.strip().startswith('#'):
        continue
    indent = len(line) - len(line.lstrip())
    if indent <= 8:
        print(f"Line {i:4d} (indent={indent}): {line.strip()[:80]}")
