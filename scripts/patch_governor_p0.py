#!/usr/bin/env python3
"""P0 Patch: TokenGuard & VAP <-> Governor Integration

Run: python scripts/patch_governor_p0.py
"""

import os, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

comp_path = os.path.join(REPO_ROOT, "src", "nexus_os", "governor", "compliance.py")

with open(comp_path, "r", encoding="utf-8") as f:
    comp = f.read()

changes = 0

# 1. Add Imports at the top (after existing imports)
IMPORTS = """
from nexus_os.monitoring.token_guard import TokenGuard
from nexus_os.governor.proof_chain import ProofChain as VAPProofChain
"""

if "from nexus_os.monitoring.token_guard" not in comp:
    # Insert after the existing imports
    comp = comp.replace(
        "from nexus_os.db.manager import DatabaseManager",
        "from nexus_os.db.manager import DatabaseManager\nfrom nexus_os.monitoring.token_guard import TokenGuard\nfrom nexus_os.governor.proof_chain import ProofChain as VAPProofChain"
    )
    changes += 1
    print("[OK] compliance.py: Added TokenGuard and VAP imports")

# 2. Modify __init__ to accept optional token_guard and vap_chain
OLD_INIT = """    def __init__(self, db: DatabaseManager):
        self.db = db
        self._rules: Dict[str, ComplianceRule] = {}
        self._check_history: List[ComplianceResult] = []"""

NEW_INIT = """    def __init__(self, db: DatabaseManager = None, token_guard: TokenGuard = None, vap_chain: VAPProofChain = None):
        self.db = db
        self.token_guard = token_guard or TokenGuard()
        self.vap = vap_chain or VAPProofChain()
        self._rules: Dict[str, ComplianceRule] = {}
        self._check_history: List[ComplianceResult] = []"""

if "self.token_guard = token_guard" not in comp:
    comp = comp.replace(OLD_INIT, NEW_INIT, 1)
    changes += 1
    print("[OK] compliance.py: Injected TokenGuard and VAP into __init__")

# 3. Add budget check at start of evaluate() method
# Find where result = ComplianceResult() is and add budget check after
BUDGET_CHECK = """        result = ComplianceResult(trace_id=trace_id)

        # ── P0: TokenGuard Hard Stop Check ──
        if hasattr(self, 'token_guard'):
            required_tokens = context.get('required_tokens', 1000)
            if not self.token_guard.check(agent_id, required_tokens):
                violation = ComplianceViolation(
                    rule_id="TOKEN-BUDGET-001",
                    rule_name="Token Budget Exceeded",
                    level=ComplianceLevel.CRITICAL,
                    message=f"Token budget exceeded for {agent_id}. Required: {required_tokens}, Remaining: {self.token_guard.remaining(agent_id)}",
                    remediation="Request additional token budget or wait for budget reset.",
                )
                violation.source = RuleSource.INTERNAL
                result.violations.append(violation)
                result.status = ComplianceStatus.BLOCKED
                result.rules_checked = 1

                # Log VAP rejection
                if hasattr(self, 'vap'):
                    self.vap.record(
                        agent_id=agent_id,
                        action=action,
                        details={"reason": "budget_exceeded", "required": required_tokens, "remaining": self.token_guard.remaining(agent_id)},
                        level="WARNING"
                    )

                self._log_evaluation(result, agent_id, action, context)
                self._check_history.append(result)
                logger.warning(
                    "Compliance: BLOCKED (budget) — agent=%s action=%s remaining=%d",
                    agent_id, action, self.token_guard.remaining(agent_id)
                )
                return result

        # Log VAP approval (only if budget check passed)
        if hasattr(self, 'vap'):
            self.vap.record(
                agent_id=agent_id,
                action=action,
                details={"required_tokens": context.get('required_tokens', 1000)},
                level="INFO"
            )
"""

if "TOKEN-BUDGET-001" not in comp:
    comp = comp.replace(
        "        result = ComplianceResult(trace_id=trace_id)\n        rules_checked = 0",
        BUDGET_CHECK + "        rules_checked = 0"
    )
    changes += 1
    print("[OK] compliance.py: Added Budget Hard-Stop and VAP Audit logging")

with open(comp_path, "w", encoding="utf-8") as f:
    f.write(comp)

print(f"\n[SUMMARY] compliance.py: {changes} changes applied")
print("Next: pytest tests/governor/test_compliance_p0.py -v")
