#!/usr/bin/env python3
"""NEXUS-TEST.py — 8-component validation suite + P0b/P0c/P0d coverage"""
import sys
from pathlib import Path

SELF = Path(__file__).parent
SRC = SELF / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))


def run_tests():
    tests = []

    # ── Bridge ──────────────────────────────────────────────────────────
    try:
        from nexus_os.bridge import sign, verify
        s = sign("sec", "t1", "p")
        assert verify("sec", "t1", "p", s) and not verify("bad", "t1", "p", s)
        tests.append(("Bridge", "PASS"))
    except Exception as e:
        tests.append(("Bridge", f"FAIL:{e}"))

    # ── Engine ──────────────────────────────────────────────────────────
    try:
        from nexus_os.engine import Hermes, Domain
        assert Hermes().classify("write python function") == Domain.CODE
        tests.append(("Engine", "PASS"))
    except Exception as e:
        tests.append(("Engine", f"FAIL:{e}"))

    # ── Governor ────────────────────────────────────────────────────────
    try:
        from nexus_os.governor import Governor, _LANES
        gov = Governor()
        assert gov.check("read file")["allowed"]
        # P0b: verify calibrated lane thresholds
        assert _LANES["research"] == (0.35, 7), f"research lane wrong: {_LANES['research']}"
        assert _LANES["compliance"] == (0.80, 2), "compliance lane missing"
        lanes = gov.lanes()
        assert lanes["review"] == (0.55, 4), f"review lane wrong: {lanes['review']}"
        tests.append(("Governor", "PASS"))
    except Exception as e:
        tests.append(("Governor", f"FAIL:{e}"))

    # ── Vault ───────────────────────────────────────────────────────────
    try:
        from nexus_os.vault import Vault, Track
        v = Vault()
        v.store("a1", Track.EVENT, "test", "k1", {"v": 1}, 0.8)
        assert len(v.query("a1")) == 1
        tests.append(("Vault", "PASS"))
    except Exception as e:
        tests.append(("Vault", f"FAIL:{e}"))

    # ── GMR + P0d Circuit Breaker ───────────────────────────────────────
    try:
        from nexus_os.gmr import GMR, CircuitState
        g = GMR()
        m = g.select("code task")
        assert m.name == "minimax-m2.7"
        # P0d: test half-open circuit breaker
        m._circuit = CircuitState.CLOSED
        m._failures = 0
        assert m.can_use() is True
        m.record_failure()
        m.record_failure()
        m.record_failure()
        assert m._circuit == CircuitState.OPEN
        assert m.can_use() is False
        # Wait for cooldown to expire (set to 0.1s for test)
        import time
        m._open_until = time.time() + 0.1
        time.sleep(0.15)
        assert m.can_use() is True
        assert m._circuit == CircuitState.HALF_OPEN
        m.record_success()
        assert m._circuit == CircuitState.CLOSED
        assert m._cooldown == 60.0
        # Test double cooldown on HALF_OPEN failure
        m.record_failure()
        m.record_failure()
        m.record_failure()
        m._open_until = time.time() + 0.1
        time.sleep(0.15)
        assert m.can_use() is True  # now HALF_OPEN
        m.record_failure()           # probe fails → doubles
        assert m._circuit == CircuitState.OPEN
        assert m._cooldown == 120.0
        # Report
        report = g.circuit_report()
        assert len(report) == 5
        tests.append(("GMR + CircuitBreaker", "PASS"))
    except Exception as e:
        tests.append(("GMR + CircuitBreaker", f"FAIL:{e}"))

    # ── Swarm + P0c deer-flow harness ───────────────────────────────────
    try:
        from nexus_os.swarm import Foreman, Worker, WStatus, Task
        f = Foreman(2)
        # P0c: submit returns task_id
        tid = f.submit("process this", domain="code")
        assert isinstance(tid, str) and len(tid) == 8
        # Status check
        st = f.status()
        assert st["queue_depth"] == 1
        assert len(st["workers"]) == 2
        # Worker isolated memory
        w0 = f.workers[0]
        handler_call = [False]
        def h(p): handler_call[0] = True; return {"result": p}
        w0.handler = h
        w0.execute(Task(id="test1", prompt="hello"))
        assert handler_call[0] is True
        snap = w0.memory_snapshot()
        assert len(snap) == 1
        assert snap[0]["ok"] is True
        # Collect pattern
        results = f.collect()
        tests.append(("Swarm + deer-flow", "PASS"))
    except Exception as e:
        tests.append(("Swarm + deer-flow", f"FAIL:{e}"))

    # ── TokenGuard ──────────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenGuard
        tg = TokenGuard({"a": 1000})
        assert tg.check("a", 500)
        tg.track("a", 500)
        assert not tg.check("a", 600)
        tests.append(("TokenGuard", "PASS"))
    except Exception as e:
        tests.append(("TokenGuard", f"FAIL:{e}"))

    # ── TokenTracker ────────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenTracker, start_tracking, get_usage, end_tracking
        start_tracking(total_tokens=50000)
        TokenTracker.get_instance().record_api_call("test", 100, 50, "qwen3-coder")
        assert get_usage()["used"] > 0
        end_tracking()
        tests.append(("TokenTracker", "PASS"))
    except Exception as e:
        tests.append(("TokenTracker", f"FAIL:{e}"))

    # ── Print results ────────────────────────────────────────────────────
    print("\n" + "═" * 54)
    print("NEXUS OS v3.0 — P0b/P0c/P0d Enhanced Test Results")
    print("═" * 54)
    passed = sum(1 for _, r in tests if r == "PASS")
    for n, r in tests:
        print(f"{'✓' if r == 'PASS' else '✗'} {n}: {r}")
    print("═" * 54)
    print(f"Result: {passed}/{len(tests)} passed")
    print("═" * 54)
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)
