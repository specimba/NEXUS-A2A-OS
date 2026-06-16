# Claude Fable 5 & Mythos 5 Technical Deep Dive

## Executive Summary

Claude Fable 5 and Mythos 5 represent Anthropic's entry into the "Mythos-class" tier of frontier AI models — a significant leap above the previous Opus class (4.6/4.7). Released June 9, 2026, Fable 5 is the safeguarded general-public version, while Mythos 5 is the unrestricted version available through Project Glasswing to trusted cyberdefenders and researchers.

## Model Architecture & Training

### Training Paradigm
- **Claude Mythos Preview** (April 2026) was the precursor, trained with advanced constitutional AI techniques
- **Fable 5/Mythos 5** share the same underlying base model — the distinction is purely in safety guardrails
- Training data includes: web corpus, books, code repositories, scientific papers, and specialized cybersecurity datasets (for Mythos variant)
- Constitutional training incorporates multi-layered value alignment with human feedback at multiple scales

### Key Technical Specifications
- **Context Window**: Extended (exact token count not publicly disclosed, but references to "millions of tokens" in long-context tasks suggest >1M tokens)
- **Architecture**: Likely Mixture-of-Experts (MoE) or dense transformer with advanced routing (given the performance leap over Opus 4.6)
- **Parameter Count**: Not disclosed, but inference cost suggests significantly larger than Opus 4.6 (~175B parameters equivalent in compute)
- **Inference Cost**: $10/1M input tokens, $50/1M output tokens (less than half of Mythos Preview pricing)
- **Knowledge Cutoff**: ~2026 (includes very recent events)

## Capabilities & Benchmarks

### Software Engineering (SOTA)
- **FrontierCode (Cognition)**: Highest score among frontier models, even at "medium effort" setting
- **Stripe Test**: Compressed months of engineering into days — 50M line Ruby codebase migration completed in 1 day vs. 2+ months for human team
- **GitHub Tests**: Took on complex, long-horizon coding tasks with autonomy and reliability exceeding previous benchmarks
- **CursorBench**: State-of-the-art according to Cursor team
- **Token Efficiency**: More efficient than past Claude models on coding tasks

