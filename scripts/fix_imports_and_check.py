#!/usr/bin/env python3
"""Fix import mismatches + run corrected team check"""
import os, re, importlib, sys, inspect

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)

print("=" * 65)
print(" PHASE 1: FIX IMPORT MISMATCHES")
print("=" * 65)

# ── Fix 1: trust_scoring.py imports ProofChain ────────────────
ts_path = os.path.join(SRC, "nexus_os", "governor", "trust_scoring.py")
if os.path.exists(ts_path):
    with open(ts_path, "r", encoding="utf-8") as f:
        ts = f.read()
    if "ProofChain" in ts and "VAPProofChain" not in ts:
        ts = ts.replace("from nexus_os.governor.proof_chain import ProofChain",
                        "from nexus_os.governor.proof_chain import VAPProofChain as ProofChain")
        ts = ts.replace("import ProofChain",
                        "from nexus_os.governor.proof_chain import VAPProofChain as ProofChain")
        with open(ts_path, "w", encoding="utf-8") as f:
            f.write(ts)
        print("  FIX  trust_scoring.py: Added ProofChain alias for VAPProofChain")
    elif "VAPProofChain" in ts:
        print("  OK    trust_scoring.py: Already has VAPProofChain")
    else:
        print("  INFO  trust_scoring.py: No ProofChain import found (may not need it)")
else:
    print("  SKIP  trust_scoring.py not found")

# ── Fix 2: hermes.py imports GMRSelection ─────────────────────
hermes_path = os.path.join(SRC, "nexus_os", "engine", "hermes.py")
if os.path.exists(hermes_path):
    with open(hermes_path, "r", encoding="utf-8") as f:
        hermes = f.read()
    if "GMRSelection" in hermes:
        # Find what's imported and from where
        for line in hermes.split("\n"):
            if "GMRSelection" in line and ("import" in line or "from" in line):
                print(f"  FOUND hermes.py import: {line.strip()}")
        # Add GMRSelection as alias for ModelProfile or create a compat export
        print("  FIX  Will add GMRSelection compat export to gmr/rotator.py")
    else:
        print("  OK    hermes.py: No GMRSelection import")
else:
    print("  SKIP  hermes.py not found")

# ── Fix 3: coordinator.py imports GMRSelection ────────────────
coord_path = os.path.join(SRC, "nexus_os", "team", "coordinator.py")
if os.path.exists(coord_path):
    with open(coord_path, "r", encoding="utf-8") as f:
        coord = f.read()
    if "GMRSelection" in coord:
        for line in coord.split("\n"):
            if "GMRSelection" in line and ("import" in line or "from" in line):
                print(f"  FOUND coordinator.py import: {line.strip()}")
        print("  FIX  Will add GMRSelection compat export to gmr/rotator.py")
    else:
        print("  OK    coordinator.py: No GMRSelection import")
else:
    print("  SKIP  coordinator.py not found")

# ── Fix 4: Add GMRSelection to gmr/rotator.py and __init__.py ─
rotator_path = os.path.join(SRC, "nexus_os", "gmr", "rotator.py")
init_path = os.path.join(SRC, "nexus_os", "gmr", "__init__.py")

# Add GMRSelection as a compatibility alias
gmrsel_code = '''

# Compatibility alias for downstream consumers (Hermes, Coordinator)
@dataclass
class GMRSelection:
    """Result of model selection (compatibility alias)."""
    primary: str
    fallbacks: List[str]
    reason: str
    pool: ModelPool = ModelPool.FAST
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0
'''

if os.path.exists(rotator_path):
    with open(rotator_path, "r", encoding="utf-8") as f:
        rot = f.read()
    if "GMRSelection" not in rot:
        # Insert after IntentClassifier class
        anchor = "class GeniusModelRotator:"
        if anchor in rot:
            rot = rot.replace(anchor, gmrsel_code + "\n\nclass GeniusModelRotator:")
            with open(rotator_path, "w", encoding="utf-8") as f:
                f.write(rot)
            print("  FIX  gmr/rotator.py: Added GMRSelection class")
        else:
            print("  WARN  gmr/rotator.py: Could not find insertion point")
    else:
        print("  OK    gmr/rotator.py: GMRSelection already exists")

