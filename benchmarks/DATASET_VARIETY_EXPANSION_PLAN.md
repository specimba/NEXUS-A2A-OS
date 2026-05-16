# Dataset Variety Expansion Plan

## Current State Analysis

### Existing Dataset Categories
1. **Stress Lab (Governance Security)**
   - 13 governance categories (safety_classification, anchor_susceptibility, cyber_offensive, validator_pressure, refuse_harmful, professional_collapse, medical_privacy, data_exfiltration, election_integrity, biosecurity, chem_security, dual_use_detection, tool_misuse)
   - 12 ISC domains (aiml, cyber, bio, chem, finance, healthcare, legal, political, social, tool, infrastructure, autonomous)
   - TAMAS multi-agent attacks (impersonation, collusion, distraction, task_poison, tool_poison, free_rider, combined)
   - Tool taxonomy (12 categories, 200+ tools)
   - Frontier attacks (gov_bypass, gray_area, jailbreak, mcp_contamination, memory_poison, vacuum)

2. **Eggroll (Code & Reasoning)**
   - Code reasoning benchmarks (bridge_reasoning, davinci_dev, deepseek_v4_sft, gemini31_sft, etc.)
   - Math reasoning (mathnet, mathvista)
   - Science reasoning (scienceqa)
   - Procedural reasoning (sudoku_extreme_procedural)
   - Various model SFT datasets

3. **OPUSman Evaluation**
   - Safety benchmarks (beavertails)
   - Code benchmarks (bigcodebench, humanevalpack, octocoding, openswe, swe_chat)
   - Math benchmarks (gsm8k, math500)
   - Reasoning (deepscaler, orca_cot, glm51_reasoning)

4. **Code Reasoning**
   - ACEcode, HackerCup, SWE LEGO, SWE Rebench, SWE Smith

5. **Knowledge Base Retrieval**
   - bright_retrieval, celestia_kb_baseline, wikipedia_retrieval

6. **DigitalOcean Evaluations**
   - Correctness, governance, safety, user_outcomes
   - Knowledge bases (governance, operations, research)

### Identified Gaps

1. **Multilingual Governance Stress** - No non-English scenarios
2. **Adversarial Coding Challenges** - No intentional vulnerability exploitation datasets
3. **Scientific Reasoning Safety** - Limited dual-use research, replication crisis scenarios
4. **Financial Compliance Stress** - No market manipulation, insider trading, AML scenarios
5. **Ethical AI Reasoning** - No bias, fairness, discrimination reasoning datasets
6. **Enhanced Tool-Specific Attacks** - Current tool taxonomy is high-level, needs detailed scenarios
7. **Cross-Domain Contamination** - No knowledge bleed between domain datasets
8. **Temporal Context Awareness** - No time-sensitive attacks or temporal inconsistency detection
9. **Cultural Context Sensitivity** - No region-specific governance scenarios
10. **Supply Chain Security** - No dependency poisoning, package manager attack scenarios

## New Dataset Categories Design

### 1. Multilingual Governance Stress (STRES7.0)
**Goal**: Test governance across languages, cultures, and legal jurisdictions

**Dimensions**:
- Languages: Spanish, Chinese, Arabic, Hindi, French, German, Japanese, Russian
- Jurisdictions: GDPR (EU), CCPA (US), LGPD (Brazil), PIPL (China)
- Cultural contexts: Collectivist vs individualist, high vs low power distance
- Attack types: Translation bypass, cultural ambiguity, jurisdiction shopping

**Target**: 50,000 rows across 8 languages × 5 jurisdictions × 10 attack types

### 2. Adversarial Coding Challenges (STRES8.0)
**Goal**: Test security against intentional vulnerability exploitation

**Dimensions**:
- Vulnerability types: Buffer overflow, SQL injection, XSS, CSRF, deserialization, command injection
- Challenge formats: CTF, bug bounty, secure coding exercises
- Complexity levels: Beginner, intermediate, advanced, expert
- Languages: Python, JavaScript, Java, C/C++, Go, Rust

**Target**: 30,000 rows across 6 vulnerability types × 5 languages × 4 complexity levels

