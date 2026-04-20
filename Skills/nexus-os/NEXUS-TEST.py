#!/usr/bin/env python3
"""NEXUS-TEST.py — 8-component validation suite"""
import sys
from pathlib import Path

# Resolve src relative to this file's location
SELF = Path(__file__).parent
SRC = SELF / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

def run_tests():
    tests = []
    try:
        from nexus_os.bridge import sign, verify
        s = sign("sec", "t1", "p")
        assert verify("sec", "t1", "p", s) and not verify("bad", "t1", "p", s)
        tests.append(("Bridge", "PASS"))
    except Exception as e:
        tests.append(("Bridge", f"FAIL:{e}"))
    try:
        from nexus_os.engine import Hermes, Domain
        assert Hermes().classify("write python function") == Domain.CODE
        tests.append(("Engine", "PASS"))
    except Exception as e:
        tests.append(("Engine", f"FAIL:{e}"))
    try:
        from nexus_os.governor import Governor
        assert Governor().check("read file")["allowed"]
        tests.append(("Governor", "PASS"))
    except Exception as e:
        tests.append(("Governor", f"FAIL:{e}"))
    try:
        from nexus_os.vault import Vault, Track
        v = Vault()
        v.store("a1", Track.EVENT, "test", "k1", {"v": 1}, 0.8)
        assert len(v.query("a1")) == 1
        tests.append(("Vault", "PASS"))
    except Exception as e:
        tests.append(("Vault", f"FAIL:{e}"))
    try:
        from nexus_os.gmr import GMR
        assert GMR().select("code task").name == "minimax-m2.7"
        tests.append(("GMR", "PASS"))
    except Exception as e:
        tests.append(("GMR", f"FAIL:{e}"))
    try:
        from nexus_os.swarm import Foreman
        f = Foreman(2)
        f.workers[0].handler = lambda d: {"r": d}
        f.submit("t1", "data")
        r = f.process()
        assert r and r.ok
        tests.append(("Swarm", "PASS"))
    except Exception as e:
        tests.append(("Swarm", f"FAIL:{e}"))
    try:
        from nexus_os.monitoring import TokenGuard
        tg = TokenGuard({"a": 1000})
        assert tg.check("a", 500)
        tg.track("a", 500)
        assert not tg.check("a", 600)
        tests.append(("TokenGuard", "PASS"))
    except Exception as e:
        tests.append(("TokenGuard", f"FAIL:{e}"))
    try:
        from nexus_os.monitoring import TokenTracker, start_tracking, get_usage
        start_tracking(total_tokens=50000)
        TokenTracker.get_instance().record_api_call("test", 100, 50, "qwen3-coder")
        assert get_usage()["used"] > 0
        tests.append(("TokenTracker", "PASS"))
    except Exception as e:
        tests.append(("TokenTracker", f"FAIL:{e}"))

    print("\n" + "═" * 50)
    print("NEXUS OS v3.0 — Test Results")
    print("═" * 50)
    passed = sum(1 for _, r in tests if r == "PASS")
    for n, r in tests:
        print(f"{'✓' if r == 'PASS' else '✗'} {n}: {r}")
    print("═" * 50)
    print(f"Result: {passed}/{len(tests)} passed")
    print("═" * 50)
    return passed == len(tests)

if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)