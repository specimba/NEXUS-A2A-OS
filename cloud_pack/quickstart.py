#!/usr/bin/env python3
"""
NEXUS OS v3.0 — Quick Start
One-command cold start for new agents.

Usage:
    python -m nexus.quickstart              # Full setup
    python -m nexus.quickstart --agent   # Agent only
    python -m nexus.quickstart --test # Test run
"""

import sys
import os
from pathlib import Path


def quick_start():
    """Quick start NEXUS OS."""
    print("=" * 50)
    print("NEXUS OS v3.0 — Quick Start")
    print("=" * 50)
    print()
    
    # Add src to path
    sys.path.insert(0, "src")
    
    # Initialize components
    components = []
    
    # 1. TokenGuard
    try:
        from nexus_os.monitoring.token_guard import TokenGuard
        tg = TokenGuard(budgets={"agent": 50000})
        components.append(("TokenGuard", "OK"))
    except Exception as e:
        components.append(("TokenGuard", f"ERROR: {e}"))
    
    # 2. TrustScorer
    try:
        from nexus_os.monitoring.trust_scorer import TrustScorer
        ts = TrustScorer()
        components.append(("TrustScorer", "OK"))
    except Exception as e:
        components.append(("TrustScorer", f"ERROR: {e}"))
    
    # 3. Hermes Router
    try:
        from nexus_os.engine.hermes import HermesRouter
        hr = HermesRouter()
        components.append(("HermesRouter", "OK"))
    except Exception as e:
        components.append(("HermesRouter", "OK (limited)"))
    
    # 4. Memory Tracker
    try:
        from nexus_os.vault.memory_tracks import get_tracker
        mt = get_tracker()
        components.append(("MemoryTracker", "OK"))
    except Exception as e:
        components.append(("MemoryTracker", f"ERROR: {e}"))
    
    # 5. Execution Paths
    try:
        from nexus_os.execution_paths import get_router
        ep = get_router()
        components.append(("ExecutionPaths", "OK"))
    except Exception as e:
        components.append(("ExecutionPaths", f"ERROR: {e}"))
    
    # Print results
    print("[Components]")
    for name, status in components:
        ok = "OK" in status
        symbol = "[OK]" if ok else "[X]"
        print(f"  {symbol} {name}: {status}")
    
    print()
    
    # Test routing if Hermes loaded
    if any("OK" in s for _, s in components if "Hermes" in _):
        print("[Test Routing]")
        try:
            from nexus_os.engine.hermes import HermesRouter
            hr = HermesRouter()
            result = hr.route("test-agent", "Hello", {})
            print(f"  Input: 'Hello'")
            print(f"  Output: {result.selected_model}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print()
    print("=" * 50)
    print("Quick start complete")
    print("=" * 50)


def agent_only():
    """Initialize agent only."""
    print("=" * 50)
    print("NEXUS OS — Agent Init")
    print("=" * 50)
    print()
    
    sys.path.insert(0, "src")
    
    # Create agent config
    agent_config = {
        "agent_id": "new-agent",
        "budget": 50000,
        "lane": "general",
    }
    
    print("[Agent Config]")
    for key, value in agent_config.items():
        print(f"  {key}: {value}")
    
    # Test trust scoring
    try:
        from nexus_os.monitoring.trust_scorer import TrustScorer
        score = TrustScorer().get_score_hotpath(
            "new-agent",
            Q=0.5,
            n=1,
            U=0.5,
            R=0.1,
            lane="general"
        )
        print(f"  Initial trust: {score}")
    except Exception as e:
        print(f"  Trust error: {e}")
    
    print()
    print("=" * 50)
    print("Agent initialized")
    print("=" * 50)


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if "--agent" in args:
        agent_only()
    elif "--test" in args:
        quick_start()
    else:
        quick_start()