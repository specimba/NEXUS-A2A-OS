#!/usr/bin/env python3
import os

init_path = os.path.join("src", "nexus_os", "__init__.py")

if os.path.exists(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    with open(init_path, "w", encoding="utf-8") as f:
        for line in lines:
            # Fix the specific strategies import
            if "from .monitoring.strategies import" in line:
                f.write("from .monitoring.strategies import SemanticCache, hot_path, warm_path\n")
            # Scrub any lingering references to the dead stubs
            elif "ModelRouter" in line or "BudgetManager" in line:
                continue 
            else:
                f.write(line)
                
    print(f"[✅] Purged stale stubs from {init_path}")
else:
    print(f"[⚠️] {init_path} not found. Check path.")