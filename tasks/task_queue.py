#!/usr/bin/env python3
"""NEXUS OS Task Queue — CLI for agents.

Usage:
    python tasks/task_queue.py create <id> <title> <owner> [priority]
    python tasks/task_queue.py claim <id> <agent>
    python tasks/task_queue.py update <id> <progress> [note]
    python tasks/task_queue.py complete <id> [note]
    python tasks/task_queue.py list [pending|in-progress|done]
    python tasks/task_queue.py report <id>
"""
import sys, json, os
from pathlib import Path
from datetime import datetime

BASE = Path("tasks")
PENDING = BASE / "pending"
INPROG  = BASE / "in-progress"
DONE    = BASE / "done"

for d in [PENDING, INPROG, DONE]:
    d.mkdir(parents=True, exist_ok=True)

def read_task(tid, folder):
    p = folder / f"{tid}.json"
    return json.loads(p.read_text()) if p.exists() else None

def write_task(tid, folder, data):
    (folder / f"{tid}.json").write_text(json.dumps(data, indent=2))

def now():
    return datetime.now().isoformat()

cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

if cmd == "create":
    tid, title, owner = sys.argv[2], sys.argv[3], sys.argv[4]
    pri = sys.argv[5] if len(sys.argv) > 5 else "medium"
    data = {"id": tid, "title": title, "owner": owner, "priority": pri,
            "status": "pending", "created": now(), "updated": now(), "progress": 0}
    write_task(tid, PENDING, data)
    print(f"✅ Created: {tid} → {owner}")

elif cmd == "claim":
    tid, agent = sys.argv[2], sys.argv[3]
    data = read_task(tid, PENDING)
    if not data:
        print(f"❌ {tid} not found in pending"); sys.exit(1)
    data["status"] = "in-progress"; data["owner"] = agent; data["updated"] = now()
    write_task(tid, INPROG, data)
    (PENDING / f"{tid}.json").unlink()
    print(f"🚀 Claimed: {tid} by {agent}")

elif cmd == "update":
    tid, prog = sys.argv[2], int(sys.argv[3])
    note = sys.argv[4] if len(sys.argv) > 4 else ""
    for folder in [INPROG, PENDING]:
        data = read_task(tid, folder)
        if data:
            data["progress"] = prog; data["updated"] = now()
            if note: data["last_note"] = note
            write_task(tid, folder, data)
            print(f"📈 {tid} → {prog}%{f' | {note}' if note else ''}")
            sys.exit(0)
    print(f"❌ {tid} not found"); sys.exit(1)

elif cmd == "complete":
    tid = sys.argv[2]
    note = sys.argv[3] if len(sys.argv) > 3 else ""
    data = read_task(tid, INPROG)
    if not data:
        print(f"❌ {tid} not in progress"); sys.exit(1)
    data["status"] = "done"; data["completed"] = now(); data["updated"] = now()
    if note: data["final_note"] = note
    write_task(tid, DONE, data)
    (INPROG / f"{tid}.json").unlink()
    print(f"✅ Completed: {tid}")

elif cmd == "list":
    state = sys.argv[2] if len(sys.argv) > 2 else "pending"
    folder = {"pending": PENDING, "in-progress": INPROG, "done": DONE}.get(state, PENDING)
    tasks = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not tasks:
        print(f"No {state} tasks."); sys.exit(0)
    for p in tasks:
        d = json.loads(p.read_text())
        bar = "█" * (d["progress"] // 10) + "░" * (10 - d["progress"] // 10)
        print(f"[{d['priority']:8}] {d['id']} | {d['owner']:15} | {bar} {d['progress']}% | {d['title']}")

elif cmd == "report":
    tid = sys.argv[2]
    for folder in [PENDING, INPROG, DONE]:
        data = read_task(tid, folder)
        if data:
            print(json.dumps(data, indent=2)); sys.exit(0)
    print(f"❌ {tid} not found")

else:
    print(__doc__)