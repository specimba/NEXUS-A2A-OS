---
id: NODE-MIG-MEMORY_CHECKPOINT_CURRENT
authority_scope: experimental
origin_sha256: 007581e3a8b07b111fe520b64cc312b0412c464593ff3453985075e9a6a1f196
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-12298B
---
# RESEARCH MEMORY CHECKPOINT

**Date**: 2026-05-20  
**Purpose**: Continuity-aware state capture — read this first when resuming MCP security research, governance model development, or architecture work.

<!-- CANARY: 197c9493a45f214092b340e559c50688 -->
---

## Current State

### Completed
1. **RED-BLUE-PURPLE library staged**: 284MB zip, ~55 papers + 25 JSONL stress datasets (200K+ records, gitignored)
2. **7-layer enterprise governance model** written at `docs/research/ENTERPRISE_GOVERNANCE_MODEL.md`
3. **4 new arXiv MCP security papers** downloaded, extracted (PyMuPDF), and deep-analyzed:
   - `arXiv_2504_08623_Enterprise_MCP_Security` — enterprise mitigation framework
   - `arXiv_2509_24272_When_MCP_Servers_Attack` — 12-category attack taxonomy, cross-host/LLM ASR
   - `arXiv_2503_23278_MCP_Landscape_Threats` — 4-phase lifecycle, 16 threat scenarios
   - `arXiv_2510_16558_First_Look_MCP_Security` — 67K server registry analysis, MCPInspect tool
4. **Cross-reference analysis** written at `docs/research/MCP_SECURITY_PAPERS_2026-05-20.md`

### Critical Empirical Data
| Finding | Source | Implication |
|---|---|---|
| 6 attack categories at 100% ASR | Paper 2 | No single defense works |
| Existing scanners detect 3.3% | Paper 2 | Must build own detection |
| 833/67K servers vulnerable | Paper 4 | 1.24% of ecosystem compromised |
| 212 hijackable accounts | Paper 4 | Registry supply chain is active threat |
| All 4 hosts lack tool verification | Paper 4 | Architectural gap in all current hosts |
| System prompts > model capability | Paper 2 | Host design matters more than LLM choice |
| Gemini identifies but follows attacks | Paper 4 | Safety awareness ≠ safety enforcement |

### Stress Datasets (200K+ records)
- `nexus_frontier_v5_mcp_contamination.jsonl` — 3,000 MCP tool contamination attacks
- `nexus_frontier_v5_gov_bypass.jsonl` — 3,000 governance bypass attacks
- `nexus_frontier_v5_memory_poison.jsonl` — 3,000 memory poisoning attacks
- `nexus_frontier_v5_jailbreak.jsonl` — 2,000 jailbreak attacks
- `nexus_stress_v6_tamas_base.jsonl` — 684 multi-agent attack records
- `nexus_stress_v6_tool_scored_thermo_fine_tuning.jsonl` — 5,760 tool-scored attacks
- Plus 19 more files in `research/Papers/RED-BLUE-PURPLE/`

### Papers on Disk (PDF + extracted .txt)
Location: `research/Papers/RED-BLUE-PURPLE/`
- `arXiv_2504_08623_Enterprise_MCP_Security.pdf` + .txt (54K chars, 1,229 lines)
- `arXiv_2509_24272_When_MCP_Servers_Attack.pdf` + .txt (72K chars, 1,660 lines)
- `arXiv_2503_23278_MCP_Landscape_Threats.pdf` + .txt (155K chars, 2,637 lines)
- `arXiv_2510_16558_First_Look_MCP_Security.pdf` + .txt (80K chars, 1,758 lines)

### Baseline Evaluation (proof that defenses are trivially weak)
- `nexus_governance_score.py` — keyword-based scoring script (needs replacement)
- `governance_eval_results.json` — scores ~0.034-0.116

### Key Gaps (uncovered by any paper)
- Memory poisoning detection in agent conversation history
- Cross-agent collusion across different MCP server providers
- Long-horizon behavioral baseline anomaly detection
- Delegation chain tracking across multi-hop MCP calls
- Quantitative defense rate measurement against v5/v6 stress datasets

## Next Steps (Prioritized)

### Phase 1: Empirical Baseline (Do First)
1. Run TrustKernel against v5 MCP contamination dataset → measure current defense rate
2. Run TrustKernel against v5 jailbreak dataset
3. Establish baseline stacked defense rate (target: measure what we have before building more)

### Phase 2: Paper-Driven Improvements
4. Add **registry-level pre-integration checks** (Paper 4's MCPInspect approach)
5. Implement **host-independent tool verification** (Paper 4 finding: no host does this)
6. Add **system prompt hardening** (Paper 2 finding: system prompts > model capability)
7. Build **A3 init-logic sandbox** for MCP servers (Paper 2: 100% ASR on init attacks)

### Phase 3: Novel Defenses (Gap Coverage)
8. Memory poisoning detection (not covered by any paper)
9. Cross-agent collusion detection (not covered by any paper)
10. Long-horizon behavioral baselines (L7 implementation)
11. Delegation chain tracking for multi-hop MCP (L2 implementation)

### Phase 4: Validation
12. Run full 200K+ stress dataset suite → measure stacked defense rate
13. Iterate on weak layers until 80%+ defense achieved
14. Write results to governance model doc

## Architecture Context
- **TrustKernel** at `nexus_os/governor/trust_kernel.py` (631 lines) — event-sourced Bayesian trust, SQLite
- **MCP bridge** at `nexus_os/mcp/server.py` (494 lines) — governed MCP with auth scaffold
- **TWAVE v2.0** at `nexus_os/twave/` — ChimeraRouterV2, LandauGinzburgTrackerV2
- **7-layer model** at `docs/research/ENTERPRISE_GOVERNANCE_MODEL.md`
- **All papers + datasets**: gitignored, local only at `research/Papers/RED-BLUE-PURPLE/`

## Quick Commands
```powershell
# Re-extract PDF text (if needed):
python -c "import fitz; [fitz.open(f).save(...) for f in glob('*.pdf')]"

# Run governance scoring:
python research/Papers/RED-BLUE-PURPLE/nexus_governance_score.py

# Run stress test live:
python benchmarks/stress_test_live.py
```