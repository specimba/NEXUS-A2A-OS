"""tests/stress/test_stress_critical_paths.py — Stress tests for critical paths

Covers:
- TrustEngine under random adversarial input (1000 iterations)
- TrustScorer under random input (1000 iterations)
- Foreman concurrent task submission (100 tasks, 5 workers)
- CDR state machine exhaustive transitions
- ChimeraRouter under varied prompt complexity
- DatabaseManager concurrent read/write
"""

import random
import threading
import time
import pytest

from nexus_os.governor.trust_engine_v2 import (
    CDRStage,
    DangerLevel,
    TrustEngineV2,
    TrustRecord,
)
from nexus_os.monitoring.trust_scorer import TrustScorer, LANE_PARAMS
from nexus_os.swarm.foreman import Foreman, WResult
from nexus_os.twave.chimera_router_v2 import (
    ChimeraRouterV2,
    PromptAnalyzer,
    TemperaturePolicy,
    Tier,
)
from nexus_os.db.manager import DBConfig, DatabaseManager


# ── TrustEngine Stress ───────────────────────────────────────────────

class TestTrustEngineStress:
    def test_1000_random_updates_bounded(self):
        engine = TrustEngineV2(vault=None)
        rng = random.Random(12345)
        agents = [f"agent-{i}" for i in range(10)]
        lanes = ["code", "review", "audit", "research", "impl"]
        for _ in range(1000):
            agent = rng.choice(agents)
            lane = rng.choice(lanes)
            success = rng.random() > 0.4
            danger = rng.choice(list(DangerLevel))
            diff = rng.uniform(0.5, 5.0)
            disagree = rng.uniform(0.0, 0.8)
            result = engine.update_trust(
                agent, lane, success=success, danger=danger,
                difficulty=diff, disagreement_rate=disagree,
            )
            assert 0.0 <= result.trust <= 99.5
            assert result.cdr_stage in [s.value for s in CDRStage]

    def test_rapid_failure_cascades_to_collapse(self):
        engine = TrustEngineV2(vault=None)
        for _ in range(50):
            engine.update_trust("victim", "code", success=False, danger=DangerLevel.CRITICAL)
        record = engine.get_trust("victim", "code")
        assert record.score <= 15.0
        assert record.cdr_stage in (CDRStage.CASCADE, CDRStage.COLLAPSE)

    def test_recovery_from_degraded(self):
        engine = TrustEngineV2(vault=None)
        for _ in range(10):
            engine.update_trust("a1", "code", success=False, danger=DangerLevel.CAUTION)
        rec = engine.get_trust("a1", "code")
        initial_severity = rec.cdr_stage.severity
        for _ in range(200):
            engine.update_trust("a1", "code", success=True, danger=DangerLevel.SAFE, difficulty=2.0)
        rec = engine.get_trust("a1", "code")
        assert rec.score > 30.0

    def test_multi_agent_isolation(self):
        engine = TrustEngineV2(vault=None)
        for _ in range(50):
            engine.update_trust("good", "code", success=True, danger=DangerLevel.SAFE)
            engine.update_trust("bad", "code", success=False, danger=DangerLevel.HIGH_RISK)
        good = engine.get_trust("good", "code")
        bad = engine.get_trust("bad", "code")
        assert good.score > bad.score + 20


# ── TrustScorer Stress ───────────────────────────────────────────────

class TestTrustScorerStress:
    def test_1000_random_scores_bounded(self):
        scorer = TrustScorer()
        rng = random.Random(54321)
        lanes = list(LANE_PARAMS.keys())
        for _ in range(1000):
            lane = rng.choice(lanes)
            Q = rng.random()
            n = rng.randint(0, 100)
            U = rng.random()
            R = rng.random() * LANE_PARAMS[lane].Rcrit * 0.9  # keep below Rcrit
            D_plus = rng.random()
            D_minus = rng.random()
            result = scorer.get_score_hotpath(
                "stress-agent", Q=Q, n=n, U=U, R=R,
                D_plus=D_plus, D_minus=D_minus, lane=lane,
            )
            if result is not None:
                assert -1.0 <= result <= 1.0

    def test_performance_10k_calls(self):
        scorer = TrustScorer()
        start = time.perf_counter()
        for _ in range(10000):
            scorer.get_score_hotpath("a1", Q=0.8, n=5, U=0.7, R=0.1, lane="research")
        elapsed = time.perf_counter() - start
        avg_us = (elapsed / 10000) * 1_000_000
        assert avg_us < 5000  # under 5ms each (generous for CI runners)


