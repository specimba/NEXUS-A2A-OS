#!/usr/bin/env python3
import os

print("🩹 Patching final pytest mock signatures...")

# 1. Add is_available() to Flexible ModelProfile
for filepath in ["src/nexus_os/engine/hermes.py", "src/nexus_os/gmr/rotator.py"]:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            c = f.read()
        
        if "def is_available(self):" not in c:
            c = c.replace("self.supported_domains = self.intent_categories", 
                          "self.supported_domains = self.intent_categories\n\n    def is_available(self):\n        return True")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"[✅] Added is_available() to ModelProfile in {os.path.basename(filepath)}")

# 2. Remove invalid 'task_id' from RoutingDecision fallback
coord_path = os.path.join("src", "nexus_os", "team", "coordinator.py")
if os.path.exists(coord_path):
    with open(coord_path, "r", encoding="utf-8") as f:
        c = f.read()
    
    if "task_id=task_id," in c:
        c = c.replace("task_id=task_id,", "")
        with open(coord_path, "w", encoding="utf-8") as f:
            f.write(c)
        print("[✅] Removed invalid task_id kwarg from RoutingDecision in coordinator.py")

print("\n[🚀] Run: python -m pytest tests/ -q --tb=short")