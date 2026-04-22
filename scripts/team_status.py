#!/usr/bin/env python3
"""NEXUS OS v3.0 — Full Team Status Check (Fixed)"""
import os, importlib, sys, inspect

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

# Check format: (name, module, class_name, required_methods)
checks = [
    ("Trust Scoring v2.1", "nexus_os.governor.trust_scoring", "compute_score", None),
    ("TrustScoringGate", "nexus_os.governor.trust_scoring", "TrustScoringGate", ["score","get_trust","get_agent_card","record_refusal"]),
    ("TokenGuard", "nexus_os.monitoring.token_guard", "TokenGuard", ["track","check","remaining","get_remaining_budget"]),
    ("VAP Proof Chain", "nexus_os.governor.proof_chain", "VAPProofChain", ["append","verify"]),
    ("Bridge Server", "nexus_os.bridge.server", "BridgeServer", ["handle_request","handle_submit"]),
    ("Vault Manager", "nexus_os.vault.manager", "VaultManager", ["store","retrieve","promote"]),
    ("Governor", "nexus_os.governor.base", "NexusGovernor", ["check_access"]),
    ("KAIJU Auth", "nexus_os.governor.kaiju_auth", "KaijuAuthorizer", ["authorize"]),
    ("Hermes", "nexus_os.engine.hermes", "HermesRouter", None),
    ("GMR Rotator", "nexus_os.gmr.rotator", "GeniusModelRotator", ["get_routing_cascade","execute_with_fallback","register_model"]),
    ("GMR Telemetry", "nexus_os.gmr.telemetry", "TelemetryIngest", ["fetch"]),
    ("GMR Savings", "nexus_os.gmr.savings", "SavingsTracker", ["record","get_report"]),
    ("GMR Scheduler", "nexus_os.gmr.scheduler", "RefreshScheduler", ["start","stop"]),
    ("GMR Context", "nexus_os.gmr.context_packet", "ContextPacket", ["to_prompt_prefix"]),
    ("SkillSmith", "nexus_os.engine.skill_smith", "SkillSmith", ["record_outcome","get_skill_for_task","register_skill_manual"]),
    ("Foreman", "nexus_os.swarm.foreman", "Foreman", None),
    ("Coordinator", "nexus_os.team.coordinator", "TeamCoordinator", None),
]

ok = 0
fail = 0
for name, mod_path, class_or_func, methods in checks:
    try:
        mod = importlib.import_module(mod_path)
        obj = getattr(mod, class_or_func, None)
        if obj is None:
            print(f"  FAIL  {name} - {class_or_func} not found")
            fail += 1
            continue
        if methods is None:
            print(f"  OK    {name}")
            ok += 1
            continue
        if inspect.isclass(obj):
            missing = [m for m in methods if not hasattr(obj, m)]
            if missing:
                print(f"  WARN  {name} - missing methods: {missing}")
                fail += 1
            else:
                print(f"  OK    {name} - {len(methods)} methods verified")
                ok += 1
        else:
            print(f"  OK    {name}")
            ok += 1
    except Exception as e:
        err = str(e).split("\n")[0][:80]
        print(f"  FAIL  {name} - {err}")
        fail += 1

print(f"\n{ok} OK, {fail} issues\n")

# Integration checks
bs_path = os.path.join(REPO, "src", "nexus_os", "bridge", "server.py")
if os.path.exists(bs_path):
    with open(bs_path, "r", encoding="utf-8") as f:
        bs = f.read()
    for label, needle in [
        ("Bridge budget gate", "token_guard.check"),
        ("Bridge 429 response", "429"),
        ("Bridge X-Token-Remaining", "X-Token-Remaining"),
    ]:
        print(f"  {label}: {'YES' if needle in bs else 'NO'}")

tg_path = os.path.join(REPO, "src", "nexus_os", "monitoring", "token_guard.py")
if os.path.exists(tg_path):
    with open(tg_path, "r", encoding="utf-8") as f:
        tg = f.read()
    print(f"  TokenGuard GMR alias: {'YES' if 'get_remaining_budget' in tg else 'NO'}")

gc_path = os.path.join(REPO, "src", "nexus_os", "governor", "compliance.py")
if os.path.exists(gc_path):
    with open(gc_path, "r", encoding="utf-8") as f:
        gc = f.read()
    print(f"  Governor hard-stop: {'YES' if 'token_guard' in gc or 'TOKEN-BUDGET' in gc else 'NO'}")

gmr_dir = os.path.join(REPO, "src", "nexus_os", "gmr")
if os.path.isdir(gmr_dir):
    files = [f for f in os.listdir(gmr_dir) if f.endswith(".py") and f != "__init__.py"]
    print(f"  GMR package: {len(files)} modules")

print(f"\n{'='*50}")
print(f"RESULT: {ok} OK, {fail} issues")
print(f"{'='*50}")