### Vision Capabilities (SOTA)
- **Web App Reconstruction**: Can rebuild web app source code from screenshots alone
- **Game Playing**: Beat Pokémon FireRed with vision-only harness (no maps, no navigation aids) — previous Claude models needed complex helper harnesses
- **Scientific Figures**: Extracts precise numbers from detailed scientific figures
- **Vibe Coding**: Highest-performing on ViBench (Cognition's end-to-end vibe-coding benchmark)

### Knowledge Work & Reasoning
- **Hebbia Finance Benchmark**: Highest score of any model on senior-level reasoning tasks
- **Document Analysis**: Superior document-based reasoning, chart/table interpretation, problem solving
- **IMC Trading Analysis**: Aced factual lookup, conceptual reasoning, root-cause analysis, expected-value analysis
- **Long-Context Memory**: 3x better performance with persistent file-based memory vs. Opus 4.8 (tested on Slay the Spire)
- **Self-Improvement**: Uses own notes to improve outputs across millions of tokens

### Scientific Research
- **Protein Design**: 10x acceleration in drug design process using Mythos 5
- **Novel Hypotheses**: First Anthropic model to consistently produce novel, compelling scientific hypotheses
- **Molecular Biology**: Scientists preferred Mythos hypotheses ~80% of the time in blinded comparisons
- **Genomics**: Conducted novel research over a week of autonomous work; assembled single-cell data for millions of cells across 138 species; designed and trained custom ML model that outperformed recent Science journal publication despite being 100x smaller
- **Independent Validation**: One Mythos hypothesis (novel E. coli protein mechanism) was independently corroborated in a separate lab study

## Safety Architecture: Classifier-Based Routing

### Three-Layer Safety System

**Layer 1: Main Model (Fable 5)**
- Handles all general requests
- Full capabilities for benign use cases
- No artificial capability degradation on safe queries

**Layer 2: Safety Classifiers**
- Separate AI systems that detect potential misuse
- Three categories monitored:
  1. **Cybersecurity**: Exploitation, offensive cyber tasks, vulnerability development
  2. **Biology/Chemistry**: Dual-use research, bioweapons-related queries, viral engineering
  3. **Distillation**: Attempts to extract model capabilities for training competing models
- Coverage is broad by design (conservative tuning)
- <5% of sessions trigger fallback
- Triggers average: less than 5% of all sessions

**Layer 3: Fallback Model (Claude Opus 4.8)**
- Highly capable model in its own right
- Activated when classifiers trigger
- Provides excellent response quality instead of outright refusal
- User is informed when fallback occurs

### Red-Teaming & Jailbreak Resistance
- **External Bug Bounty**: No universal jailbreaks found in 1,000+ hours of testing
- **External Red-Teams**: Failed to find universal jailbreaks on long-form agentic tasks
- **UK AISI**: Made progress toward one universal jailbreak within brief initial testing window
- **30 Jailbreak Techniques**: Fable 5 complied with zero harmful single-turn requests relating to cyberattack planning, exploit development, or defense evasion
- **Partner Testing**: Most robust safeguards against harmful cyber queries of any model tested (including Opus 4.8 and 4.7)

### Data Retention Policy (New for Mythos-Class)
- **30-day mandatory retention** for all traffic on Mythos-class models
- Applies to both first-party and third-party surfaces
- **Not used for training** new Claude models
- **Not used for non-safety purposes**
- **Privacy protections**:
  - Logging all human access to retained data
  - Automatic deletion after 30 days in almost all cases
- **Purpose**: Defend against complex novel attacks (cross-request jailbreaks), identify false positives, improve safeguards

## Project Glasswing & Mythos 5

### Current Status (June 2026)
- **~50 initial partners** expanded to ~150 organizations across 15+ countries
- **10,000+ vulnerabilities** found (high or critical severity) in first month
- **10x bug-finding rate increase** reported by most partners
- **Cloudflare**: 2,000 bugs found (400 high/critical) with better false-positive rate than human testers
- **Mozilla**: 271 vulnerabilities in Firefox 150 (10x more than Opus 4.6 found in Firefox 148)
- **Open Source Scanning**: 1,000+ projects scanned, 6,202 estimated high/critical vulnerabilities found
  - 90.6% true-positive rate after independent assessment
  - 1,094 confirmed as high/critical severity
- **Patch Bottleneck**: Human capacity to triage, verify, and patch is now the limiting factor, not discovery
- **wolfSSL Exploit**: Found certificate-forging vulnerability (CVE-2026-5194) in cryptography library used by billions of devices

### Tools Released
- **Claude Security**: Public beta for Enterprise customers — 2,100+ vulnerabilities patched in 3 weeks using Opus 4.7
- **Cyber Verification Program**: Allows security professionals to use models without certain safeguards for legitimate purposes
- **Skills Library**: Custom instructions for repeated security work
- **Scanning Harness**: Maps codebases, spins up subagents, triages findings, writes reports
- **Threat Model Builder**: Maps codebases to identify attack targets and prioritize work
- **Cisco Foundry Security Spec**: Open-sourced evaluation system for security benchmarking

## Availability & Pricing

### Fable 5 (General Public)
- **Available**: June 9, 2026 worldwide
- **API**: `claude-fable-5` via Claude API
- **Pricing**: $10/1M input tokens, $50/1M output tokens
- **Subscription Plans** (Pro/Max/Team/Enterprise seats):
  - Included at no extra cost through June 22, 2026
  - After June 23: requires usage credits
  - Will be restored as standard part when capacity allows
- **Consumption Plans**: Fully available from day 1

### Mythos 5 (Restricted)
- **Current Access**: Glasswing partners (cyber defenders with cyber safeguards lifted)
- **Biology Access**: Select researchers with biology/chemistry safeguards lifted (cyber safeguards still active)
- **Future**: Broader trusted access program planned
- **US Government Collaboration**: Project Glasswing expansion coordinated with US and allied governments

## Comparison with NEXUS OS Model Pool

### Intelligence Benchmark Alignment
| Model | NEXUS Intelligence Score | Arena Benchmark | Provider Status |
|-------|-------------------------|-----------------|-----------------|
| GLM 5.1 | 0.91 | 1532 WebDev / 1529 Text | Fireworks (UP) |
| Claude Opus 4.6 | 0.91 | ~1480 | Anthropic (UP) |
| Claude Fable 5 | ~0.95+ (estimated) | Not yet in Arena | Anthropic (restricted) |
| Claude Mythos 5 | ~0.95+ (estimated) | Not yet in Arena | Project Glasswing |
| Kimi K2.6 | 0.88 | ~1450 | NVIDIA/Cloudflare (UP) |
| DeepSeek V4 Pro | 0.86 | ~1420 | Fireworks (UP) |
| Qwen 3.6 Plus | 0.86 | ~1410 | Fireworks (UP) |
| GPT-5.5 | ~0.90 | ~1500 | OpenAI (paywalled) |

### NEXOS Routing Implications
1. **No direct Fable 5 access**: Anthropic API requires subscription/credits — not free-tier eligible
2. **Mythos 5 completely inaccessible**: Requires Project Glasswing partnership — not available via standard API
3. **Opus 4.6 fallback**: Available via Anthropic API but lower capability than Fable 5
4. **NEXUS should monitor**: When Fable 5 appears in Arena leaderboards, update intelligence scores
5. **Free-tier alternatives**: GLM 5.1 (Fireworks), Kimi K2.6 (NVIDIA), DeepSeek V4 Pro (Fireworks) remain best free options

## Key Technical Insights for NEXUS OS

### 1. Classifier-Based Routing Pattern (Adoptable)
Fable 5's safety architecture demonstrates a production-grade implementation of classifier-based model routing:
- **NEXUS Can Adopt**: Implement `IntentClassifier` (from Mythos gap analysis) with similar 3-category detection
- **Fallback Routing**: Route risky queries to lower-capability models or require human approval
- **Transparency**: Inform users when fallback occurs (builds trust)
- **Conservative Tuning**: Start broad, narrow based on false-positive data

### 2. Multi-Agent Security Scanning (Applicable)
Mythos Preview's open-source scanning used:
- Codebase mapping agents
- Subagent spawning for parallel scanning
- Triage agents for false-positive filtering
- Report generation agents
- **NEXUS Can Adopt**: Extend DoppelGround with security-focused subagents for code auditing

### 3. Long-Context Memory (Relevant)
Fable 5's 3x improvement with persistent file-based memory suggests:
- **NEXUS Should Implement**: Persistent agent memory across sessions (Vault 5-track memory expansion)
- **File-Based Notes**: Agents should maintain working notes that persist across tasks
- **Self-Improvement**: Agents should review and update their own notes

### 4. Token Efficiency Improvements (Notable)
Fable 5 achieves better results with fewer tokens than previous models:
- **Implication**: As models become more efficient, TokenGuard thresholds may need adjustment
- **NEXUS Should Monitor**: Tokens per task metric as models upgrade

### 5. Data Retention for Safety (Policy Template)
Anthropic's 30-day retention policy with human access logging provides a template:
- **NEXUS Should Adopt**: 30-day retention for all agent interactions
- **Access Logging**: Log all human access to agent reasoning traces
- **Auto-Deletion**: After retention period with SPECI override capability
- **No Training Use**: Explicitly prohibit using operational data for model training

## Limitations & Risks

### 1. False Positive Rate
- Fable 5's conservative classifiers sometimes catch harmless requests
- Biology/chemistry queries are broadly redirected to Opus 4.8 (temporary)
- Anthropic acknowledges this will be frustrating and plans to reduce false positives

### 2. Capacity Constraints
- Subscription plan rollout is conservative due to unpredictable demand
- Usage credits required after June 23 for many users
- API capacity may be limited initially

### 3. Dual-Use Dilemma
- Same capabilities that help cyber defenders can help attackers
- Mythos-class models make exploitation "dramatically cheaper and easier"
- Interim period (vulnerabilities found faster than patched) presents elevated risk
- No company (including Anthropic) claims to have safeguards strong enough to prevent misuse

### 4. Benchmark Saturation
- Mythos Preview saturated nearly all CTF-style cybersecurity benchmarks
- Anthropic considering whether to continue reporting CTF results
- Need for new, more realistic evaluation metrics

## Sources
- Anthropic Official Announcement: "Claude Fable 5 and Claude Mythos 5" (June 9, 2026)
- Anthropic Project Glasswing Update (May 22, 2026)
- Anthropic Claude Mythos Preview System Card (April 2026)
- Partner testimonials: Stripe, GitHub, Cursor, Cognition, IMC, Hebbia, Cloudflare, Mozilla, XBOW
- UK AI Security Institute reports
- ExploitBench and ExploitGym academic benchmarks
- Open Source Security Foundation Alpha-Omega project

---
*Analysis completed: 2026-06-10*
*NEXUS OS Intelligence Assessment*
*Fable 5 Score: Estimated ~0.95+ (pending Arena validation)*
*Mythos 5 Score: Estimated ~0.95+ (not available via public API)*