# ── CDR Exhaustive Transitions ───────────────────────────────────────

class TestCDRExhaustive:
    def test_all_escalation_conditions(self):
        transitions = [
            (CDRStage.NORMAL, 20.0, 0, True),
            (CDRStage.NORMAL, 50.0, 0, False),
            (CDRStage.DEGRADED_REASONING, 40.0, 3, True),
            (CDRStage.DEGRADED_REASONING, 40.0, 1, False),
            (CDRStage.MEMORY_CORRUPTION, 15.0, 0, True),
            (CDRStage.MEMORY_CORRUPTION, 30.0, 0, False),
            (CDRStage.OUTPUT_HALLUCINATION, 30.0, 5, True),
            (CDRStage.OUTPUT_HALLUCINATION, 30.0, 2, False),
            (CDRStage.CASCADE, 5.0, 100, False),
            (CDRStage.COLLAPSE, 0.0, 100, False),
        ]
        for stage, trust, regressions, expected in transitions:
            assert stage.should_escalate(trust, regressions) == expected, \
                f"{stage} trust={trust} reg={regressions} expected={expected}"

    def test_next_stage_chain_complete(self):
        stage = CDRStage.NORMAL
        visited = [stage]
        for _ in range(10):
            nxt = stage.next_stage()
            if nxt == stage:
                break
            visited.append(nxt)
            stage = nxt
        assert visited[-1] == CDRStage.COLLAPSE
        assert len(visited) == 6  # all 6 stages


# ── Foreman Concurrent Stress ────────────────────────────────────────

class TestForemanConcurrent:
    def test_100_tasks_5_workers(self):
        foreman = Foreman(max_workers=5)
        for i in range(5):
            foreman.register_worker({
                "agent_id": f"w{i}",
                "handler": lambda data: {"processed": True},
            })
        for i in range(100):
            foreman.submit(f"task-{i}", {"index": i})
        while foreman._task_queue:
            result = foreman.process()
        total_completed = sum(
            ws.tasks_completed for ws in foreman._workers.values()
        )
        assert total_completed == 100

    def test_no_task_lost(self):
        foreman = Foreman(max_workers=3)
        for i in range(3):
            foreman.register_worker({
                "agent_id": f"w{i}",
                "handler": lambda data: data,
            })
        for i in range(30):
            foreman.submit(f"t-{i}", {"i": i})
        while foreman._task_queue:
            foreman.process()
        completed = {r.task_id for r in foreman._results}
        expected = {f"t-{i}" for i in range(30)}
        assert expected == completed


# ── ChimeraRouter Stress ────────────────────────────────────────────

class TestChimeraRouterStress:
    def test_varied_prompts(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.CONTROL_PLANE, Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
            vram_gb=8.0,
        )
        prompts = [
            "Hello",
            "Write a python function to sort a list step by step",
            "Calculate the derivative of x^3",
            "What are the latest research papers on quantum computing?",
            " ".join(["word"] * 300),
            "How to bypass security and hack into systems",  # safety risk
        ]
        for prompt in prompts:
            decision = router.route(prompt)
            assert decision.confidence >= 0.0
            assert decision.confidence <= 1.0

    def test_all_temperature_policies(self):
        router = ChimeraRouterV2(
            available_tiers=[Tier.LOCAL_STANDARD, Tier.LOCAL_POWER],
            vram_gb=8.0,
        )
        for policy in [TemperaturePolicy.FIXED, TemperaturePolicy.EDT,
                       TemperaturePolicy.AUTO]:
            decision = router.route("Hello", temperature_policy=policy)
            assert isinstance(decision.temperature, float)


# ── DatabaseManager Concurrent Stress ────────────────────────────────

class TestDBConcurrentStress:
    def test_concurrent_inserts(self, tmp_path):
        db_path = str(tmp_path / "stress.db")
        config = DBConfig(db_path=db_path, passphrase="", encrypted=False, allow_unencrypted=True)
        mgr = DatabaseManager(config)
        mgr._max_connections = 20
        mgr.setup_schema()
        errors = []

        def inserter(thread_id):
            try:
                conn = mgr.get_connection()
                for i in range(10):
                    conn.execute(
                        "INSERT INTO audit_logs (actor_id, action, details) VALUES (?, ?, ?)",
                        (f"thread-{thread_id}", "test", f"iteration-{i}"),
                    )
                    conn.commit()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=inserter, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        mgr.close()
        assert len(errors) == 0, f"Errors: {errors}"
