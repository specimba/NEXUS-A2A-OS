#!/usr/bin/env python3
"""NEXUS OS v3.0 — Complete test suite (P0 + P1 + P2)
Run: python3 Skills/nexus-os/NEXUS-TEST.py"""
import sys
from pathlib import Path

SELF = Path(__file__).parent
SRC = SELF / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))


def run_tests():
    tests = []

    # ── 1. Bridge ─────────────────────────────────────────────────────────────
    try:
        from nexus_os.bridge import (
            sign, verify, BridgeServer, AuthMode, AuthResult,
            JSONRPCDispatcher, JSONRPCRequest,
        )
        # HMAC
        s = sign("sec", "t1", "p")
        assert verify("sec", "t1", "p", s)
        assert not verify("bad", "t1", "p", s)
        # Bearer auth
        bs = BridgeServer(bearer_token="my_secret_token_1234567890abcdef")
        r = bs.authenticate({"authorization": "Bearer my_secret_token_1234567890abcdef"}, "body")
        assert r.ok and r.mode == "bearer", f"bearer fail: {r.mode}"
        assert not bs.authenticate({"authorization": "Bearer wrong"}, "body").ok
        # MCP-OAuth2 PKCE (token >= 32 chars)
        assert bs.authenticate({"authorization": f"Bearer {'a'*64}"}, "body").mode == "mcp_oauth2_pkce"
        # JSON-RPC
        disp = JSONRPCDispatcher()
        disp.register("add", lambda p: p.get("a", 0) + p.get("b", 0))
        rpc = JSONRPCRequest.from_json('{"method":"add","params":{"a":3,"b":4},"id":"r1"}')
        assert disp.dispatch(rpc)["result"] == 7
        tests.append(("Bridge", "PASS"))
    except Exception as e:
        tests.append(("Bridge", f"FAIL:{e}"))

    # ── 2. Engine + P1c ToolDisciplineGate ───────────────────────────────────
    try:
        from nexus_os.engine import Hermes, Domain, ToolDisciplineGate
        h = Hermes()
        assert h.classify("write python function") == Domain.CODE
        assert h.classify("think through this") == Domain.REASON
        assert h.classify("search相关信息") == Domain.RESEARCH
        gate = ToolDisciplineGate()
        # Gate 1: necessity blocks prompts with < 2 tool indicators
        g = gate.gates("What is the capital of France?", "web_search")
        assert g["necessity"]["allowed"] is False, f"FAIL: {g['necessity']}"
        # Gate 1: passes for prompts with 2+ tool indicators
        g2 = gate.gates("read the file and list its contents", "read_file")
        assert g2["necessity"]["allowed"] is True
        assert g2["appropriateness"]["allowed"] is True
        # Gate 2: passes necessity but tool is wrong for domain.
        # "quick read and fetch results from the web" → FAST (has "quick")
        # but uses web_search (not in FAST allowed tools → blocked)
        g3 = gate.gates("quick read and fetch results from the web", "web_search")
        assert g3["necessity"]["allowed"] is True, f"Gate1 should pass: {g3['necessity']}"
        assert g3["appropriateness"]["allowed"] is False, f"Gate2 should fail: {g3['appropriateness']}"
        tests.append(("Engine + P1c ToolGate", "PASS"))
    except Exception as e:
        tests.append(("Engine + P1c ToolGate", f"FAIL:{e}"))

    # ── 3. Governor ────────────────────────────────────────────────────────────
    try:
        from nexus_os.governor import Governor, _LANES, RigorLLMGate, ShieldGemmaGate, ComplianceGate
        from nexus_os.governor import Kaiju, TrustScorer, Scope, Decision, GuardResult
        gov = Governor()
        # P0b: OR-Bench calibrated lanes
        assert _LANES["research"] == (0.35, 7, 0.8), f"research lane wrong: {_LANES['research']}"
        assert _LANES["compliance"] == (0.80, 2, 0.2)
        assert gov.lanes()["review"] == (0.55, 4, 0.6)
        # Kaiju auth
        assert gov.check("read file")["allowed"]
        assert not gov.check("sudo rm -rf everything")["allowed"]
        # P1a: RigorLLM gate
        rg = RigorLLMGate()
        assert rg.check("normal request").passed
        # P1a: ShieldGemma gate
        sg = ShieldGemmaGate()
        r = sg.check("standard request")
        assert hasattr(r, "passed") and hasattr(r, "flags")
        # P2c: ComplianceGate
        cg = ComplianceGate()
        assert cg.check("read file", Scope.PROJECT).passed
        assert not cg.check("sudo rm -rf /", Scope.SYSTEM).passed
        tests.append(("Governor", "PASS"))
    except Exception as e:
        import traceback; traceback.print_exc()
        tests.append(("Governor", f"FAIL:{e}"))

    # ── 4. Vault + P1b (8-channel) + P2a (KV compression) ─────────────────────
    try:
        from nexus_os.vault import Vault, Track, Channel, CompressedContextPacket
        from nexus_os.vault import TEMPORAL_CAUSAL, ONTOLOGICAL
        v = Vault()
        # P1b: 8-channel storage (EVENT, TRUST, CAP, FAIL, GOV already exist)
        v.store("a1", Track.EVENT, "test", "k1", {"v": 1}, 0.8)
        v.store("a1", Track.TRUST, "trust", "t1", {"score": 0.9}, 0.9)
        # New P1b channels
        v.store("a1", TEMPORAL_CAUSAL, "causal", "因果链", {"reason": "decision"}, 0.85, causal_tag="decision_001")
        v.store("a1", ONTOLOGICAL, "ontology", "entity1", {"type": "agent"}, 0.8)
        assert len(v.query("a1")) == 4
        # TEMPORAL_CAUSAL channel query
        causal_q = v.query("a1", TEMPORAL_CAUSAL)
        assert len(causal_q) == 1, f"causal query returned {len(causal_q)}"
        # ONTOLOGICAL channel query
        ont_q = v.query("a1", ONTOLOGICAL)
        assert len(ont_q) == 1
        # P2a: KV compression — Attention-Sink Aware Quantization
        original = " ".join([f"token_{i}" for i in range(200)])
        pkt = CompressedContextPacket.compress(original, anchor_ratio=0.15)
        # Compression ratio: >85% of tokens should be in compressed body
        assert 0.7 < pkt.compression_ratio < 0.95, f"bad compression ratio: {pkt.compression_ratio}"
        # 30 anchor tokens (15% of 200)
        assert len(pkt.anchor_token_ids) == 30, f"anchor count: {len(pkt.anchor_token_ids)}"
        # Metadata preserved
        assert pkt.metadata["n_tokens"] == 200 and pkt.metadata["n_anchors"] == 30
        # Decompress and verify roundtrip (anchor tokens preserved verbatim)
        decompressed = pkt.decompress()
        for a in pkt.metadata.get("_anchors", []):
            assert a in decompressed, f"anchor '{a}' missing from decompressed"
        # Verify anchors were preserved
        assert "token_170" in decompressed and "token_199" in decompressed
        # Serialization roundtrip
        d = pkt.to_dict()
        assert "kv_compressed" in d and "anchor_token_ids" in d
        pkt2 = CompressedContextPacket.from_dict(d)
        assert pkt2.compression_ratio == pkt.compression_ratio
        assert pkt2.anchor_token_ids == pkt.anchor_token_ids
        # Verify roundtrip method
        assert pkt.verify_roundtrip(original)
        tests.append(("Vault + P1b 8ch + P2a KV", "PASS"))
    except Exception as e:
        import traceback; traceback.print_exc()
        tests.append(("Vault + P1b 8ch + P2a KV", f"FAIL:{e}"))

    # ── 5. GMR + P0d (circuit breaker) + P1d (speculative) + P2a (TALE) ───────
    try:
        from nexus_os.gmr import GMR, CircuitState, SpeculativeRouter, TALEstimator
        g = GMR()
        m = g.select("code task")
        assert m.name == "minimax-m2.7"
        # P0d: half-open circuit breaker state machine
        m._circuit = CircuitState.CLOSED; m._failures = 0; m._cooldown = 60.0
        assert m.can_use() is True
        for _ in range(3): m.record_failure()
        assert m._circuit == CircuitState.OPEN and not m.can_use()
        import time; m._open_until = time.time() + 0.1
        time.sleep(0.15)
        assert m.can_use() is True and m._circuit == CircuitState.HALF_OPEN
        m.record_success()
        assert m._circuit == CircuitState.CLOSED and m._cooldown == 60.0
        # HALF_OPEN failure → double cooldown
        for _ in range(3): m.record_failure()
        m._open_until = time.time() + 0.1; time.sleep(0.15)
        assert m.can_use() is True  # HALF_OPEN
        m.record_failure()
        assert m._circuit == CircuitState.OPEN and m._cooldown == 120.0
        # P1d: SpeculativeRouter — descending score order
        router = SpeculativeRouter()
        cands = [m for m in g.route("code", "code")]
        scored = router.pre_score("write a python function", cands)
        scores = [s for _, s in scored]
        assert scores == sorted(scores, reverse=True), "not descending"
        # P2a: TALE estimator
        tale = TALEstimator()
        est = tale.estimate("Write a comprehensive analysis of the codebase with detailed reports")
        assert 0 < est["estimated_tokens"] <= 200000
        assert est["budget"] >= 100
        assert 0 < est["reasoning_efficiency"] <= 1.0
        tale.adjust_after_completion(est["task_id"], int(est["estimated_tokens"] * 0.6))
        tale.adjust_after_completion(est["task_id"], int(est["estimated_tokens"] * 0.9))
        tests.append(("GMR + Circuit + Spec + TALE", "PASS"))
    except Exception as e:
        import traceback; traceback.print_exc()
        tests.append(("GMR + Circuit + Spec + TALE", f"FAIL:{e}"))

    # ── 6. Swarm + P0c (deer-flow) + P2b (auction) ─────────────────────────────
    try:
        from nexus_os.swarm import Foreman, Worker, WStatus, Task, Bid
        f = Foreman(2)
        # P0c: submit returns 8-char task_id
        tid = f.submit("process this", domain="code")
        assert isinstance(tid, str) and len(tid) == 8
        st = f.status()
        assert st["queue_depth"] == 1 and len(st["workers"]) == 2
        # Worker isolated memory
        w0 = f.workers[0]
        called = [False]
        def h(p): called[0] = True; return {"result": p}
        w0.handler = h
        w0.execute(Task(id="test1", prompt="hello"))
        assert called[0] is True
        assert len(w0.memory_snapshot()) == 1
        # P2b: auction bidding — all bids in [0, 1], highest wins
        task = Task(id="auction_test", prompt="code review", domain="code", priority=0.7)
        bids = [w.bid_on(task) for w in f.workers]
        assert len(bids) == 2 and all(isinstance(b, Bid) and 0 <= b.final_bid <= 1.0 for b in bids)
        winner = max(bids, key=lambda b: b.final_bid).worker_id
        assert 0 <= winner < 2
        # Auction formula: (cap*0.4)+(trust*0.3)+((1-load)*0.2)+(spec*0.1)
        for b in bids:
            expected = (b.capability*0.4)+(b.trust*0.3)+((1-b.load)*0.2)+(b.spec_match*0.1)
            assert abs(b.final_bid - expected) < 1e-9, f"bid formula wrong: {b.final_bid} vs {expected}"
        tests.append(("Swarm + deer-flow + auction", "PASS"))
    except Exception as e:
        import traceback; traceback.print_exc()
        tests.append(("Swarm + deer-flow + auction", f"FAIL:{e}"))

    # ── 7. Skillsmith + P1e (auto-register) ──────────────────────────────────
    try:
        from nexus_os.skillsmith import Skillsmith, SkillRecord
        from nexus_os.vault import Vault
        vault = Vault()
        sm = Skillsmith(vault)
        # P1e: Skillsmith auto-register
        # log_outcome stores to vault; register() builds library directly
        sm.register("code_writer", ["python", "code", "write"], "generate_code")
        assert len(sm.library()) >= 1, f"nothing in library: {sm.library()}"
        rec = sm.dispatch("write python function")
        assert rec is not None, "dispatch failed"
        # track failures → no promotion
        for _ in range(3):
            sm.log_outcome("a1", "reason task", success=False, domain="reasoning")
        reason_rec = sm.find_skill("reasoning", min_score=0.6)
        assert reason_rec is None, "failed skill should not be promoted"
        report = sm.report()
        assert "total_skills" in report and "auto_registered" in report
        tests.append(("Skillsmith + P1e", "PASS"))
    except Exception as e:
        import traceback; traceback.print_exc()
        tests.append(("Skillsmith + P1e", f"FAIL:{e}"))

    # ── 8. TokenGuard ───────────────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenGuard
        tg = TokenGuard({"a": 1000})
        assert tg.check("a", 500)
        tg.track("a", 500)
        assert not tg.check("a", 600)
        assert tg.check("a", 400)  # 400 left, 500+400=900 OK
        tests.append(("TokenGuard", "PASS"))
    except Exception as e:
        tests.append(("TokenGuard", f"FAIL:{e}"))

    # ── 9. TokenTracker ───────────────────────────────────────────────────────
    try:
        from nexus_os.monitoring import TokenTracker, start_tracking, get_usage, end_tracking
        start_tracking(total_tokens=50000)
        TokenTracker.get_instance().record_api_call("test", 100, 50, "qwen3-coder")
        usage = get_usage()
        assert usage["used"] > 0 and usage["remaining"] < 50000
        end_tracking()
        tests.append(("TokenTracker", "PASS"))
    except Exception as e:
        tests.append(("TokenTracker", f"FAIL:{e}"))

    # ── Results ────────────────────────────────────────────────────────────────
    print("\n" + "═" * 56)
    print("NEXUS OS v3.0 — Full P0/P1/P2 Test Suite")
    print("═" * 56)
    passed = sum(1 for _, r in tests if r == "PASS")
    for n, r in tests:
        print(f"{'✓' if r == 'PASS' else '✗'} {n}: {r}")
    print("═" * 56)
    print(f"Result: {passed}/{len(tests)} passed")
    print("═" * 56)
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)