#!/usr/bin/env python3
"""NEXUS OS v3.0 - Full Team Status Check"""
import os, importlib, sys, inspect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

checks = [
    ("Trust Scoring v2.1", "nexus_os.governor.trust_scoring", ["compute_score","TrustScoringGate","MemoryTracks","AgentCard","Lane","FindingState"]),
    ("TokenGuard", "nexus_os.monitoring.token_guard", ["TokenGuard"]),
    ("VAP Proof Chain", "nexus_os.governor.proof_chain", ["VAPProofChain"]),
    ("Bridge Server", "nexus_os.bridge.server", ["BridgeServer"]),
    ("Vault Manager", "nexus_os.vault.manager", ["VaultManager"]),
    ("Executor", "nexus_os.engine.executor", ["SyncCallbackExecutor","AsyncBridgeExecutor"]),
    ("Governor", "nexus_os.governor.base", ["NexusGovernor"]),
    ("KAIJU", "nexus_os.governor.kaiju_auth", ["KaijuAuthorizer"]),
    ("Hermes", "nexus_os.engine.hermes", ["HermesRouter","TaskDomain","SkillRecord"]),
    ("GMR Rotator", "nexus_os.gmr.rotator", ["GeniusModelRotator","GMRSelection","IntentClassifier"]),
    ("GMR Telemetry", "nexus_os.gmr.telemetry", ["TelemetryIngest"]),
    ("GMR Savings", "nexus_os.gmr.savings", ["SavingsTracker"]),
    ("GMR Scheduler", "nexus_os.gmr.scheduler", ["RefreshScheduler"]),
    ("GMR Context", "nexus_os.gmr.context_packet", ["ContextPacket"]),
    ("SkillSmith", "nexus_os.engine.skill_smith", ["SkillSmith","SkillRecord","SkillStatus"]),
    ("Foreman", "nexus_os.swarm.foreman", ["Foreman"]),
    ("Coordinator", "nexus_os.team.coordinator", ["TeamCoordinator"]),
]

ok = 0
fail = 0
for name, mod_path, attrs in checks:
    try:
        mod = importlib.import_module(mod_path)
        missing = [a for a in attrs if not hasattr(mod, a)]
        if missing:
            print(f"  WARN  {name} - missing: {missing}")
            fail += 1
        else:
            print(f"  OK    {name}")
            ok += 1
    except Exception as e:
        print(f"  FAIL  {name} - {e}")
        fail += 1

print(f"\n{ok} OK, {fail} issues")

# Integration checks
bs_path = os.path.join(REPO, "src", "nexus_os", "bridge", "server.py")
if os.path.exists(bs_path):
    with open(bs_path, "r", encoding="utf-8") as f:
        bs = f.read()
    gate = "token_guard.check" in bs
    code429 = "429" in bs
    remain = "X-Token-Remaining" in bs
    print(f"  Bridge budget gate: {'YES' if gate else 'NO'}")
    print(f"  Bridge 429: {'YES' if code429 else 'NO'}")
    print(f"  Bridge X-Token-Remaining: {'YES' if remain else 'NO'}")

tg_path = os.path.join(REPO, "src", "nexus_os", "monitoring", "token_guard.py")
if os.path.exists(tg_path):
    with open(tg_path, "r", encoding="utf-8") as f:
        tg = f.read()
    alias = "get_remaining_budget" in tg
    print(f"  TG get_remaining_budget: {'YES' if alias else 'NO'}")

# Test counts
total = 0
for td in ["tests/governor","tests/bridge","tests/monitoring","tests/engine","tests/vault","tests/integration"]: