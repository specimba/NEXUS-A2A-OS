import json
from pathlib import Path

analysis_path = Path("C:/Users/speci.000/Documents/NEXUS/experiments/gross/runs/20260527T074324Z-long-session-sandbox-default/analysis.json")
analysis = json.load(analysis_path.open(encoding="utf-8"))

unique_files = {}
for s in analysis["queue_snapshots"]:
    for r in s["queue"]["rows"]:
        # Get relative name of the file inside the snapshot directory
        path_obj = Path(r["path"])
        filename = path_obj.name
        unique_files[filename] = {
            "path": r["path"],
            "bytes": r["bytes"],
            "matched_markers": r["matched_markers"]
        }

print(f"Total unique files captured in queue: {len(unique_files)}")
print("\nFiles matching markers/canaries:")
for name, info in sorted(unique_files.items()):
    if info["matched_markers"]:
        print(f"  - {name} ({info['bytes']} bytes): {info['matched_markers']}")
        
        # Peek at contents
        try:
            p = Path(info["path"])
            text = p.read_text(encoding="utf-8", errors="ignore")[:400]
            print("    [PEEK]:", text.replace("\n", " ").strip()[:150])
        except Exception as e:
            print(f"    [ERR READ]: {e}")
