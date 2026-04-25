#!/usr/bin/env python3
"""
NEXUS Task Queue — CLI for task assignment and ledger reconciliation.
Usage:
  python tasks/task_queue.py list [pending|in-progress|done|failed]
  python tasks/task_queue.py claim <task-id>
  python tasks/task_queue.py done <task-id>
  python tasks/task_queue.py reconcile  # fix folder vs JSON drift
  python tasks/task_queue.py stats
"""
import json, sys, time
from pathlib import Path

ROOT   = Path(__file__).parent.parent
TASKS  = ROOT / "tasks"
QUEUE  = TASKS / "queue.json"
FIELDS = ["id", "title", "owner", "priority", "status", "created", "updated"]

def load_queue():
    if QUEUE.exists():
        return json.loads(QUEUE.read_text())
    return []

def save_queue(q):
    QUEUE.write_text(json.dumps(q, indent=2))

def task_files(status):
    dir_map = {"pending": TASKS/"pending", "in-progress": TASKS/"in-progress",
              "done": TASKS/"done", "failed": TASKS/"failed"}
    d = dir_map.get(status, TASKS/"pending")
    return sorted(d.glob("TASK-*.json"), key=lambda p: p.name)

def reconcile():
    """Fix folder vs JSON status drift."""
    results = []
    for status, key in [("pending", "pending"), ("in-progress", "in-progress"),
                         ("done", "completed"), ("failed", "failed")]:
        for f in task_files(status):
            try:
                data = json.loads(f.read_text())
                s = data.get("status", "unknown")
                if s != key:
                    results.append(f"DRIFT: {f.name} folder={status} json={s} → fixed")
                    data["status"] = key
                    f.write_text(json.dumps(data, indent=2))
            except Exception as e:
                results.append(f"ERROR: {f.name} → {e}")
    if not results:
        results.append("No drift detected.")
    return results

def list_tasks(filter_status=None):
    q = load_queue()
    if filter_status:
        q = [t for t in q if t.get("status") == filter_status]
    if not q:
        print("No tasks found.")
        return
    print(f"\n{'ID':<12} {'PRIORITY':<8} {'OWNER':<15} {'STATUS':<12} {'TITLE'}")
    print("-" * 90)
    for t in sorted(q, key=lambda x: (-x.get("priority", 0), x["id"])):
        title = t.get("title", "")[:50]
        print(f"{t['id']:<12} {t.get('priority',0):<8} {t.get('owner',''):<15} {t.get('status',''):<12} {title}")

def claim_task(task_id):
    q = load_queue()
    for t in q:
        if t["id"] == task_id and t["status"] == "pending":
            t["status"] = "in-progress"
            t["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            save_queue(q)
            print(f"Claimed: {task_id}")
            return
    print(f"Task not found or not pending: {task_id}")

def complete_task(task_id, success=True):
    q = load_queue()
    for t in q:
        if t["id"] == task_id:
            t["status"] = "completed" if success else "failed"
            t["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            save_queue(q)
            print(f"Marked {'done' if success else 'failed'}: {task_id}")
            return
    print(f"Task not found: {task_id}")

def stats():
    q = load_queue()
    total = len(q)
    by_status = {}
    for t in q:
        s = t.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    print(f"\nTask Stats ({total} total):")
    for s, n in sorted(by_status.items()):
        print(f"  {s}: {n}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd, rest = args[0], args[1:]

    if cmd == "list":
        filter_s = rest[0] if rest else None
        list_tasks(filter_s)
    elif cmd == "claim":
        if not rest: print("Usage: claim <task-id>")
        else: claim_task(rest[0])
    elif cmd == "done":
        complete_task(rest[0], success=True) if rest else None
    elif cmd == "fail":
        complete_task(rest[0], success=False) if rest else None
    elif cmd == "reconcile":
        for r in reconcile(): print(r)
    elif cmd == "stats":
        stats()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()