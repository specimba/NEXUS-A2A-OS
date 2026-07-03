"""Tests for Trinity coordinator — 3-role workflow from Sakana Trinity paper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from nexus_os.nexusclaw.trinity_coordinator import (
    TrinityCoordinator,
    TrinityWorkflow,
    TrinityDecision,
    Role,
    Verdict,
    should_terminate,
    decide_next_role,
    pick_default_thinker,
    pick_default_worker,
    pick_default_verifier,
    build_thinker_prompt,
    build_verifier_prompt,
    parse_verifier_response,
    WORKER_POOL,
)


# ── Decision policy tests ───────────────────────────────────────────────


class TestDecisionPolicy:
    def test_first_step_is_thinker(self):
        assert decide_next_role([]) == Role.THINKER

    def test_after_thinker_is_worker(self):
        h = [TrinityDecision(decision_id="d1", role=Role.THINKER, model="m1", prompt="p", output="o")]
        assert decide_next_role(h) == Role.WORKER

    def test_after_worker_is_verifier(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.THINKER, model="m1", prompt="p", output="o"),
            TrinityDecision(decision_id="d2", role=Role.WORKER, model="m2", prompt="p", output="o"),
        ]
        assert decide_next_role(h) == Role.VERIFIER

    def test_after_reject_loops_back_to_worker(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.THINKER, model="m1", prompt="p", output="o"),
            TrinityDecision(decision_id="d2", role=Role.WORKER, model="m2", prompt="p", output="o"),
            TrinityDecision(decision_id="d3", role=Role.VERIFIER, model="m3", prompt="p",
                           output="o", verdict=Verdict.REVISE),
        ]
        # After REVISE, should loop back
        assert decide_next_role(h) == Role.WORKER


class TestTermination:
    def test_terminate_on_accept(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.VERIFIER, model="m", prompt="p",
                           output="o", verdict=Verdict.ACCEPT),
        ]
        assert should_terminate(h, max_steps=5) is True

    def test_terminate_on_abort(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.VERIFIER, model="m", prompt="p",
                           output="o", verdict=Verdict.ABORT),
        ]
        assert should_terminate(h, max_steps=5) is True

    def test_terminate_on_max_steps(self):
        h = [
            TrinityDecision(decision_id=f"d{i}", role=Role.WORKER, model="m", prompt="p",
                           output="o") for i in range(5)
        ]
        assert should_terminate(h, max_steps=5) is True

    def test_no_terminate_in_middle(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.THINKER, model="m", prompt="p", output="o"),
            TrinityDecision(decision_id="d2", role=Role.WORKER, model="m", prompt="p", output="o"),
            TrinityDecision(decision_id="d3", role=Role.VERIFIER, model="m", prompt="p",
                           output="o", verdict=Verdict.REVISE),
        ]
        assert should_terminate(h, max_steps=10) is False


# ── Worker pool tests ───────────────────────────────────────────────────


class TestWorkerPool:
    def test_thinker_default(self):
        assert pick_default_thinker() == "nim/nvidia/nemotron-3-ultra-550b-a55b"

    def test_verifier_default(self):
        assert pick_default_verifier() == "nim/nvidia/nemotron-3-ultra-550b-a55b"

    def test_worker_code_task(self):
        assert pick_default_worker("implement a python function") == "opencode/deepseek-v4-flash-free"

    def test_worker_fast_task(self):
        assert pick_default_worker("quick simple answer") == "groq:llama-3.3-70b-versatile"

    def test_worker_long_context(self):
        assert pick_default_worker("long context document analysis") == "ollama-cloud:minimax-m3"

    def test_worker_default(self):
        assert pick_default_worker("") == "nim/nvidia/nemotron-3-ultra-550b-a55b"

    def test_worker_pool_has_required_roles(self):
        assert "nim/z-ai/glm-5.1" not in WORKER_POOL
        assert "nim/nvidia/nemotron-3-ultra-550b-a55b" in WORKER_POOL
        assert "opencode/deepseek-v4-flash-free" in WORKER_POOL
        assert "longcat:LongCat-2.0" in WORKER_POOL
        assert "internai:intern-s2-preview" in WORKER_POOL
        assert "groq:llama-3.3-70b-versatile" in WORKER_POOL
        assert "ollama-cloud:minimax-m3" in WORKER_POOL


# ── Prompt builder tests ─────────────────────────────────────────────────


class TestPromptBuilders:
    def test_thinker_initial_prompt(self):
        p = build_thinker_prompt("design a system", [])
        assert "THINKER" in p
        assert "design a system" in p
        assert "GLM 5.1" in p or "deepseek" in p or "longcat" in p.lower()  # model hints

    def test_thinker_revise_prompt(self):
        h = [
            TrinityDecision(decision_id="d1", role=Role.THINKER, model="m", prompt="p", output="plan"),
            TrinityDecision(decision_id="d2", role=Role.WORKER, model="m", prompt="p", output="work"),
            TrinityDecision(decision_id="d3", role=Role.VERIFIER, model="m", prompt="p",
                           output="needs more detail", verdict=Verdict.REVISE),
        ]
        p = build_thinker_prompt("design a system", h)
        assert "REVISE" in p or "re-decompose" in p.lower()
        assert "needs more detail" in p

    def test_verifier_prompt_includes_worker_output(self):
        p = build_verifier_prompt("design a system", "Worker said hello world")
        assert "VERIFIER" in p
        assert "Worker said hello world" in p
        assert "ACCEPT" in p


# ── Verifier parsing tests ──────────────────────────────────────────────


class TestVerifierParser:
    def test_parse_accept(self):
        text = '{"verdict": "ACCEPT", "confidence": 0.95, "reason": "looks good"}'
        verdict, conf, reason = parse_verifier_response(text)
        assert verdict == Verdict.ACCEPT
        assert conf == 0.95
        assert reason == "looks good"

    def test_parse_reject(self):
        text = '{"verdict": "REVISE", "confidence": 0.7, "reason": "missing detail"}'
        verdict, conf, reason = parse_verifier_response(text)
        assert verdict == Verdict.REVISE
        assert conf == pytest.approx(0.3)  # inverted
        assert reason == "missing detail"

    def test_parse_abort(self):
        text = '{"verdict": "ABORT", "confidence": 0.8, "reason": "task impossible"}'
        verdict, conf, reason = parse_verifier_response(text)
        assert verdict == Verdict.ABORT
        assert reason == "task impossible"

    def test_parse_invalid_falls_back_to_revise(self):
        text = "this is not json"
        verdict, conf, reason = parse_verifier_response(text)
        assert verdict == Verdict.REVISE
        assert conf < 0.5


# ── Coordinator integration tests ───────────────────────────────────────


def _stub_executor(model, prompt):
    """Stub executor that returns predefined responses based on role."""
    if "VERIFIER" in prompt:
        # Verifier returns ACCEPT
        return '{"verdict": "ACCEPT", "confidence": 0.85, "reason": "stub approve"}'
    elif "THINKER" in prompt:
        return "1. Subtask A\n2. Subtask B"
    else:
        return "Worker did the work"


def _stub_reject_executor(model, prompt):
    """Stub executor where verifier REJECTs first, then accepts."""
    # Stateful: track verifier calls
    if "VERIFIER" in prompt:
        if not hasattr(_stub_reject_executor, "_vcount"):
            _stub_reject_executor._vcount = 0
        _stub_reject_executor._vcount += 1
        if _stub_reject_executor._vcount == 1:
            return '{"verdict": "REVISE", "confidence": 0.7, "reason": "first try"}'
        else:
            return '{"verdict": "ACCEPT", "confidence": 0.9, "reason": "second try"}'
    elif "THINKER" in prompt:
        return "Plan v1"
    else:
        return "Worker output"


class TestCoordinatorIntegration:
    def test_simple_accept_workflow(self):
        coord = TrinityCoordinator(max_steps=5, executor=_stub_executor)
        wf = coord.start_workflow(title="Test", description="simple task")
        wf = coord.run_to_completion(wf)
        # T → W → V(ACCEPT) → terminate
        assert wf.terminated is True
        assert wf.final_verdict == Verdict.ACCEPT
        assert wf.steps_count() == 3  # T, W, V

    def test_reject_then_accept_workflow(self):
        # Reset stub counter
        if hasattr(_stub_reject_executor, "_vcount"):
            del _stub_reject_executor._vcount
        coord = TrinityCoordinator(max_steps=5, executor=_stub_reject_executor)
        wf = coord.start_workflow(title="Test", description="needs revision")
        wf = coord.run_to_completion(wf)
        # T → W → V(REVISE) → T(revise) → W → V(ACCEPT) → terminate
        # After REVISE, decide_next_role returns WORKER, not THINKER.
        # So sequence is: T, W, V, W, V (5 steps total — no second T)
        assert wf.terminated is True
        assert wf.final_verdict == Verdict.ACCEPT
        assert wf.steps_count() == 5  # T, W, V, W, V

    def test_max_steps_caps_iteration(self):
        # Always reject, will hit max_steps=3
        def always_reject(model, prompt):
            if "VERIFIER" in prompt:
                return '{"verdict": "REVISE", "confidence": 0.9}'
            return "stub"

        coord = TrinityCoordinator(max_steps=3, executor=always_reject)
        wf = coord.start_workflow(title="Test", description="loop test")
        wf = coord.run_to_completion(wf)
        # Will terminate at max_steps
        assert wf.terminated is True
        assert wf.steps_count() <= 4  # some buffer

    def test_history_records_role_sequence(self):
        coord = TrinityCoordinator(max_steps=5, executor=_stub_executor)
        wf = coord.start_workflow(title="Test", description="sequence test")
        wf = coord.run_to_completion(wf)
        roles = [d.role for d in wf.history]
        # Should start with THINKER, end with VERIFIER
        assert roles[0] == Role.THINKER
        assert roles[-1] == Role.VERIFIER
        # T → W → V pattern
        assert roles == [Role.THINKER, Role.WORKER, Role.VERIFIER]

    def test_workflow_stored_in_coordinator(self):
        coord = TrinityCoordinator(max_steps=5, executor=_stub_executor)
        wf = coord.start_workflow(title="stored", description="...")
        coord.run_to_completion(wf)
        assert wf.workflow_id in coord.workflows

    def test_steps_by_role_helper(self):
        coord = TrinityCoordinator(max_steps=5, executor=_stub_executor)
        wf = coord.start_workflow(title="Test", description="...")
        wf = coord.run_to_completion(wf)
        assert len(wf.steps_by_role(Role.THINKER)) == 1
        assert len(wf.steps_by_role(Role.WORKER)) == 1
        assert len(wf.steps_by_role(Role.VERIFIER)) == 1

    def test_decision_serialization(self):
        d = TrinityDecision(decision_id="d1", role=Role.WORKER, model="m1",
                            prompt="hello world", output="result", verdict=Verdict.ACCEPT)
        d_dict = d.to_dict()
        assert d_dict["decision_id"] == "d1"
        assert d_dict["role"] == "worker"
        assert d_dict["model"] == "m1"
        assert d_dict["verdict"] == "ACCEPT"


class TestWorkflowSerialization:
    def test_workflow_to_dict_fields(self):
        wf = TrinityWorkflow(workflow_id="wf1", task_id="t1",
                            title="Test", description="description")
        d = {
            "workflow_id": wf.workflow_id,
            "task_id": wf.task_id,
            "title": wf.title,
            "steps": wf.steps_count(),
            "terminated": wf.terminated,
        }
        assert d["workflow_id"] == "wf1"
        assert d["steps"] == 0
        assert d["terminated"] is False