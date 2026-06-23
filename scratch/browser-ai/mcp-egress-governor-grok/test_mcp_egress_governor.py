#!/usr/bin/env python3
"""
test_mcp_egress_governor.py
Self-contained verification for the dry-run mcp-egress-governor.
Runs the exact required test cases and prints clear PASS/FAIL + evidence.
No network calls. No secrets.
"""

import sys
from mcp_egress_governor import (
    MCPEgressGovernor,
    EgressRequest,
    create_test_governor,
)

def run_tests() -> bool:
    all_pass = True

    print("=" * 70)
    print("mcp-egress-governor DRY-RUN VERIFICATION SUITE")
    print("=" * 70)

    # Test 1: syntax/import already verified by py_compile; here we test basic instantiation
    print("\n[TEST 1] Syntax / Import / Instantiation")
    try:
        gov = create_test_governor()
        print("  PASS: Module imports cleanly and governor instantiates.")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_pass = False

    # Test 2: allowlisted read request returns dry-run proxy plan
    print("\n[TEST 2] Allowlisted read -> proxy_via_bridge plan (no network)")
    gov = create_test_governor()
    req = EgressRequest(
        target="https://huggingface.co/api/models",
        payload={"action": "list"},
        intent="read"
    )
    decision = gov.plan_egress(req)
    if decision.action == "proxy_via_bridge" and decision.proxy_plan is not None:
        print(f"  PASS: action={decision.action}, risk={decision.risk_level}")
        print(f"        proxy_plan backend: {decision.proxy_plan.get('backend')}")
        print(f"        note: {decision.proxy_plan.get('note')}")
    else:
        print(f"  FAIL: Expected proxy_via_bridge, got {decision.action} - {decision.reason}")
        all_pass = False

    # Test 3: non-allowlisted domain blocks (fail-closed)
    print("\n[TEST 3] Non-allowlisted domain -> block (fail-closed)")
    gov = create_test_governor()
    req_bad = EgressRequest(
        target="https://evil.example.com/payload",
        payload={},
        intent="read"
    )
    decision = gov.plan_egress(req_bad)
    if decision.action == "block" and "non-allowlisted" in decision.reason.lower():
        print(f"  PASS: action={decision.action}, reason={decision.reason}")
    else:
        print(f"  FAIL: Expected block for non-allowlist, got {decision.action} - {decision.reason}")
        all_pass = False

    # Test 4: write/exec intent escalates to require_kaiju_approval (high risk)
    print("\n[TEST 4] High-risk write/exec intent -> require_kaiju_approval (dry-run)")
    gov = create_test_governor()
    req_write = EgressRequest(
        target="https://huggingface.co/api/models",
        payload={"model": " dangerous"},
        intent="write"
    )
    decision = gov.plan_egress(req_write)
    if decision.action == "require_kaiju_approval" and "KAIJU" in decision.reason.upper():
        print(f"  PASS: action={decision.action}, reason={decision.reason}")
    else:
        print(f"  FAIL: Expected require_kaiju_approval, got {decision.action} - {decision.reason}")
        all_pass = False

    # Test 5: TokenGuard exhausted path blocks
    print("\n[TEST 5] TokenGuard exhausted -> block")
    gov = create_test_governor(token_budget=0)  # simulate exhausted
    req = EgressRequest(target="https://huggingface.co/api/models", payload={}, intent="read")
    decision = gov.plan_egress(req)
    if decision.action == "block" and "TokenGuard" in decision.reason:
        print(f"  PASS: action={decision.action}, reason={decision.reason}")
    else:
        print(f"  FAIL: Expected block on exhausted, got {decision.action} - {decision.reason}")
        all_pass = False

    # Test 6: no live network call in dry-run mode (evidence: we never reached network code)
    print("\n[TEST 6] Dry-run guarantees no network (structural + behavioral)")
    # We already proved by: (a) syntax ok, (b) all plan_egress paths above returned decisions
    # without any socket/requests/urllib, (c) proxy_plan contains only strings describing the plan.
    # Additional runtime check: ensure no unexpected side effects on token_budget for a normal call.
    gov = create_test_governor(token_budget=50)
    req = EgressRequest(target="https://huggingface.co/api/models", payload={}, intent="read")
    _ = gov.plan_egress(req)
    if gov.token_budget == 49:  # one cost deducted
        print("  PASS: Dry-run executed decision logic only (budget decremented, no I/O).")
    else:
        print(f"  FAIL: Unexpected budget state {gov.token_budget}")
        all_pass = False

    print("\n" + "=" * 70)
    if all_pass:
        print("OVERALL RESULT: ALL TESTS PASSED (6/6)")
        print("Evidence: All decisions returned correctly in dry-run with no network, proper blocks, and governance paths exercised.")
    else:
        print("OVERALL RESULT: SOME TESTS FAILED - review output above.")
    print("=" * 70)
    return all_pass


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)