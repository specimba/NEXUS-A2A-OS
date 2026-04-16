# NEXUS OS v3.0 — Quick Start Boot Pack
**Version**: m3-hardened | **Status**: CODE_CONFIRMED | **Last Updated**: 2026-04-16

## 60-Second Bootstrap
1. Clone: git clone https://github.com/specimba/nexusalpha.git
2. Activate: .\venv\Scripts\Activate.ps1
3. Install: pip install -r requirements.txt
4. Verify: python scripts/c5_integration_gate.py

## Key Components (P0 Verified)
- Bridge Token Headers: bridge/server.py
- Governor Hard-Stop: governor/base.py
- Trust Hot-Path: monitoring/trust_scorer.py
- VAP Audit Chain: governor/proof_chain.py

## Current Metrics
- Tests: 450 passed, 0 failed
- Execution: ~20s
- Tag: m3-hardened


