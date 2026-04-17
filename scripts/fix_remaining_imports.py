#!/usr/bin/env python3
"""Fix 2 remaining import issues: governor/__init__.py and coordinator.py"""
import os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src")

print("=" * 65)
print(" DIAGNOSE + FIX REMAINING IMPORT ISSUES")
print("=" * 65)

# ── Issue 1: Trust Scoring import fails ───────────────────────
# Something in the import chain does: from proof_chain import ProofChain
# (not VAPProofChain). Most likely governor/__init__.py

gov_init = os.path.join(SRC, "nexus_os", "governor", "__init__.py")
print("\n--- Issue 1: governor/__init__.py ---")
if os.path.exists(gov_init):
    with open(gov_init, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"  Content ({len(content)} chars):")
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            print(f"    {i}: {line.rstrip()}")

    if "ProofChain" in content and "VAPProofChain" not in content:
        content = content.replace("from nexus_os.governor.proof_chain import ProofChain",
                                  "from nexus_os.governor.proof_chain import VAPProofChain")
        # Also handle direct imports
        content = content.replace("import ProofChain",
                                  "from nexus_os.governor.proof_chain import VAPProofChain")
        with open(gov_init, "w", encoding="utf-8") as f:
            f.write(content)
        print("  FIX  Replaced ProofChain -> VAPProofChain")
    elif "ProofChain" in content and "VAPProofChain" in content:
        print("  OK    Already has VAPProofChain")
    else:
        # Maybe the init imports from another module that imports ProofChain
        print("  INFO  No ProofChain in __init__.py - checking other files...")
        # Scan all .py in governor/ for ProofChain import
        gov_dir = os.path.join(SRC, "nexus_os", "governor")
        for fname in os.listdir(gov_dir):
            if fname.endswith(".py") and fname != "__init__.py":
                fpath = os.path.join(gov_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    fcontent = f.read()
                if "ProofChain" in fcontent:
                    lines_with = [l.strip() for l in fcontent.split("\n")
                                 if "ProofChain" in l and "import" in l]
                    if lines_with:
                        print(f"  FOUND in {fname}:")
                        for l in lines_with:
                            print(f"    {l}")
                        # Fix it
                        fixed = fcontent.replace(
                            "from nexus_os.governor.proof_chain import ProofChain",
                            "from nexus_os.governor.proof_chain import VAPProofChain"
                        )
                        fixed = fixed.replace(
                            "from .proof_chain import ProofChain",
                            "from .proof_chain import VAPProofChain"
                        )
                        fixed = fixed.replace(
                            "import ProofChain",
                            "from nexus_os.governor.proof_chain import VAPProofChain"
                        )
                        if fixed != fcontent:
                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(fixed)
                            print(f"  FIX  {fname}: Replaced ProofChain -> VAPProofChain")
else:
    print("  SKIP  governor/__init__.py not found")

# Also check if proof_chain.py itself has ProofChain (old name)
pc_path = os.path.join(SRC, "nexus_os", "governor", "proof_chain.py")
if os.path.exists(pc_path):
    with open(pc_path, "r", encoding="utf-8") as f:
        pc = f.read()
    has_vap = "class VAPProofChain" in pc
    has_proof = "class ProofChain" in pc
    print(f"  INFO  proof_chain.py: VAPProofChain={has_vap}, ProofChain={has_proof}")
    if has_vap and not has_proof:
        # Add ProofChain as alias
        pc = pc.replace("class VAPProofChain",
                        "class VAPProofChain\n\n# Backward compatibility\nProofChain = VAPProofChain\n# class VAPProofChain")
        # Actually, cleaner approach: add alias after the class
        pass

# ── Issue 2: Team Coordinator imports TaskDomain ──────────────
print("\n--- Issue 2: team/coordinator.py ---")
coord_path = os.path.join(SRC, "nexus_os", "team", "coordinator.py")
hermes_path = os.path.join(SRC, "nexus_os", "engine", "hermes.py")

# First, discover what hermes.py actually exports
if os.path.exists(hermes_path):
    with open(hermes_path, "r", encoding="utf-8") as f:
        hermes = f.read()
    classes = re.findall(r'^class (\w+)', hermes, re.MULTILINE)
    enums = re.findall(r'^class (\w+)\(Enum\)', hermes, re.MULTILINE)
    all_exports = classes + enums
    print(f"  hermes.py exports: {all_exports}")

    # Check if TaskDomain exists under different name
    for name in all_exports:
        if "domain" in name.lower() or "task" in name.lower():
            print(f"  FOUND  Similar class: {name}")

    if "TaskDomain" not in all_exports:
        print("  INFO  TaskDomain not in hermes.py - need to add it or fix import")

if os.path.exists(coord_path):
    with open(coord_path, "r", encoding="utf-8") as f:
        coord = f.read()
    # Find all import lines
    import_lines = [l.strip() for l in coord.split("\n")
                   if "import" in l and "hermes" in l.lower()]
    print(f"  coordinator.py hermes imports:")
    for l in import_lines:
        print(f"    {l}")

    # Find all lines using TaskDomain
    td_lines = [l.strip() for l in coord.split("\n") if "TaskDomain" in l]
    print(f"  TaskDomain usage:")
    for l in td_lines:
        print(f"    {l}")

# ── Fix: Add TaskDomain to hermes.py ──────────────────────────
if os.path.exists(hermes_path):
    with open(hermes_path, "r", encoding="utf-8") as f:
        hermes = f.read()

    if "TaskDomain" not in hermes:
        # Find the Enum import
        task_domain_code = '''

class TaskDomain(Enum):
    """Task domain classification for routing."""
    CODE = "code"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    CREATIVE = "creative"
    OPERATIONS = "operations"
    SECURITY = "security"

class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"
    STANDARD = "standard"
    COMPLEX = "complex"
    CRITICAL = "critical"
'''
        # Insert after the last Enum class or after imports
        # Find a good insertion point
        if "class HermesRouter" in hermes:
            hermes = hermes.replace("class HermesRouter",
                                    task_domain_code + "\nclass HermesRouter")
            with open(hermes_path, "w", encoding="utf-8") as f:
                f.write(hermes)
            print("  FIX  hermes.py: Added TaskDomain and TaskComplexity enums")
        else:
            print("  WARN  hermes.py: Could not find HermesRouter insertion point")
    else:
        print("  OK    hermes.py: TaskDomain already exists")

# ── Add backward compat alias: ProofChain = VAPProofChain ─────
if os.path.exists(pc_path):
    with open(pc_path, "r", encoding="utf-8") as f:
        pc = f.read()
    if "ProofChain = VAPProofChain" not in pc:
        # Add alias at end of file
        pc += "\n\n# Backward compatibility alias\nProofChain = VAPProofChain\n"
        with open(pc_path, "w", encoding="utf-8") as f:
            f.write(pc)
        print("  FIX  proof_chain.py: Added ProofChain = VAPProofChain alias")
    else:
        print("  OK    proof_chain.py: Alias already exists")

print()
print("=" * 65)
print(" RE-VERIFY")
print("=" * 65)

import sys
sys.path.insert(0, SRC)

# Quick check of the 2 failing modules
try:
    from nexus_os.governor.trust_scoring import compute_score, TrustScoringGate
    print("  OK    Trust Scoring v2.1 imports successfully")
except Exception as e:
    print(f"  FAIL  Trust Scoring: {e}")

try:
    from nexus_os.team.coordinator import TeamCoordinator
    print("  OK    Team Coordinator imports successfully")
except Exception as e:
    print(f"  FAIL  Team Coordinator: {e}")

try:
    from nexus_os.gmr.rotator import GMRSelection, GeniusModelRotator
    print("  OK    GMR Rotator (with GMRSelection) imports successfully")
except Exception as e:
    print(f"  FAIL  GMR Rotator: {e}")

print("=" * 65)