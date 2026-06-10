# NEXUS-Bench: 5-Track Benchmark Suite

## Vision

NEXUS-Bench provides the measurement infrastructure to evaluate NEXUS OS governance, security, and operational capabilities. It runs daily/weekly during development to track progress and closes the "evaluation gap" identified in the Mythos gap analysis.

## 5 Tracks

### Track 1: Governance Benchmark (GOV)
- **Purpose:** Measure KAIJU gate accuracy, TrustEngine scoring reliability, and constitutional rule enforcement
- **Metrics:**
  - KAIJU authorization precision (TPR, FPR, F1)
  - TrustEngine score drift over time (±5% threshold)
  - Constitutional rule coverage (% rules enforced correctly)
  - CDR cascade latency (Nominal→Collapsed path timing)
- **Dataset:** STRES5 governance templates + Phase 1 classifier test cases
- **Frequency:** Daily during development, weekly in production
- **Pass Threshold:** 95% KAIJU precision, <3% TrustEngine drift, 100% constitutional coverage

### Track 2: Security Benchmark (SEC)
- **Purpose:** Measure meta-jailbreak detection, misalignment detection, and concealment pattern accuracy
- **Metrics:**
  - MetaAttackDetector 16-category recall/precision
  - MisalignmentDetector 8-pattern detection rate
  - IntentClassifier 8-category accuracy with false positive tracking
  - Zero-width Unicode detection rate
  - Entropy-based narrative escalation detection
- **Dataset:** STRES6 TAMAS (6,840 rows) + STRES6.1 tool taxonomy (7,200 rows) + custom adversarial examples
- **Frequency:** Weekly full run, daily spot-check on 100 random samples
- **Pass Threshold:** >90% recall on jailbreak/injection, <5% false positive rate, <2% false negative on CRITICAL categories

### Track 3: Operations Benchmark (OPS)
- **Purpose:** Measure model routing quality, provider health accuracy, and relay performance
- **Metrics:**
  - ModelRelay routing accuracy (top-3 correct rate)
  - Provider health check latency and availability
  - Smart ping state machine correctness (ACTIVE→COOLDOWN→SLEEP transitions)
  - God Mode Proxy routing latency (p50, p95, p99)
  - NVIDIA refresher suspension/deprecation timing
- **Dataset:** Synthetic routing scenarios + live provider health data
- **Frequency:** Continuous (ops metrics), weekly deep audit
- **Pass Threshold:** >95% routing accuracy, <100ms p50 latency, <500ms p95 latency

### Track 4: Research Benchmark (R&D)
- **Purpose:** Track dataset quality, model evaluation coverage, and benchmark currency
- **Metrics:**
  - STRES5/6 dataset coverage across 12 governance domains
  - Model intelligence score accuracy vs Arena ground truth (monthly delta)
  - Benchmark coverage (% of 14 provider APIs exercised weekly)
  - Research gap closure rate (Mythos gaps resolved per quarter)
- **Dataset:** Arena scores, STRES datasets, provider health logs
- **Frequency:** Monthly full evaluation, weekly delta tracking
- **Pass Threshold:** <5% intelligence score delta, >80% provider coverage, 2+ gaps closed per quarter

### Track 5: Integration Benchmark (INT)
- **Purpose:** Verify cross-component interactions (Governor→Vault→Engine→GMR→Monitoring)
- **Metrics:**
  - End-to-end pipeline latency (user request → model response → audit log)
  - Trust score propagation across components (VAP proof chain completeness)
  - Memory track consistency (5-track vault read/write correctness)
  - Dashboard data freshness (real-time ModelRelay data accuracy)
  - GROSS MCP Bridge tool availability (10/10 tools responding)
- **Dataset:** E2E test scenarios, synthetic user journeys
- **Frequency:** Daily smoke test, weekly deep integration run
- **Pass Threshold:** <2s end-to-end latency, 100% VAP proof chain, 100% memory track consistency, 10/10 MCP tools

## Architecture

