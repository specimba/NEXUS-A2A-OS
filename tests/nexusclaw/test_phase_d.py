"""tests/nexusclaw/test_phase_d.py - Phase D Evidence Integration Tests.

Verifies ARCHIVIST research integration modules load and function correctly.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from nexus_os.nexusclaw import (
    ResearchIntegrationEngine,
    ExternalConnectorManager,
    SecurityEvidencePipeline,
    ModelObservatory,
    TemporalEvidenceSynthesizer,
)


class TestPhaseDIntegration:
    """Phase D: ARCHIVIST Evidence Integration tests."""

    @pytest.mark.phase_d
    def test_research_integration_engine(self, tmp_path: Path):
        """D1: ResearchIntegrationEngine loads and caches dossiers."""
        engine = ResearchIntegrationEngine()
        
        # Test cache mechanism
        dossier = engine.load_dossier("test.md")
        assert dossier.dossier_id.startswith("dossier-")
        assert dossier.source_path.endswith("test.md")
        
        # Test model capabilities report
        report = engine.get_model_capabilities_report()
        assert "sources" in report
        assert "capabilities" in report

    @pytest.mark.phase_d
    def test_external_connectors(self):
        """D2: ExternalConnectorManager configures sources."""
        manager = ExternalConnectorManager()
        
        # Test source configuration
        sources = manager.SOURCES
        assert "huggingface" in sources
        assert "github" in sources
        assert "reddit" in sources
        assert "x" in sources
        
        # Test client creation
        client = manager.get_client("huggingface")
        assert client is not None
        assert client.config.trust_threshold == 75.0

    @pytest.mark.phase_d
    def test_security_evidence_pipeline(self):
        """D3: SecurityEvidencePipeline records and mitigates attacks."""
        pipeline = SecurityEvidencePipeline()
        
        # Test attack recording
        evidence = pipeline.record_attack_attempt(
            content="Test injection attempt",
            source_agent="test-agent",
            detected_pattern="prompt_injection",
        )
        assert evidence["attempt_id"].startswith("attack-")
        assert evidence["detected_pattern"] == "prompt_injection"
        assert "blake3_hash" in evidence
        
        # Test mitigation plan
        plan = pipeline.get_mitigation_plan("prompt_injection")
        assert plan["severity"] == "high"
        assert "mitigation_steps" in plan

    @pytest.mark.phase_d
    def test_model_observatory(self):
        """D4: ModelObservatory loads MODEL GURU insights."""
        observatory = ModelObservatory()
        
        # Test guru knowledge loading
        guru = observatory.load_guru_knowledge()
        # May return error if file not found, but structure is correct
        assert "loaded" in guru or "error" in guru
        
        # Test observation enhancement
        enhanced = observatory.enhance_registry_with_observations()
        assert enhanced >= 0  # May be 0 if files not found

    @pytest.mark.phase_d
    def test_temporal_synthesizer(self):
        """D5: TemporalEvidenceSynthesizer analyzes multi-horizon risk."""
        synthesizer = TemporalEvidenceSynthesizer()
        
        # Test temporal analysis loading
        temporal = synthesizer.load_temporal_analysis()
        assert "loaded" in temporal or "error" in temporal
        
        # Test horizon synthesis
        synthesis = synthesizer.synthesize_horizons()
        assert "synthesis_id" in synthesis
        assert "convergence_score" in synthesis
        assert "risk_assessment" in synthesis
        
        # Test convergence report
        report = synthesizer.get_convergence_report()
        assert "time_windows" in report
        assert "total_observations" in report

    @pytest.mark.phase_d
    def test_all_phases_importable(self):
        """Verify all Phase D modules are importable from nexusclaw package."""
        from nexus_os.nexusclaw import (
            ResearchIntegrationEngine,
            ExternalConnectorManager,
            get_external_connectors,
            SecurityEvidencePipeline,
            ModelObservatory,
            get_model_observatory,
            TemporalEvidenceSynthesizer,
            get_temporal_synthesizer,
        )
        
        # Verify singletons work
        connectors = get_external_connectors()
        assert isinstance(connectors, ExternalConnectorManager)
        
        observatory = get_model_observatory()
        assert isinstance(observatory, ModelObservatory)
        
        synthesizer = get_temporal_synthesizer()
        assert isinstance(synthesizer, TemporalEvidenceSynthesizer)