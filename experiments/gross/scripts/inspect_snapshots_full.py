import json
from pathlib import Path

analysis_path = Path("C:/Users/speci.000/Documents/NEXUS/experiments/gross/runs/20260527T074324Z-long-session-sandbox-default/analysis.json")
analysis = json.load(analysis_path.open(encoding="utf-8"))

unique_files = {}
for s in analysis["queue_snapshots"]:
    for r in s["queue"]["rows"]:
        path_obj = Path(r["path"])
        filename = path_obj.name
        unique_files[filename] = {
            "path": r["path"],
            "bytes": r["bytes"],
            "matched_markers": r["matched_markers"]
        }

print("=== DETAILED CODENAME & CONTENT MAPPING IN UPLOAD QUEUE ===")
for name in sorted(unique_files.keys()):
    info = unique_files[name]
    print(f"\n* File: {name} ({info['bytes']} bytes)")
    if info["matched_markers"]:
        print(f"  Matched markers: {info['matched_markers']}")
    try:
        p = Path(info["path"])
        content = p.read_text(encoding="utf-8", errors="ignore")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        print(f"  First 3 lines of content:")
        for line in lines[:3]:
            print(f"    {line[:120]}")
    except Exception as e:
        print(f"  [ERR READ]: {e}")
