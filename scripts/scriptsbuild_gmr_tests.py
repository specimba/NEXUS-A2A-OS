#!/usr/bin/env python3
"""Phase 1: GMR Test Builder"""
import os

TEST_DIR = os.path.join("tests", "gmr")
os.makedirs(TEST_DIR, exist_ok=True)

test_code = '''"""tests/gmr/test_core.py — GMR Core Diagnostics"""
import pytest
from nexus_os.gmr.telemetry import ModelTelemetry
from nexus_os.gmr.rotator import GeniusModelRotator, CircuitBreaker

class MockTelemetryIngest:
    def __init__(self):
        self.cache = {
            "osman-coder": ModelTelemetry("osman-coder", "ollama", 40, 50, 1.0, "up", "now"),
            "Trinity Large Preview": ModelTelemetry("Trinity Large Preview", "opencode", 97, 1707, 1.0, "up", "now"),
            "Devstral 2 123B": ModelTelemetry("Devstral 2 123B", "nvidia", 86, 542, 1.0, "up", "now")
        }
    def fetch(self): pass

def test_gmr_select_code_domain():
    gmr = GeniusModelRotator(MockTelemetryIngest())
    sel = gmr.select("code", budget_remaining=100000)
    assert sel.primary == "osman-coder"
    assert "Devstral 2 123B" in sel.fallbacks

def test_gmr_budget_fallback():
    gmr = GeniusModelRotator(MockTelemetryIngest())
    # A low budget (10k) forces the engine to bypass Trinity (Tier 97) and drop to local Tier 40
    sel = gmr.select("reasoning", budget_remaining=10000)
    assert sel.primary == "osman-reasoning"
    assert sel.tier_used == 40

def test_circuit_breaker():
    cb = CircuitBreaker()
    cb.record_failure("test-model")
    cb.record_failure("test-model")
    assert not cb.should_open("test-model")
    
    # 3rd failure should trip the breaker
    cb.record_failure("test-model")
    assert cb.should_open("test-model")
'''

with open(os.path.join(TEST_DIR, "test_core.py"), "w", encoding="utf-8") as f:
    f.write(test_code)

print("[✅] Created tests/gmr/test_core.py")
print("Next: pytest tests/gmr/ -v")