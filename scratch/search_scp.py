import sys
import re

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\speci.000\Downloads\ARCHIVIST\SAKANAaiDISCOVERYinternANDothernewthings2206.txt"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print("Searching for SCP...")
for idx, line in enumerate(lines):
    if "scp" in line.lower() or "science context" in line.lower():
        print(f"L{idx+1}: {line.strip()}")
