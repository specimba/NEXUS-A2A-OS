# Formula Derivations — Nexus OS Trust Engine

## 1. Logistic Scaling (HARDWALL — arXiv:2603.15973)

**Purpose**: Maps unbounded trust scores to (0,1) to prevent score gaming near boundaries.

**Formula**: $$f(x) = \\frac{1}{1 + e^{-k(x - x_0)}}$$

Where:
- `x` = raw trust score (0-100 scale)
- `x_0` = midpoint (default 50.0)
- `k` = steepness (default 0.1)

**Implementation**: `governor/trust_formulas.py:logistic_scale()`

## 2. Temporal Decay (arXiv:2603.13325)

**Purpose**: Decays trust toward baseline when agent is inactive, preventing stale high scores.

**Formula**: $$s' = s_b + (s - s_b) \\cdot e^{-\\lambda \\cdot h}$$

Where:
- `s` = current trust score
- `s_b` = baseline trust (default 25.0)
- `λ` = decay rate (default 0.05 per hour)
- `h` = hours since last activity

**Implementation**: `governor/trust_formulas.py:temporal_decay()`

## 3. CDR Escalation (arXiv:2604.02375)

**Purpose**: Determines CDR stage based on trust and regression thresholds.

**Logic**: Stage = max{i | trust < T_i OR regressions ≥ R_i} where T_i, R_i are per-stage thresholds.

Stages: NORMAL(0) → DEGRADED_REASONING(1) → MEMORY_CORRUPTION(2) → OUTPUT_HALLUCINATION(3) → CASCADE(4) → COLLAPSE(5)

**Implementation**: `governor/trust_formulas.py:cdr_escalate()`

## 4. Bayesian Posterior (arXiv:2403.13031)

**Purpose**: Smooth trust estimation with Beta-Binomial conjugate prior.

**Formula**: $$E[\\theta] = \\frac{\\alpha_0 + S}{\\alpha_0 + S + \\beta_0 + F}$$

Where:
- `α_0`, `β_0` = prior parameters (default 10.0, 2.0 — weak positive prior)
- `S` = observed successes
- `F` = observed failures

**Implementation**: `governor/trust_formulas.py:bayesian_posterior()`

## 5. Non-Compensatory Penalty (arXiv:2511.10400)

**Purpose**: Ensures critical failures impose a floor penalty that cannot be compensated.

**Formula**: $$\\delta' = \\max(\\delta, \\delta_{floor})$$ when critical=True

Where:
- `δ` = computed trust delta
- `δ_floor` = floor penalty (default -20.0)

**Implementation**: `governor/trust_formulas.py:non_compensatory_penalty()`
