import re
import sys

# Reconfigure stdout to use UTF-8 on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

files_to_search = [
    r"C:\Users\speci.000\Downloads\ARCHIVIST\SAKANAaiDISCOVERYinternANDothernewthings2206.txt",
    r"C:\Users\speci.000\Downloads\ARCHIVIST\2006fancyMODELSandNewPaPeRs.txt",
    r"C:\Users\speci.000\Documents\NEXUS\01_PROJECT_STATE.md"
]

patterns = [
    r"(?i)coger",
    r"(?i)elastic.*reasoning",
    r"(?i)tandem",
    r"(?i)progent",
    r"(?i)flipped.*triple",
    r"(?i)fugu"
]

for file_path in files_to_search:
    print(f"=== Searching in {file_path} ===")
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines):
            matched = False
            for pattern in patterns:
                if re.search(pattern, line):
                    matched = True
            if matched:
                print(f"L{idx+1}: {line.strip()}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
