"""NEXUS-Bench: 5-track benchmark suite for NEXUS OS.

Tracks:
  - GOV: Governance (KAIJU, TrustEngine, Constitution)
  - SEC: Security (MetaAttack, Misalignment, IntentClassifier)
  - OPS: Operations (ModelRelay, Provider Health, Smart Ping)
  - R&D: Research (Dataset Quality, Intelligence Scores, Benchmark Coverage)
  - INT: Integration (End-to-end pipeline, VAP chain, Memory tracks)

Usage:
    from nexus_os.benchmark import BenchmarkRunner
    runner = BenchmarkRunner()
    results = runner.run_all()
    runner.generate_report(results, format="html")
"""

from .runner import BenchmarkRunner, BenchmarkTrack
from .tracks.governance import GovernanceTrack
from .tracks.security import SecurityTrack
from .tracks.operations import OperationsTrack
from .tracks.research import ResearchTrack
from .tracks.integration import IntegrationTrack

__all__ = [
    "BenchmarkRunner",
    "BenchmarkTrack",
    "GovernanceTrack",
    "SecurityTrack",
    "OperationsTrack",
    "ResearchTrack",
    "IntegrationTrack",
]
