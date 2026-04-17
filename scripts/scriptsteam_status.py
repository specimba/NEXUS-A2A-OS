python -c "
import os, importlib, sys, inspect
sys.path.insert(0, 'src')

checks = [
    ('Trust Scoring v2.1', 'nexus_os.governor.trust_scoring', ['compute_score','TrustScoringGate','MemoryTracks','AgentCard','Lane','FindingState']),
    ('TokenGuard', 'nexus_os.monitoring.token_guard', ['TokenGuard']),
    ('VAP Proof Chain', 'nexus_os.governor.proof_chain', ['VAPProofChain']),
    ('Bridge Server', 'nexus_os.bridge.server', ['BridgeServer']),
    ('Vault Manager', 'nexus_os.vault.manager', ['VaultManager']),
    ('Executor', 'nexus_os.engine.executor', ['SyncCallbackExecutor','AsyncBridgeExecutor']),
    ('Governor', 'nexus_os.governor.base', ['NexusGovernor']),
    ('KAIJU', 'nexus_os.governor.kaiju_auth', ['KaijuAuthorizer']),
    ('Hermes', 'nexus_os.engine.hermes', ['HermesRouter','TaskDomain','SkillRecord']),
    ('GMR Rotator', 'nexus_os.gmr.rotator', ['GeniusModelRotator','GMRSelection','IntentClassifier']),
    ('GMR Telemetry', 'nexus_os.gmr.telemetry', ['TelemetryIngest']),
    ('GMR Savings', 'nexus_os.gmr.savings', ['SavingsTracker']),
    ('GMR Scheduler', 'nexus_os.gmr.scheduler', ['RefreshScheduler']),
    ('GMR Context', 'nexus_os.gmr.context_packet', ['ContextPacket']),
    ('SkillSmith', 'nexus_os.engine.skill_smith', ['SkillSmith','SkillRecord','SkillStatus']),
    ('Foreman', 'nexus_os.swarm.foreman', ['Foreman']),
    ('Coordinator', 'nexus_os.team.coordinator', ['TeamCoordinator']),
]

ok = 0
fail = 0
for name, mod_path, attrs in checks:
    try:
        mod = importlib.import_module(mod_path)
        missing = [a for a in attrs if not hasattr(mod, a)]
        if missing:
            print(f'  WARN  {name} - missing: {missing}')
            fail += 1
        else:
            print(f'  OK    {name}')
            ok += 1
    except Exception as e:
        print(f'  FAIL  {name} - {e}')
        fail += 1

print(f'\n{ok} OK, {fail} issues')

# Quick integration checks
bs = open('src/nexus_os/bridge/server.py','r',encoding='utf-8').read()
tg = open('src/nexus_os/monitoring/token_guard.py','r',encoding='utf-8').read()
print(f'  Bridge budget gate: {\"YES\" if \"token_guard.check\" in bs else \"NO\"}')
print(f'  Bridge 429: {\"YES\" if \"429\" in bs else \"NO\"}')
print(f'  Bridge X-Token-Remaining: {\"YES\" if \"X-Token-Remaining\" in bs else \"NO\"}')
print(f'  TG get_remaining_budget: {\"YES\" if \"get_remaining_budget\" in tg else \"NO\"}')

# Test counts
total = 0
for td in ['tests/governor','tests/bridge','tests/monitoring','tests/engine','tests/vault','tests/integration']:
    if os.path.isdir(td):
        c = len([f for f in os.listdir(td) if f.startswith('test_') and f.endswith('.py')])
        total += c
        print(f'  {td}/ - {c} files')
print(f'  Total test files: {total}')
"