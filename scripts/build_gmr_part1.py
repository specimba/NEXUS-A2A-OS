import os, importlib, sys
sys.path.insert(0, 'src')

checks = [
    ('Trust Scoring v2.1', 'nexus_os.governor.trust_scoring', ['compute_score','ScoringInput','TrustScoringGate','MemoryTracks','AgentCard','FindingState','Lane']),
    ('TokenGuard', 'nexus_os.monitoring.token_guard', ['TokenGuard','track','check','remaining','get_remaining_budget']),
    ('VAP Proof Chain', 'nexus_os.governor.proof_chain', ['VAPProofChain','verify']),
    ('Bridge Server', 'nexus_os.bridge.server', ['BridgeServer','handle_request','token_guard']),
    ('Vault Manager', 'nexus_os.vault.manager', ['VaultManager','store','retrieve','promote']),
    ('Engine Executor', 'nexus_os.engine.executor', ['SyncCallbackExecutor','AsyncBridgeExecutor','KillSwitch','Task']),
    ('Governor Base', 'nexus_os.governor.base', ['NexusGovernor']),
    ('KAIJU Auth', 'nexus_os.governor.kaiju_auth', ['KAIJUAuth']),
    ('Hermes Router', 'nexus_os.engine.hermes', ['HermesRouter']),
    ('Swarm Foreman', 'nexus_os.swarm.foreman', ['Foreman']),
    ('Team Coordinator', 'nexus_os.team.coordinator', ['TeamCoordinator']),
]

print('='*65)
print(' NEXUS OS v3.0 — FULL TEAM STATUS CHECK')
print('='*65)

for name, module_path, attrs in checks:
    try:
        mod = importlib.import_module(module_path)
        missing = [a for a in attrs if not hasattr(mod, a)]
        if missing:
            print(f'  WARNING  {name} — loaded, MISSING: {missing}')
        else:
            print(f'  OK  {name} — all {len(attrs)} attrs present')
    except ImportError as e:
        print(f'  FAIL  {name} — IMPORT ERROR: {e}')
    except Exception as e:
        print(f'  FAIL  {name} — ERROR: {e}')

print()
print('--- Integration Checks ---')
try:
    with open('src/nexus_os/bridge/server.py','r') as f: bs = f.read()
    print(f'  {\"OK\" if \"token_guard.check\" in bs else \"MISSING\"}  Bridge budget gate')
    print(f'  {\"OK\" if \"429\" in bs and \"budget\" in bs.lower() else \"MISSING\"}  Bridge 429 response')
    print(f'  {\"OK\" if \"X-Token-Remaining\" in bs else \"MISSING\"}  Bridge X-Token-Remaining header')
except: print('  FAIL  Bridge file check failed')

try:
    with open('src/nexus_os/monitoring/token_guard.py','r') as f: tg = f.read()
    print(f'  {\"OK\" if \"get_remaining_budget\" in tg else \"MISSING\"}  TokenGuard GMR alias')
except: print('  FAIL  TokenGuard file check failed')

try:
    with open('src/nexus_os/governor/compliance.py','r') as f: gc = f.read()
    print(f'  {\"OK\" if \"TOKEN-BUDGET\" in gc or 'token_guard' in gc else \"MISSING\"}  Governor hard-stop')
except: print('  FAIL  Governor compliance check failed')

gmr_path = os.path.join('src','nexus_os','gmr')
if os.path.isdir(gmr_path):
    files = os.listdir(gmr_path)
    print(f'  OK  GMR package: {files}')
else:
    print(f'  MISSING  GMR package (next to build)')

print()
print('--- Test Inventory ---')
test_dirs = ['tests/governor','tests/bridge','tests/monitoring','tests/engine','tests/vault','tests/integration']
total = 0
for td in test_dirs:
    if os.path.isdir(td):
        count = len([f for f in os.listdir(td) if f.startswith('test_') and f.endswith('.py')])
        total += count
        print(f'  {td}/ — {count} files')
    else:
        print(f'  {td}/ — MISSING')
print(f'  Total test files: {total}')
print('='*65)
"