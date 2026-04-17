#!/usr/bin/env python3
"""P1-3: Adaptive Circuit Breaker HALF_OPEN state implementation"""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Patch 1: Update CircuitBreaker in bridge/sdk.py
sdk_path = os.path.join(REPO, "src", "nexus_os", "bridge", "sdk.py")

with open(sdk_path, "r", encoding="utf-8") as f:
    code = f.read()

# Add HALF_OPEN state
if "HALF_OPEN" not in code:
    code = re.sub(
        r'class CircuitState\(Enum\):\s+CLOSED = "closed"\s+OPEN = "open"',
        '''class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"''',
        code
    )
    print("[✅] Added HALF_OPEN state")

# Add half open transition logic
code = re.sub(
    r'def _transition_state\(self\):',
    '''def _transition_state(self):
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_at > self.open_timeout:
                self.state = CircuitState.HALF_OPEN
                self.remaining_probes = 1
                self._emit("circuit_half_open")
                return''',
    code
)

print("\n[✅] P1-3 Adaptive Circuit Breaker applied.")