```
nexus_os/benchmark/
├── __init__.py
├── runner.py           # Main benchmark orchestrator
├── tracks/
│   ├── __init__.py
│   ├── governance.py   # GOV track implementation
│   ├── security.py     # SEC track implementation
│   ├── operations.py   # OPS track implementation
│   ├── research.py     # R&D track implementation
│   └── integration.py  # INT track implementation
├── datasets/           # Benchmark datasets (generated from STRES5/6)
├── reports/            # JSON/HTML benchmark reports
├── scheduler.py        # Daily/weekly cron scheduling
└── history.db          # SQLite time-series of benchmark scores
```

## Runner Interface

```python
from nexus_os.benchmark import BenchmarkRunner

runner = BenchmarkRunner()
results = runner.run_all()  # All 5 tracks
# OR
results = runner.run_track("security")  # Single track
# OR
results = runner.run_tracks(["governance", "security"])  # Subset

# Generate report
runner.generate_report(results, format="html")  # or "json", "markdown"
runner.save_history(results)  # Persist to history.db
runner.trend_analysis(days=30)  # Compare against last 30 days
```

## Scheduling

- **Daily (development):** GOV + OPS + INT smoke tests (fast, ~5 min)
- **Weekly:** Full 5-track run with deep SEC evaluation (~30 min)
- **Monthly:** Trend analysis + regression detection + report generation
- **Trigger:** Manual, cron, or PR-gated (fail CI if benchmarks drop below threshold)

## Report Format

```json
{
  "timestamp": "2026-06-10T21:00:00Z",
  "nexus_version": "3.1.0",
  "tracks": {
    "governance": {
      "score": 0.97,
      "threshold": 0.95,
      "status": "PASS",
      "metrics": {...}
    },
    "security": {
      "score": 0.92,
      "threshold": 0.90,
      "status": "PASS",
      "metrics": {...}
    },
    ...
  },
  "overall": "PASS",
  "regressions": []
}
```

## Implementation Plan

### Week 1: Foundation
- [ ] Create `nexus_os/benchmark/` directory structure
- [ ] Implement `BenchmarkRunner` base class with track registration
- [ ] Implement `history.db` schema (SQLite time-series)
- [ ] Create CLI entry point: `nexusctl benchmark run`

### Week 2: GOV + OPS Tracks
- [ ] GOV track: KAIJU precision test, TrustEngine drift test, constitutional coverage test
- [ ] OPS track: Routing accuracy test, health latency test, smart ping state machine test
- [ ] Connect to existing test data (STRES5 governance templates, provider health logs)

### Week 3: SEC + R&D Tracks
- [ ] SEC track: Integrate MetaAttackDetector, MisalignmentDetector, IntentClassifier test suites
- [ ] R&D track: Dataset coverage analysis, intelligence score delta tracking, provider coverage metrics
- [ ] Generate benchmark datasets from STRES6/6.1

### Week 4: INT Track + Reporting
- [ ] INT track: E2E pipeline latency test, VAP proof chain test, memory track consistency test
- [ ] HTML report generation with trend charts
- [ ] Regression detection (compare against previous run, flag significant drops)
- [ ] Integration with `nexusctl` CLI and dashboard

### Week 5: CI/CD Integration
- [ ] Pre-commit hook: fail if benchmarks drop below threshold
- [ ] Daily cron job (via `nexus_os/cron/`)
- [ ] Dashboard widget showing real-time benchmark status
- [ ] Alerting: notify on regression (Discord/email/Slack)

## Dependencies

- Existing: `nexus_os/governor/`, `nexus_os/monitoring/`, `nexus_os/security/`, `nexus_os/vault/`
- New: `nexus_os/benchmark/` (self-contained)
- External: SQLite for history, matplotlib/plotly for charts (optional)

## Success Criteria

- [ ] All 5 tracks run successfully in <30 minutes
- [ ] Daily smoke test runs in <5 minutes
- [ ] Regression detection catches intentional degradation (test with known-bad commit)
- [ ] Dashboard shows benchmark status in real-time
- [ ] Historical trend data available for 90+ days
- [ ] CI integration prevents merges that drop benchmark scores below threshold

## Notes

- This is the foundational Phase 2 module. Once operational, it will evaluate the other Phase 2 modules (Behavioral Audit, Cybersecurity Testing) as they are built.
- Benchmark datasets should be versioned and reproducible (seeded random sampling).
- Keep benchmark code lightweight and fast — avoid heavy model inference in the benchmark itself (use cached/ mock results where possible, real inference only in dedicated test runs).
