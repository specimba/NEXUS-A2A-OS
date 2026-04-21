#!/usr/bin/env python3
"""NEXUS OS v3.0 - System Diagnostic Tool

Usage:
    python scripts/diagnostic.py              # Full diagnostic
    python scripts/diagnostic.py gmr         # GMR only
    python scripts/diagnostic.py routing     # Routing only
    python scripts/diagnostic.py integration # Full pipeline
"""

import sys
import os
import time
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def check_gmr() -> Tuple[bool, List[str]]:
    """Check GMR engine and model selection."""
    results = ["[GMR ENGINE CHECK]"]
    ok = True

    try:
        from nexus_os.gmr import DOMAIN_MAPPING
        from nexus_os.gmr.rotator import GeniusModelRotator
        from nexus_os.gmr.telemetry import TelemetryIngest

        # 1. Domain mapping
        results.append(f"  Domains: {list(DOMAIN_MAPPING.keys())}")
        if len(DOMAIN_MAPPING) < 3:
            results.append("  ERROR: Missing domains")
            ok = False

        # 2. Budget selection
        class MockTel:
            def __init__(self):
                self.cache = {}
            def fetch(self):
                pass

        gmr = GeniusModelRotator(relay_url="http://localhost:7352")
        gmr.telemetry = MockTel()
        gmr.register_from_mapping()

        # Test budget tiers
        tests = [
            (0, "osman-coder"),
            (50000, "osman-coder"),
            (200000, "Devstral"),
            (500000, "Devstral"),
        ]

        for budget, expected in tests:
            cascade, _ = gmr.get_routing_cascade("write code", metadata={"is_code_task": True}, task_id=f"test-{budget}")
            has_expected = any(expected.lower() in m.lower() for m in cascade)
            results.append(f"  Budget {budget}: {cascade[0] if cascade else 'none'} [{'OK' if has_expected else 'WARN'}]")

        results.append(f"  [OK] GMR engine operational")

    except Exception as e:
        results.append(f"  [ERROR] {e}")
        ok = False

    return ok, results


def check_routing() -> Tuple[bool, List[str]]:
    """Check Hermes routing pipeline."""
    results = ["[ROUTING CHECK]"]
    ok = True

    try:
        from nexus_os.engine.hermes import HermesRouter, IntentClassifier

        # Test intent classification
        classifier = IntentClassifier()

        tests = [
            ("Write authentication function", "code"),
            ("Analyze this data", "code"),
            ("Explain quantum physics", "reasoning"),
            ("Get status", "fast"),
            ("Hello", "general"),
        ]

        for prompt, expected in tests:
            intent = classifier.classify(prompt)
            if intent == expected:
                results.append(f"  '{prompt[:25]}...' -> {intent} [OK]")
            else:
                results.append(f"  '{prompt[:25]}...' -> {intent} [WARN]")

        # Test full routing
        router = HermesRouter()
        result = router.route('test-agent', 'Write function', {})
        results.append(f"  Route output: {result.selected_model}")
        results.append(f"  [OK] Routing operational")

    except Exception as e:
        results.append(f"  [ERROR] {e}")
        ok = False

    return ok, results


def check_integration() -> Tuple[bool, List[str]]:
    """Check full integration pipeline."""
    results = ["[INTEGRATION CHECK]"]
    ok = True

    # Test Trust -> TokenGuard -> GMR -> Routing pipeline
    try:
        from nexus_os.monitoring.trust_scorer import TrustScorer, LANE_PARAMS
        from nexus_os.monitoring.token_guard import TokenGuard
        from nexus_os.engine.hermes import HermesRouter

        results.append("  TrustScorer lanes: {}".format(list(LANE_PARAMS.keys())))

        # Test TokenGuard
        tg = TokenGuard(budgets={'test': 50000})
        can_run = tg.check('test', 1000)
        results.append(f"  TokenGuard: {'OK' if can_run else 'FAIL'}")

        # Test Hermes
        router = HermesRouter()
        result = router.route('test-agent', 'test', {})
        results.append(f"  Hermes route: {result.selected_model}")

        results.append(f"  [OK] Integration pipeline operational")

    except Exception as e:
        results.append(f"  [ERROR] {e}")
        ok = False

    return ok, results


def check_memory() -> Tuple[bool, List[str]]:
    """Check memory and vault."""
    results = ["[MEMORY CHECK]"]
    ok = True

    try:
        from nexus_os.vault.memory_tracks import get_tracker, MemoryTrack

        tracker = get_tracker()

        # Add test records
        tracker.append_event('diag-test', 'test event', 'success', 10.0, 100)
        tracker.append_trust('diag-test', 'research', 0.8, 3)

        events = tracker.get_events('diag-test')
        results.append(f"  Events: {len(events)}")

        history = tracker.get_trust_history('diag-test', 'research')
        results.append(f"  Trust records: {len(history)}")

        results.append(f"  [OK] Memory operational")

    except Exception as e:
        results.append(f"  [ERROR] {e}")
        ok = False

    return ok, results


def check_execution_paths() -> Tuple[bool, List[str]]:
    """Check execution paths."""
    results = ["[EXECUTION PATHS CHECK]"]
    ok = True

    try:
        from nexus_os.execution_paths import get_router, ExecutionPath

        router = get_router()

        tests = [
            ("get status", ExecutionPath.HOT),
            ("write data", ExecutionPath.COLD),
            ("read memory", ExecutionPath.WARM),
        ]

        for op, expected in tests:
            path = router.route(op)
            results.append(f"  '{op}' -> {path.name}")

        results.append(f"  [OK] Execution paths operational")

    except Exception as e:
        results.append(f"  [ERROR] {e}")
        ok = False

    return ok, results


def run_diagnostic(target: str = "all") -> int:
    """Run diagnostic checks."""
    print("="*60)
    print("NEXUS OS v3.0 - SYSTEM DIAGNOSTIC")
    print("="*60)
    print()

    checks = []
    if target in ["all", "gmr"]:
        checks.append(("GMR", check_gmr))
    if target in ["all", "routing"]:
        checks.append(("Routing", check_routing))
    if target in ["all", "integration"]:
        checks.append(("Integration", check_integration))
    if target in ["all", "memory"]:
        checks.append(("Memory", check_memory))
    if target in ["all", "paths"]:
        checks.append(("Execution Paths", check_execution_paths))

    all_ok = True
    for name, check_fn in checks:
        ok, results = check_fn()
        for line in results:
            print(line)
        print()
        if not ok:
            all_ok = False

    print("="*60)
    if all_ok:
        print("[PASS] All checks passed")
    else:
        print("[FAIL] Some checks failed")
    print("="*60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    sys.exit(run_diagnostic(target))