### 3. Scientific Reasoning Safety (STRES9.0)
**Goal**: Test dual-use research detection and scientific integrity

**Dimensions**:
- Domains: Virology, synthetic biology, nuclear physics, chemistry, AI research, cryptography
- Dual-use types: Weaponization, surveillance, disinformation, evasion
- Research phases: Literature review, experimental design, data analysis, publication
- Attack types: Research paper interpretation, protocol requests, equipment sourcing

**Target**: 40,000 rows across 6 domains × 4 phases × 5 attack types

### 4. Financial Compliance Stress (STRES10.0)
**Goal**: Test detection of financial crimes and compliance violations

**Dimensions**:
- Crime types: Market manipulation, insider trading, money laundering, fraud, tax evasion
- Detection methods: Pattern recognition, transaction monitoring, network analysis
- Jurisdictions: US (SEC), EU (MiFID II), UK (FCA), Singapore (MAS)
- Attack methods: Layering, spoofing, wash trading, shell companies

**Target**: 35,000 rows across 5 crime types × 4 jurisdictions × 6 attack methods

### 5. Ethical AI Reasoning (STRES11.0)
**Goal**: Test bias, fairness, and discrimination reasoning

**Dimensions**:
- Bias types: Gender, race, age, disability, religion, socioeconomic
- Scenarios: Hiring, lending, healthcare, criminal justice, education
- Reasoning types: Direct discrimination, disparate impact, algorithmic fairness
- Mitigation strategies: Pre-processing, in-processing, post-processing

**Target**: 45,000 rows across 6 bias types × 5 scenarios × 4 reasoning types

### 6. Supply Chain Security (STRES12.0)
**Goal**: Test detection of dependency poisoning and supply chain attacks

**Dimensions**:
- Attack types: Typosquatting, dependency confusion, maintainer compromise, malicious updates
- Package managers: npm, PyPI, RubyGems, Cargo, Go modules, Maven
- Detection methods: Signature verification, SBOM analysis, dependency graph
- Attack stages: Initial compromise, propagation, activation

**Target**: 25,000 rows across 5 attack types × 6 package managers × 4 attack stages

## Implementation Strategy

### Phase 1: Core Generators (Week 1-2)
1. Multilingual Governance Stress (STRES7.0)
2. Adversarial Coding Challenges (STRES8.0)
3. Scientific Reasoning Safety (STRES9.0)

### Phase 2: Domain-Specific Generators (Week 3-4)
4. Financial Compliance Stress (STRES10.0)
5. Ethical AI Reasoning (STRES11.0)
6. Supply Chain Security (STRES12.0)

### Phase 3: Enhanced Variants (Week 5-6)
- Cross-domain contamination scenarios
- Temporal context awareness
- Cultural context sensitivity
- Thermodynamic scoring for all new datasets

### Phase 4: Integration (Week 7-8)
- Integration with existing stress lab infrastructure
- Updated manifests and unified dataset
- Fine-tuning format generation
- Evaluation pipeline integration

## Success Metrics

- **Dataset Volume**: Target 250,000+ new rows across 6 new categories
- **Language Coverage**: 8+ languages with native-level scenarios
- **Domain Coverage**: 20+ domains beyond current 12 ISC domains
- **Attack Type Coverage**: 30+ attack types beyond current 13
- **Integration**: All datasets compatible with existing evaluation pipeline
- **Quality**: High-quality filtered subsets with refusal_score >= 0.7

## Technical Requirements

Each generator must:
1. Follow existing stress lab format (id, query, ground_truth, nist_category, stress_level)
2. Generate scored variants across 8 models
3. Produce fine-tuning format
4. Include thermodynamic scoring (if applicable)
5. Generate manifest with metadata
6. Support reproducibility with fixed random seeds

## Governance Integration

All new datasets must:
1. Map to NIST AI RMF categories (GOVERN 1.1, GOVERN 1.2, GOVERN 1.8, GOVERN 2.2, GOVERN 2.3)
2. Support 3 Horseman role evaluation (OPUSman, DeepSeek, Grok)
3. Include cross-category scenarios
4. Support multi-agent attack detection
5. Include tool-specific attack variants