#!/usr/bin/env python3
"""NEXUS-TEST.py — 10-component validation suite"""
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

    # ── Engine + P1c ToolDisciplineGate ───────────────────────────────
    try:
        from nexus_os.engine import Hermes, Domain, ToolDisciplineGate
        h = Hermes()
        assert h.classify("write python function") == Domain.CODE
        assert h.classify("think about this") == Domain.REASON

        gate = ToolDisciplineGate()

        # Gate 1 — necessity: plain question blocked (0 tool indicators)
        g1 = gate.necessity_check("What is the capital of France?")
        assert g1["allowed"] is False, f"g1: {g1}"

        # Gate 1 — passes when 2+ tool indicators present
        g2 = gate.necessity_check("read the file and list its contents")
        assert g2["allowed"] is True, f"g2: {g2}"

        # Gate 2 — appropriateness: run_bash_command allowed in REASON domain
        g3 = gate.appropriateness_check("read the file and list its contents", "run_bash_command")
        assert g3["allowed"] is True, f"g3: {g3}"

        # Gate 2 — web_search NOT allowed in CODE domain (only research domain has it)
        g4 = gate.appropriateness_check("write python class", "web_search")
        assert g4["allowed"] is False, f"g4: {g4}"

        # Gate 3 — audit
        g5 = gate.audit_result("read file", "read_file", "file content here")
        assert g5["satisfied"] is True

        g6 = gate.audit_result("read file", "read_file", "")
        assert g6["satisfied"] is False

        # Full pipeline: need=pass + app=pass
        result = gate.gates("read the file and list its contents", "read_file", "content")
        assert result["necessity"]["allowed"] is True, f"full pipeline necessity: {result['necessity']}"
        assert result["audit"]["satisfied"] is True

        tests.append(("Engine + P1c ToolGate", "PASS"))
    except Exception as e:
        tests.append(("Engine + P1c ToolGate", f"FAIL:{e}"))

    # ── Governor ────────────────────────────────────────────────────────
    try:
        from nexus_os.governor import Governor, _LANES
        gov = Governor()
        assert gov.check("read file")["allowed"]
        assert _LANES["research"] == (0.35, 7)
        assert _LANES["compliance"] == (0.80, 2)
        lanes = gov.lanes()
        assert lanes["review"] == (0.55, 4)
        tests.append(("Governor", "PASS"))
    except Exception as e:
        tests.append(("Governor", f"FAIL:{e}"))

    # ── Vault + P1b 8-channel ──────────────────────────────────────────
    try:
        from nexus_os.vault import Vault, Track, Channel
        v = Vault()
        v.store("a1", Track.EVENT, "test", "k1", {"v": 1}, 0.8)
        assert len(v.query("a1")) == 1

        # P1b: 8-channel SuperLocalMemory v2
        v.store_causal("a1", "task failed", "reduce complexity", "evidence123", 0.9)
        v.store_ontology("a1", "LLM", "AI Model", "is-a", 0.85)
        causal_q = v.query_channel("a1", Channel.TEMPORAL_CAUSAL)
        assert len(causal_q) == 1
        ont_q = v.query_channel("a1", Channel.ONTOLOGICAL)
        assert len(ont_q) == 1
        assert ont_q[0]["val"]["entity"] == "LLM"

        tests.append(("Vault + P1b 8ch", "PASS"))
    except Exception as e:
        tests.append(("Vault + P1b 8ch", f"FAIL:{e}"))

    # ── GMR + P0d Circuit Breaker ─────────────────────────────────────
    try:
        from nexus_os.gmr import GMR, CircuitState
        import time
        g = GMR()
        m = g.select("code task")
        assert m.name == "minimax-m2.7"
        m._circuit = CircuitState.CLOSED
        m._failures = 0
        assert m.can_use() is True
        m.record_failure(); m.record_failure(); m.record_failure()
        assert m._circuit == CircuitState.OPEN
        assert m.can_use() is False
        m._open_until = time.time() + 0.1
        time.sleep(0.15)
        assert m.can_use() is True
        assert m._circuit == CircuitState.HALF_OPEN
        m.record_success()
        assert m._circuit == CircuitState.CLOSED
        assert m._cooldown == 60.0
        m.record_failure(); m.record_failure(); m.record_failure()
        m._open_until = time.time() + 0.1
        time.sleep(0.15)
        assert m.can_use() is True
        m.record_failure()
        assert m._circuit == CircuitState.OPEN
        assert m._cooldown == 120.0
        report = g.circuit_report()
        assert len(report) == 5
        tests.append(("GMR + P0d Circuit", "PASS"))
    except Exception as e:
        tests.append(("GMR + P0d Circuit", f"FAIL:{e}"))

    # ── Swarm + P0c deer-flow ───────────────────────────────────────────
    try:
        from nexus_os.swarm import Foreman, Worker, WStatus, Task
        f = Foreman(2)
        tid = f.submit("process this", domain="code")
        assert isinstance(tid, str) and len(tid) == 8
        st = f.status()
        assert st["queue_depth"] == 1
        assert len(st["workers"]) == 2
        w0 = f.workers[0]
        called = [False]
        def h(p): called[0] = True; return {"result": p}
        w0.handler = h
        w0.execute(Task(id="test1", prompt="hello"))
        assert called[0] is True
        snap = w0.memory_snapshot()
        assert len(snap) == 1
        assert snap[0]["ok"] is True
        f.collect()
        tests.append(("Swarm + P0c deer-flow", "PASS"))
    except Exception as e:
        tests.append(("Swarm + P0c deer-flow", f"FAIL:{e}"))

    # ── Skillsmith + P1e auto-register ────────────────────────────────
    try:
        from nexus_os.skillsmith import Skillsmith, SkillRecord
        from nexus_os.vault import Vault as VaultBase, Track
        vault = VaultBase()
        sm = Skillsmith(vault)
        assert sm.dispatch("write python code") is None
        r = sm.register("code_writer", ["python", "code", "write"], "python_template")
        assert r.name == "code_writer"
        hit = sm.dispatch("write python function")
        assert hit is not None
        assert hit.name == "code_writer"
        sm.log_outcome("agent1", "write python code", True, "code")
        sm.log_outcome("agent1", "write python code", True, "code")
        sm.log_outcome("agent1", "write python code", True, "code")
        assert any(s.name == "code_writer" for s in sm.library()), "skill not promoted"
        tests.append(("Skillsmith + P1e", "PASS"))
    except Exception as e:
        tests.append(("Skillsmith + P1e", f"FAIL:{e}"))

    # ── TokenGuard ─────────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenGuard
        tg = TokenGuard({"a": 1000})
        assert tg.check("a", 500)
        tg.track("a", 500)
        assert not tg.check("a", 600)
        tests.append(("TokenGuard", "PASS"))
    except Exception as e:
        tests.append(("TokenGuard", f"FAIL:{e}"))

    # ── TokenTracker ───────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenTracker, start_tracking, get_usage, end_tracking
        start_tracking(total_tokens=50000)
        TokenTracker.get_instance().record_api_call("test", 100, 50, "qwen3-coder")
        assert get_usage()["used"] > 0
        end_tracking()
        tests.append(("TokenTracker", "PASS"))
    except Exception as e:
        tests.append(("TokenTracker", f"FAIL:{e}"))

    # ── Print results ─────────────────────────────────────────────────
    print("\n" + "=" * 54)
    print("NEXUS OS v3.0 — Enhanced Test Results")
    print("=" * 54)
    passed = sum(1 for _, r in tests if r == "PASS")
    for n, r in tests:
        print(f"{'✓' if r == 'PASS' else '✗'} {n}: {r}")
    print("=" * 54)
    print(f"Result: {passed}/{len(tests)} passed")
    print("=" * 54)
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)