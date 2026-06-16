"""Tests for Trust Engine V2 factory function."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.governor.trust_engine_v2 import TrustEngineV2, get_trust_engine


class TestGetTrustEngineFactory:
    def test_returns_instance(self):
        engine = get_trust_engine()
        assert engine is not None

    def test_singleton(self):
        a = get_trust_engine()
        b = get_trust_engine()
        assert a is b

    def test_constants_accessible(self):
        engine = get_trust_engine()
        assert engine.BASELINE_SCORE == 25.0
        assert engine.MAX_SCORE == 99.5
        assert engine.MIN_SCORE == 0.0
        assert engine.SUCCESS_BASE_DELTA == 4.0
        assert engine.FAILURE_DELTA == -10.0
        assert engine.CRITICAL_DELTA == -20.0
        assert engine.BASE_DECAY == 0.02