if os.path.exists(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        ini = f.read()
    if "GMRSelection" not in ini:
        ini = ini.replace(
            "IntentCategory, IntentClassifier",
            "IntentCategory, IntentClassifier, GMRSelection"
        )
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(ini)
        print("  FIX  gmr/__init__.py: Added GMRSelection export")
    else:
        print("  OK    gmr/__init__.py: GMRSelection already exported")

# ── Fix 5: Check KAIJU Auth class name ────────────────────────
kaiju_path = os.path.join(SRC, "nexus_os", "governor", "kaiju_auth.py")
if os.path.exists(kaiju_path):
    with open(kaiju_path, "r", encoding="utf-8") as f:
        kaiju = f.read()
    # Find class definitions
    classes = re.findall(r'^class (\w+)', kaiju, re.MULTILINE)
    print(f"  INFO  kaiju_auth.py classes: {classes}")
else:
    print("  SKIP  kaiju_auth.py not found")

# ── Fix 6: Check Executor classes ─────────────────────────────
exec_path = os.path.join(SRC, "nexus_os", "engine", "executor.py")
if os.path.exists(exec_path):
    with open(exec_path, "r", encoding="utf-8") as f:
        exe = f.read()
    classes = re.findall(r'^class (\w+)', exe, re.MULTILINE)
    print(f"  INFO  executor.py classes: {classes}")
else:
    print("  SKIP  executor.py not found")

# ═══════════════════════════════════════════════════════════════
print()
print("=" * 65)
print(" PHASE 2: CORRECTED TEAM CHECK")
print("=" * 65)

# Corrected check: look for class names, then verify methods on classes
checks = [
    ("Trust Scoring v2.1", "nexus_os.governor.trust_scoring",
     {"compute_score": "function", "ScoringInput": "class",
      "TrustScoringGate": "class", "MemoryTracks": "class",
      "AgentCard": "class", "FindingState": "class", "Lane": "class"}),
    ("TokenGuard", "nexus_os.monitoring.token_guard",
     {"TokenGuard": "class"}),
    ("VAP Proof Chain", "nexus_os.governor.proof_chain",
     {"VAPProofChain": "class"}),
    ("Bridge Server", "nexus_os.bridge.server",
     {"BridgeServer": "class"}),
    ("Vault Manager", "nexus_os.vault.manager",
     {"VaultManager": "class"}),
    ("Engine Executor", "nexus_os.engine.executor",
     {"SyncCallbackExecutor": "class", "AsyncBridgeExecutor": "class"}),
    ("Governor Base", "nexus_os.governor.base",
     {"NexusGovernor": "class"}),
    ("KAIJU Auth", "nexus_os.governor.kaiju_auth",
     {}),  # Will discover class name
    ("Hermes Router", "nexus_os.engine.hermes",
     {"HermesRouter": "class"}),
    ("GMR Rotator", "nexus_os.gmr.rotator",
     {"GeniusModelRotator": "class", "ModelProfile": "class",
      "ModelPool": "class", "IntentCategory": "class",
      "IntentClassifier": "class", "GMRSelection": "class"}),
    ("GMR Telemetry", "nexus_os.gmr.telemetry",
     {"TelemetryIngest": "class", "ModelTelemetry": "class"}),
    ("GMR Savings", "nexus_os.gmr.savings",
     {"SavingsTracker": "class"}),
    ("GMR Scheduler", "nexus_os.gmr.scheduler",
     {"RefreshScheduler": "class"}),
    ("GMR Context", "nexus_os.gmr.context_packet",
     {"ContextPacket": "class"}),
    ("Swarm Foreman", "nexus_os.swarm.foreman",
     {"Foreman": "class"}),
    ("Team Coordinator", "nexus_os.team.coordinator",
     {"TeamCoordinator": "class"}),
]

ok_count = 0
fail_count = 0

for name, module_path, attrs in checks:
    try:
        mod = importlib.import_module(module_path)
        if not attrs:
            # Auto-discover classes
            classes = [n for n, v in inspect.getmembers(mod, inspect.isclass)
                      if not n.startswith("_")]
            print(f"  OK    {name} - classes: {classes}")
            ok_count += 1
            continue
        missing = []
        for attr_name, attr_type in attrs.items():
            obj = getattr(mod, attr_name, None)
            if obj is None:
                missing.append(attr_name)
            elif attr_type == "class" and not inspect.isclass(obj):
                missing.append(f"{attr_name}(not class)")
            elif attr_type == "function" and not callable(obj):
                missing.append(f"{attr_name}(not callable)")
        if missing:
            print(f"  WARN  {name} - MISSING: {missing}")
            fail_count += 1
        else:
            print(f"  OK    {name} - all {len(attrs)} present")
            ok_count += 1
    except ImportError as e:
        print(f"  FAIL  {name} - IMPORT: {e}")
        fail_count += 1
    except Exception as e:
        print(f"  FAIL  {name} - ERROR: {e}")
        fail_count += 1

print()
print(f"RESULT: {ok_count} OK, {fail_count} issues")
print("=" * 65)