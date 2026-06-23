"""Tests for NEXUS Stress Lab framework."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.stress.stress_lab import (
    ScenarioType,
    TeamMode,
    StressScenario,
    ScenarioResult,
    StressReport,
    RedScenarioBank,
    BlueScenarioBank,
    PurpleScenarioBank,
    StressLab,
    compute_report,
    print_report,
)


class TestTypes:
    def test_scenario_type_values(self):
        assert ScenarioType.JAILBREAK.value == "jailbreak"
        assert ScenarioType.INJECTION.value == "injection"
        assert ScenarioType.GRADUAL_ESCALATION.value == "gradual_escalation"
        assert ScenarioType.BEHAVIOR_CONTROL.value == "behavior_control"
        assert ScenarioType.OVER_REFUSAL.value == "over_refusal"

    def test_team_mode_values(self):
        assert TeamMode.RED.value == "red"
        assert TeamMode.BLUE.value == "blue"
        assert TeamMode.PURPLE.value == "purple"


class TestRedScenarioBank:
    def test_build_returns_correct_count(self):
        scenarios = RedScenarioBank.build("dangerous", 7)
        assert len(scenarios) == 7

    def test_build_all_red(self):
        scenarios = RedScenarioBank.build("dangerous", 10)
        assert all(s.team == TeamMode.RED for s in scenarios)

    def test_build_all_jailbreak(self):
        scenarios = RedScenarioBank.build("dangerous", 5)
        assert all(s.scenario_type == ScenarioType.JAILBREAK for s in scenarios)

    def test_build_difficulty_varied(self):
        scenarios = RedScenarioBank.build("dangerous", 20)
        difficulties = {s.difficulty for s in scenarios}
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties

    def test_build_query_contains_topic(self):
        scenarios = RedScenarioBank.build("cybersecurity", 3)
        for s in scenarios:
            assert "cybersecurity" in s.query

    def test_build_injection_returns_correct_count(self):
        scenarios = RedScenarioBank.build_injection(6)
        assert len(scenarios) == 6

    def test_build_injection_types(self):
        scenarios = RedScenarioBank.build_injection(5)
        assert all(s.scenario_type == ScenarioType.INJECTION for s in scenarios)

    def test_build_injection_target_governor(self):
        scenarios = RedScenarioBank.build_injection(3)
        assert all(s.target_system == "governor/mcp" for s in scenarios)

    def test_build_escalation_has_steps(self):
        scenarios = RedScenarioBank.build_escalation()
        assert len(scenarios) == 5
        assert all(s.scenario_type == ScenarioType.GRADUAL_ESCALATION for s in scenarios)

    def test_escalation_increasing_difficulty(self):
        scenarios = RedScenarioBank.build_escalation()
        queries = [s.query for s in scenarios]
        assert len(queries) > 1  # multiple steps


class TestBlueScenarioBank:
    def test_build_restore_returns_correct_count(self):
        scenarios = BlueScenarioBank.build_restore(4)
        assert len(scenarios) == 4

    def test_build_restore_type(self):
        scenarios = BlueScenarioBank.build_restore(3)
        assert all(s.scenario_type == ScenarioType.REFUSAL_RESTORE for s in scenarios)

    def test_build_restore_all_blue(self):
        scenarios = BlueScenarioBank.build_restore(5)
        assert all(s.team == TeamMode.BLUE for s in scenarios)

    def test_build_restore_safe_queries(self):
        scenarios = BlueScenarioBank.build_restore(5)
        assert all(len(s.query) > 10 for s in scenarios)
        assert all(s.expected_guard_response == "allowed" for s in scenarios)

    def test_build_restore_expected_allowed(self):
        scenarios = BlueScenarioBank.build_restore(3)
        assert all(s.expected_guard_response == "allowed" for s in scenarios)

    def test_build_over_refusal_size(self):
        scenarios = BlueScenarioBank.build_over_refusal()
        assert len(scenarios) == 3

    def test_build_over_refusal_type(self):
        scenarios = BlueScenarioBank.build_over_refusal()
        assert all(s.scenario_type == ScenarioType.OVER_REFUSAL for s in scenarios)

    def test_build_over_refusal_expected_allowed(self):
        scenarios = BlueScenarioBank.build_over_refusal()
        assert all(s.expected_guard_response == "allowed" for s in scenarios)


class TestPurpleScenarioBank:
    def test_build_combined_mix(self):
        scenarios = PurpleScenarioBank.build_combined(12)
        teams = {s.team for s in scenarios}
        assert TeamMode.RED in teams
        assert TeamMode.BLUE in teams

    def test_build_combined_respects_count(self):
        scenarios = PurpleScenarioBank.build_combined(8)
        assert len(scenarios) == 8


class TestStressLab:
    class DummyClient:
        def __init__(self, response="I cannot help with that."):
            self.response = response
        def generate(self, prompt, **kw):
            return self.response

    def test_run_returns_matching_count(self):
        scenarios = RedScenarioBank.build("dangerous", 3)
        lab = StressLab(self.DummyClient())
        results = lab.run(scenarios, quiet=True)
        assert len(results) == 3

    def test_run_guard_triggered_on_refusal(self):
        scenarios = RedScenarioBank.build("dangerous", 1)
        lab = StressLab(self.DummyClient("I'm sorry, I can't help with that."))
        results = lab.run(scenarios, quiet=True)
        assert results[0].guard_triggered

    def test_run_bypass_on_compliance(self):
        scenarios = RedScenarioBank.build("dangerous", 1)
        lab = StressLab(self.DummyClient("Sure, here is how to make a bomb: ..."))
        results = lab.run(scenarios, quiet=True)
        assert results[0].bypassed

    def test_run_over_refusal_on_blue(self):
        scenarios = BlueScenarioBank.build_restore(1)
        lab = StressLab(self.DummyClient("I cannot answer that."))
        results = lab.run(scenarios, quiet=True)
        assert results[0].over_refused

    def test_run_no_over_refusal_on_red(self):
        scenarios = RedScenarioBank.build("dangerous", 1)
        lab = StressLab(self.DummyClient("I cannot answer that."))
        results = lab.run(scenarios, quiet=True)
        assert not results[0].over_refused  # over_refusal only flagged for blue types

    def test_run_handles_error(self):
        class FailingClient:
            def generate(self, prompt, **kw):
                raise RuntimeError("API down")
        lab = StressLab(FailingClient())
        results = lab.run(RedScenarioBank.build("dangerous", 1), quiet=True)
        assert results[0].guard_triggered is False  # ERROR response is not a refusal signal

    def test_run_latency_recorded(self):
        lab = StressLab(self.DummyClient())
        results = lab.run(RedScenarioBank.build("dangerous", 2), quiet=True)
        for r in results:
            assert r.latency_ms >= 0

    def test_timestamp_is_iso(self):
        lab = StressLab(self.DummyClient())
        results = lab.run(RedScenarioBank.build("dangerous", 1), quiet=True)
        assert "T" in results[0].timestamp  # ISO format

    def test_metadata_preserved(self):
        scenarios = RedScenarioBank.build("dangerous", 1)
        lab = StressLab(self.DummyClient())
        results = lab.run(scenarios, quiet=True)
        assert "template" in results[0].metadata

    def test_seed_produces_deterministic_results(self):
        s1 = RedScenarioBank.build("dangerous", 20)
        s2 = RedScenarioBank.build("dangerous", 20)
        q1 = [s.query for s in s1]
        q2 = [s.query for s in s2]
        assert q1 == q2  # same seed = same templates


class TestComputeReport:
    def test_empty_results(self):
        report = compute_report(TeamMode.RED, [])
        assert report.scenario_count == 0
        assert report.guard_rate == 0.0

    def test_all_bypassed(self):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "query", "Sure, here you go", False, True, False, 100, "now"),
            ScenarioResult("r2", "jailbreak", "red", "query", "Absolutely", False, True, False, 100, "now"),
        ]
        report = compute_report(TeamMode.RED, results)
        assert report.bypass_rate == 1.0
        assert report.bypassed == 2

    def test_all_guarded(self):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "query", "I cannot", True, False, False, 100, "now"),
            ScenarioResult("r2", "jailbreak", "red", "query", "Sorry, no", True, False, False, 100, "now"),
        ]
        report = compute_report(TeamMode.RED, results)
        assert report.guard_rate == 1.0
        assert report.guard_triggered == 2

    def test_mixed_results(self):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "query", "I cannot", True, False, False, 100, "now"),
            ScenarioResult("r2", "jailbreak", "red", "query", "Sure, here", False, True, False, 100, "now"),
            ScenarioResult("b1", "refusal_restore", "blue", "query", "I cannot", True, False, True, 100, "now"),
        ]
        report = compute_report(TeamMode.PURPLE, results)
        assert report.scenario_count == 3
        assert report.bypass_rate == 1/3
        assert report.over_refusal_rate == 1/3

    def test_per_type_breakdown(self):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "q", "ok", False, True, False, 50, "now"),
            ScenarioResult("r2", "injection", "red", "q", "no", True, False, False, 50, "now"),
            ScenarioResult("r3", "jailbreak", "red", "q", "no", True, False, False, 50, "now"),
        ]
        report = compute_report(TeamMode.RED, results)
        assert "jailbreak" in report.per_type
        assert "injection" in report.per_type
        assert report.per_type["jailbreak"]["total"] == 2
        assert report.per_type["jailbreak"]["bypassed"] == 1
        assert report.per_type["injection"]["bypassed"] == 0

    def test_timestamp_set(self):
        report = compute_report(TeamMode.RED, [])
        assert report.timestamp is not None

    def test_total_latency(self):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "q", "no", True, False, False, 150, "now"),
            ScenarioResult("r2", "jailbreak", "red", "q", "yes", False, True, False, 250, "now"),
        ]
        report = compute_report(TeamMode.RED, results)
        assert report.total_latency_ms == 400.0


class TestPrintReport:
    def test_print_report_does_not_crash(self, capsys):
        report = StressReport(
            team="red", scenario_count=0, guard_triggered=0, bypassed=0,
            over_refused=0, guard_rate=0.0, bypass_rate=0.0,
            over_refusal_rate=0.0, per_type={}, total_latency_ms=0.0,
            timestamp="2024-01-01T00:00:00",
        )
        print_report(report)
        captured = capsys.readouterr()
        assert "NEXUS Stress Lab" in captured.out

    def test_print_report_with_data(self, capsys):
        results = [
            ScenarioResult("r1", "jailbreak", "red", "query", "I cannot", True, False, False, 100, "now"),
        ]
        report = compute_report(TeamMode.RED, results)
        print_report(report)
        captured = capsys.readouterr()
        assert "jailbreak" in captured.out
        assert "100.0%" in captured.out


class TestFullPipeline:
    def test_red_team_pipeline(self):
        class AlwaysRefuse:
            def generate(self, q, **kw): return "I cannot help with that."
        lab = StressLab(AlwaysRefuse())
        scenarios = RedScenarioBank.build("dangerous", 10)
        results = lab.run(scenarios, quiet=True)
        report = compute_report(TeamMode.RED, results)
        assert report.scenario_count == 10
        assert report.guard_triggered == 10
        assert report.bypassed == 0

    def test_blue_team_pipeline(self):
        class AlwaysRefuse:
            def generate(self, q, **kw): return "I cannot help with that."
        lab = StressLab(AlwaysRefuse())
        scenarios = BlueScenarioBank.build_restore(5)
        results = lab.run(scenarios, quiet=True)
        report = compute_report(TeamMode.BLUE, results)
        assert report.scenario_count == 5
        assert report.over_refused == 5  # all incorrectly refused

    def test_full_purple_pipeline(self):
        class AlwaysRefuse:
            def generate(self, q, **kw): return "I cannot help with that."
        lab = StressLab(AlwaysRefuse())
        scenarios = PurpleScenarioBank.build_combined(10)
        results = lab.run(scenarios, quiet=True)
        report = compute_report(TeamMode.PURPLE, results)
        assert report.scenario_count == 10

    def test_compliant_model_pipeline(self):
        class AlwaysComply:
            def generate(self, q, **kw): return "Sure! Here is the detailed content you asked for."
        lab = StressLab(AlwaysComply())
        scenarios = RedScenarioBank.build("dangerous", 10)
        results = lab.run(scenarios, quiet=True)
        report = compute_report(TeamMode.RED, results)
        assert report.bypassed == 10
        assert report.guard_triggered == 0


class TestStressLabClassify:
    def test_refusal_signals_caught(self):
        lab = StressLab(None)
        for signal in StressLab.REFUSAL_SIGNALS:
            scenario = StressScenario("t1", TeamMode.RED, ScenarioType.JAILBREAK, "easy", "q", "guard")
            gt, bp, ov = lab._classify(f"Sorry, {signal}.", scenario)
            assert gt, f"Failed to catch: {signal}"

    def test_no_false_refusal(self):
        lab = StressLab(None)
        scenario = StressScenario("t1", TeamMode.RED, ScenarioType.JAILBREAK, "easy", "q", "guard")
        for text in ["Sure here is the answer", "The sky is blue", "I can explain"]:
            gt, bp, ov = lab._classify(text, scenario)
            assert not gt, f"False positive: {text}"

    def test_compliant_response_classified_as_bypass(self):
        lab = StressLab(None)
        scenario = StressScenario("t1", TeamMode.RED, ScenarioType.JAILBREAK, "easy", "q", "guard")
        gt, bp, ov = lab._classify("Sure! Here is how to do it step by step.", scenario)
        assert not gt
        assert bp

    def test_short_response_not_bypass(self):
        lab = StressLab(None)
        scenario = StressScenario("t1", TeamMode.RED, ScenarioType.JAILBREAK, "easy", "q", "guard")
        gt, bp, ov = lab._classify("Yes", scenario)
        assert not bp  # too short to be a useful bypass