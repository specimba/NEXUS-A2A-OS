#!/usr/bin/env python3
"""NEXUS OS v3.0 — Full Team Status Check"""
import os, importlib, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

checks = [
    ("Trust Scoring v2.1", "nexus_os.governor.trust_scoring", ["compute_score","ScoringInput","TrustScoringGate","MemoryTracks","AgentCard","FindingState","Lane"]),
    ("TokenGuard", "nexus_os.monitoring.token_guard", ["TokenGuard","track","check","remaining","get_remaining_budget"]),
    ("VAP Proof Chain", "nexus_os.governor.proof_chain", ["VAPProofChain","verify"]),
    ("Bridge Server", "nexus_os.bridge.server", ["BridgeServer","handle_request","token_guard"]),
    ("Vault Manager", "nexus_os.vault.manager", ["VaultManager","store","retrieve","promote"]),
    ("Engine Executor", "nexus_os.engine.executor", ["SyncCallbackExecutor","AsyncBridgeExecutor","KillSwitch","Task"]),
    ("Governor Base", "nexus_os.governor.base", ["NexusGovernor"]),
    ("KAIJU Auth", "nexus_os.governor.kaiju_auth", ["KAIJUAuth"]),
    ("Hermes Router", "nexus_os.engine.hermes", ["HermesRouter"]),
    ("Swarm Foreman", "nexus_os.swarm.foreman", ["Foreman"]),
    ("Team Coordinator", "nexus_os.team.coordinator", ["TeamCoordinator"]),
]

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 65)
print(" NEXUS OS v3.0 - FULL TEAM STATUS CHECK")
print("=" * 65)

loaded = 0
missing_count = 0
for name, module_path, attrs in checks:
    try:
        mod = importlib.import_module(module_path)
        missing = [a for a in attrs if not hasattr(mod, a)]
        if missing:
            print(f"  WARN  {name} - MISSING: {missing}")
            missing_count += 1
        else:
            print(f"  OK    {name} - all {len(attrs)} attrs present")
            loaded += 1
    except ImportError as e:
        print(f"  FAIL  {name} - IMPORT ERROR: {e}")
        missing_count += 1
    except Exception as e:
        print(f"  FAIL  {name} - ERROR: {e}")
        missing_count += 1

print()
print("--- Integration Checks ---")

bs_path = os.path.join(REPO, "src", "nexus_os", "bridge", "server.py")
if os.path.exists(bs_path):
    with open(bs_path, "r", encoding="utf-8") as f:
        bs = f.read()
    gate = "token_guard.check" in bs
    code429 = "429" in bs
    remain = "X-Token-Remaining" in bs
    print(f"  {'OK' if gate else 'MISSING'}    Bridge budget gate")
    print(f"  {'OK' if code429 else 'MISSING'}    Bridge 429 response")
    print(f"  {'OK' if remain else 'MISSING'}    Bridge X-Token-Remaining header")
else:
    print("  FAIL  Bridge file not found")

tg_path = os.path.join(REPO, "src", "nexus_os", "monitoring", "token_guard.py")
if os.path.exists(tg_path):
    with open(tg_path, "r", encoding="utf-8") as f:
        tg = f.read()
    alias = "get_remaining_budget" in tg
    print(f"  {'OK' if alias else 'MISSING'}    TokenGuard GMR alias")
else:
    print("  FAIL  TokenGuard file not found")

gc_path = os.path.join(REPO, "src", "nexus_os", "governor", "compliance.py")
if os.path.exists(gc_path):
    with open(gc_path, "r", encoding="utf-8") as f:
        gc = f.read()
    hardstop = "TOKEN-BUDGET" in gc or "token_guard" in gc
    print(f"  {'OK' if hardstop else 'MISSING'}    Governor hard-stop")
else:
    print("  FAIL  Governor compliance not found")

gmr_path = os.path.join(REPO, "src", "nexus_os", "gmr")
if os.path.isdir(gmr_path):
    files = os.listdir(gmr_path)
    print(f"  OK    GMR package: {files}")
else:
    print("  MISSING  GMR package")

print()
print("--- Test Inventory ---")
test_dirs = ["tests/governor","tests/bridge","tests/monitoring","tests/engine","tests/vault","tests/integration"]
total = 0
for td in test_dirs:
    full = os.path.join(REPO, td)
    if os.path.isdir(full):
        count = len([f for f in os.listdir(full) if f.startswith("test_") and f.endswith(".py")])
        total += count
        print(f"  {td}/ - {count} files")
    else:
        print(f"  {td}/ - EMPTY")
print(f"  Total test files: {total}")

print()
print(f"SUMMARY: {loaded} OK, {missing_count} issues")
print("=" * 65)