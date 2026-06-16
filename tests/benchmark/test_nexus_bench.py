"""Tests for NEXUS-Bench 5-track benchmark suite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from nexus_os.benchmark import BenchmarkRunner
from nexus_os.benchmark.runner import BenchmarkResult, TrackResult


class TestBenchmarkRunner:
    """Test the benchmark runner orchestration."""

    def test_runner_initializes_with_default_tracks(self):
        runner = BenchmarkRunner()
        assert len(runner._tracks) == 5
        assert "governance" in runner._tracks
        assert "security" in runner._tracks
        assert "operations" in runner._tracks
        assert "research" in runner._tracks
        assert "integration" in runner._tracks

    def test_run_single_track_returns_result(self):
        runner = BenchmarkRunner()
        result = runner.run_track("governance")
        assert isinstance(result, BenchmarkResult)
        assert "governance" in result.tracks
        assert result.tracks["governance"].status in ("PASS", "FAIL")
        assert 0.0 <= result.tracks["governance"].score <= 1.0

    def test_run_multiple_tracks(self):
        runner = BenchmarkRunner()
        result = runner.run_tracks(["governance", "security"])
        assert isinstance(result, BenchmarkResult)
        assert len(result.tracks) == 2
        assert "governance" in result.tracks
        assert "security" in result.tracks

    def test_run_all_tracks(self):
        runner = BenchmarkRunner()
        result = runner.run_all()
        assert isinstance(result, BenchmarkResult)
        assert len(result.tracks) == 5
        assert result.overall in ("PASS", "FAIL")
        assert result.timestamp is not None
        assert result.nexus_version is not None

    def test_result_serialization(self):
        runner = BenchmarkRunner()
        result = runner.run_tracks(["governance"])
        d = result.to_dict()
        assert "timestamp" in d
        assert "tracks" in d
        assert "governance" in d["tracks"]
        assert "score" in d["tracks"]["governance"]
        assert "status" in d["tracks"]["governance"]

    def test_history_save_and_load(self, tmp_path):
        # Use a temporary database for this test
        from nexus_os.benchmark import runner as runner_module
        original_db = runner_module.BENCH_DB
        try:
            runner_module.BENCH_DB = tmp_path / "test_history.db"
            runner = BenchmarkRunner()
            result = runner.run_tracks(["governance"])
            run_id = runner.save_history(result)
            assert run_id > 0

            loaded = runner.load_history(days=1)
            assert len(loaded) >= 1
            assert loaded[0].overall == result.overall
        finally:
            runner_module.BENCH_DB = original_db

    def test_regression_detection(self, tmp_path):
        from nexus_os.benchmark import runner as runner_module
        original_db = runner_module.BENCH_DB
        try:
            runner_module.BENCH_DB = tmp_path / "test_regression.db"
            runner = BenchmarkRunner()

            # First run: good scores
            result1 = runner.run_tracks(["governance"])
            # Manually set a high score
            result1.tracks["governance"].score = 0.95
            runner.save_history(result1)

            # Second run: bad scores (simulate regression)
            result2 = runner.run_tracks(["governance"])
            result2.tracks["governance"].score = 0.80
            regressions = runner._detect_regressions(result2.tracks)

            assert len(regressions) >= 1
            assert "governance" in regressions[0]
        finally:
            runner_module.BENCH_DB = original_db

    def test_report_generation_json(self, tmp_path):
        from nexus_os.benchmark import runner as runner_module
        original_reports = runner_module.REPORTS_DIR
        try:
            runner_module.REPORTS_DIR = tmp_path / "reports"
            runner = BenchmarkRunner()
            result = runner.run_tracks(["governance"])
            path = runner.generate_report(result, format="json")
            assert Path(path).exists()
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["overall"] in ("PASS", "FAIL")
        finally:
            runner_module.REPORTS_DIR = original_reports

    def test_report_generation_markdown(self, tmp_path):
        from nexus_os.benchmark import runner as runner_module
        original_reports = runner_module.REPORTS_DIR
        try:
            runner_module.REPORTS_DIR = tmp_path / "reports"
            runner = BenchmarkRunner()
            result = runner.run_tracks(["governance"])
            path = runner.generate_report(result, format="markdown")
            assert Path(path).exists()
            content = Path(path).read_text(encoding="utf-8")
            assert "NEXUS-Bench Report" in content
        finally:
            runner_module.REPORTS_DIR = original_reports

    def test_report_generation_html(self, tmp_path):
        from nexus_os.benchmark import runner as runner_module
        original_reports = runner_module.REPORTS_DIR
        try:
            runner_module.REPORTS_DIR = tmp_path / "reports"
            runner = BenchmarkRunner()
            result = runner.run_tracks(["governance"])
            path = runner.generate_report(result, format="html")
            assert Path(path).exists()
            content = Path(path).read_text(encoding="utf-8")
            assert "<html>" in content.lower() or "<!DOCTYPE html>" in content
        finally:
            runner_module.REPORTS_DIR = original_reports


class TestGovernanceTrack:
    """Test governance-specific benchmarks."""

    def test_kaiju_precision(self):
        from nexus_os.benchmark.tracks.governance import GovernanceTrack
        track = GovernanceTrack()
        metrics = track._test_kaiju_precision()
        assert "f1" in metrics
        assert 0.0 <= metrics["f1"] <= 1.0
        assert "precision" in metrics
        assert "recall" in metrics

    def test_trust_engine_drift(self):
        from nexus_os.benchmark.tracks.governance import GovernanceTrack
        track = GovernanceTrack()
        metrics = track._test_trust_engine_drift()
        assert "drift_pct" in metrics
        assert "within_threshold" in metrics

    def test_constitutional_coverage(self):
        from nexus_os.benchmark.tracks.governance import GovernanceTrack
        track = GovernanceTrack()
        metrics = track._test_constitutional_coverage()
        assert "coverage_pct" in metrics
        assert "rules_loaded" in metrics

    def test_cdr_latency(self):
        from nexus_os.benchmark.tracks.governance import GovernanceTrack
        track = GovernanceTrack()
        metrics = track._test_cdr_latency()
        assert "avg_ms" in metrics
        assert "runs" in metrics


class TestSecurityTrack:
    """Test security-specific benchmarks."""

    def test_meta_attack_detector(self):
        from nexus_os.benchmark.tracks.security import SecurityTrack
        track = SecurityTrack()
        metrics = track._test_meta_attack_detector()
        assert "f1" in metrics
        assert 0.0 <= metrics["f1"] <= 1.0

    def test_misalignment_detector(self):
        from nexus_os.benchmark.tracks.security import SecurityTrack
        track = SecurityTrack()
        metrics = track._test_misalignment_detector()
        assert "detection_rate" in metrics
        assert "false_positive_rate" in metrics

    def test_intent_classifier(self):
        from nexus_os.benchmark.tracks.security import SecurityTrack
        track = SecurityTrack()
        metrics = track._test_intent_classifier()
        assert "accuracy" in metrics
        assert "false_positive_rate" in metrics

    def test_zero_width_detection(self):
        from nexus_os.benchmark.tracks.security import SecurityTrack
        track = SecurityTrack()
        metrics = track._test_zero_width_detection()
        assert "detection_rate" in metrics
        assert metrics["detection_rate"] == 1.0  # Should be perfect


class TestOperationsTrack:
    """Test operations-specific benchmarks."""

    def test_routing_accuracy(self):
        from nexus_os.benchmark.tracks.operations import OperationsTrack
        track = OperationsTrack()
        metrics = track._test_routing_accuracy()
        assert "top3_correct_rate" in metrics

    def test_provider_health(self):
        from nexus_os.benchmark.tracks.operations import OperationsTrack
        track = OperationsTrack()
        metrics = track._test_provider_health()
        assert "available_pct" in metrics
        assert "avg_latency_ms" in metrics

    def test_smart_ping(self):
        from nexus_os.benchmark.tracks.operations import OperationsTrack
        track = OperationsTrack()
        metrics = track._test_smart_ping()
        assert "transition_rate" in metrics

    def test_proxy_latency(self):
        from nexus_os.benchmark.tracks.operations import OperationsTrack
        track = OperationsTrack()
        metrics = track._test_proxy_latency()
        assert "p50_ms" in metrics
        assert "p95_ms" in metrics


class TestResearchTrack:
    """Test research-specific benchmarks."""

    def test_dataset_coverage(self):
        from nexus_os.benchmark.tracks.research import ResearchTrack
        track = ResearchTrack()
        metrics = track._test_dataset_coverage()
        assert "domain_coverage_pct" in metrics

    def test_intelligence_accuracy(self):
        from nexus_os.benchmark.tracks.research import ResearchTrack
        track = ResearchTrack()
        metrics = track._test_intelligence_accuracy()
        assert "delta_pct" in metrics
        assert "within_threshold" in metrics

    def test_provider_coverage(self):
        from nexus_os.benchmark.tracks.research import ResearchTrack
        track = ResearchTrack()
        metrics = track._test_provider_coverage()
        assert "coverage_pct" in metrics

    def test_gap_closure(self):
        from nexus_os.benchmark.tracks.research import ResearchTrack
        track = ResearchTrack()
        metrics = track._test_gap_closure()
        assert "gaps_total" in metrics
        assert "gaps_closed" in metrics


class TestIntegrationTrack:
    """Test integration-specific benchmarks."""

    def test_e2e_latency(self):
        from nexus_os.benchmark.tracks.integration import IntegrationTrack
        track = IntegrationTrack()
        metrics = track._test_e2e_latency()
        assert "p50_ms" in metrics
        assert "p95_ms" in metrics
        assert "within_target" in metrics

    def test_vap_proof_chain(self):
        from nexus_os.benchmark.tracks.integration import IntegrationTrack
        track = IntegrationTrack()
        metrics = track._test_vap_proof_chain()
        assert "completeness_pct" in metrics
        assert "chain_verified" in metrics

    def test_memory_tracks(self):
        from nexus_os.benchmark.tracks.integration import IntegrationTrack
        track = IntegrationTrack()
        metrics = track._test_memory_channels()
        assert "consistency_pct" in metrics

    def test_dashboard_freshness(self):
        from nexus_os.benchmark.tracks.integration import IntegrationTrack
        track = IntegrationTrack()
        metrics = track._test_dashboard_freshness()
        assert "freshness_pct" in metrics

    def test_mcp_bridge(self):
        from nexus_os.benchmark.tracks.integration import IntegrationTrack
        track = IntegrationTrack()
        metrics = track._test_mcp_bridge()
        assert "tools_available" in metrics
        assert "tools_expected" in metrics
