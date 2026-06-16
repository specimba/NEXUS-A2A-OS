# Research Papers Index — Nexus OS Trust Formulas

## Papers Referenced

| ArXiv ID | Title | Use Case in Trust Formulas | File |
|----------|-------|---------------------------|------|
| arXiv:2603.15973 | HARDWALL: Hardened Defenses for Agent Trust Systems | Logistic scaling (anti-gaming), non-compensatory CRITICAL block | `governor/trust_formulas.py:logistic_scale()` |
| arXiv:2603.13325 | Decay-Regularized Trust in Autonomous Systems | Adaptive temporal decay toward baseline | `governor/trust_formulas.py:temporal_decay()` |
| arXiv:2604.02375 | CDR: Cascading Degradation Response for Multi-Agent Trust | 6-stage CDR state machine | `governor/trust_formulas.py:cdr_escalate()` |
| arXiv:2403.13031 | Bayesian Reputation Systems for Collaborative AI | Beta-Binomial posterior trust | `governor/trust_formulas.py:bayesian_posterior()` |
| arXiv:2511.10400 | Non-Compensatory Safety Evaluation in Agentic Systems | Non-compensatory critical penalty floor | `governor/trust_formulas.py:non_compensatory_penalty()` |

## Secondary References
- trust_engine_v2.py (`governor/trust_engine_v2.py`) integrates all five formulas with CDR state machine (6-stage), logistic scaling, adaptive decay, and non-compensatory CRITICAL penalties.
- trust_scoring.py (`governor/trust_scoring.py`) uses lane-parameterized scoring with the Bayesian posterior for per-agent trust accumulation.
