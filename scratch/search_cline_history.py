import os
from pathlib import Path

appdata = Path(os.environ.get("APPDATA", "C:/Users/speci.000/AppData/Roaming"))
print(f"Scanning APPDATA: {appdata}...")

# Look for history folders
history_dirs = []
for p in appdata.rglob("history"):
    if "globalStorage" in p.as_posix() or "cline" in p.as_posix() or "claude-dev" in p.as_posix():
        history_dirs.append(p)
        print(f"Found history dir: {p}")

# Search for briefs inside history files
image_basenames = ["ASMRtempLLM", "DARWINflow", "LLMdevHallicReasons", "SCIflow", "recurring-LLM_MAS"]

for hd in history_dirs:
    print(f"Scanning files in {hd}...")
    for f in hd.rglob("*"):
        if f.is_file():
            try:
                # Read file
                content = f.read_text(encoding="utf-8", errors="ignore")
                for name in image_basenames:
                    target = f"NODE-WF-{name.upper().replace('-', '_')}"
                    if target in content and "Technical Analysis" in content:
                        print(f"FOUND brief for {name} in {f}!")
                        # Save the content to see
                        # (We will do manual extraction later if found)
            except Exception as e:
                pass
print("Done scanning history!")
