# Kilo Snapshot P2 Canonical Doc Queue - 2026-06-08

## Scope

Queue for P2 docs/research/task rows that may become canonical or governed archive entries after review. Archive-only rows are excluded from this queue unless they need promotion.

- Rows: `161`
## Lane Counts

| Lane | Rows |
|---|---:|
| `research` | 82 |
| `wiki` | 20 |
| `coordination` | 14 |
| `operations` | 14 |
| `governance` | 9 |
| `security` | 8 |
| `tasks_review` | 5 |
| `needs_routing` | 4 |
| `reviews` | 3 |
| `docs_governance` | 1 |
| `handbook` | 1 |

## Recommended Actions

| Action | Rows |
|---|---:|
| `review_frontmatter_and_track_or_merge` | 114 |
| `synthesize_or_archive_before_canonical` | 38 |
| `review_active_status_before_tracking` | 5 |
| `route_via_transition_manifest` | 4 |

## Largest Queue Entries

| Lane | Path | Bytes | Lines | Action |
|---|---|---:|---:|---|
| `research` | `docs/research/paper_extracts/safety_at_scale.txt` | 412781 | 5106 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/contamination_generative.txt` | 139375 | 2221 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/multiturn_safety.txt` | 137003 | 2775 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/tree_of_attacks.txt` | 119840 | 1980 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/redbench.txt` | 109747 | 1945 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/survey.txt` | 107667 | 1398 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/trust_benchmarks.txt` | 95513 | 1139 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/redteam_rewards.txt` | 84575 | 1134 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/contamination_benchmark.txt` | 84561 | 1402 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/metasecalign.txt` | 74865 | 1400 | `review_frontmatter_and_track_or_merge` |
| `coordination` | `docs/coordination/QWAVE_TWAVE_ARTIFACT_LEDGER_2026-05-26.json` | 58357 | 1868 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/merging.txt` | 53496 | 1197 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/shortcut_neuron.txt` | 50458 | 1031 | `review_frontmatter_and_track_or_merge` |
| `reviews` | `docs/reviews/NEXUS_OS_STATUS_REPORT.md` | 44253 | 794 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/paper_extracts/dice.txt` | 39283 | 734 | `review_frontmatter_and_track_or_merge` |
| `operations` | `docs/operations/A2A_ZAPIER_MCP_INTEGRATION_ARCHITECTURE.md` | 34240 | 880 | `review_frontmatter_and_track_or_merge` |
| `docs_governance` | `docs/TRANSITION_MANIFEST.md` | 33891 | 433 | `review_frontmatter_and_track_or_merge` |
| `research` | `research/ernie_NEXUS_v3_final_swarm_analysis.txt` | 30839 | 1167 | `synthesize_or_archive_before_canonical` |
| `research` | `research/ernie_swarm_variant_analysis_v5.txt` | 30739 | 1241 | `synthesize_or_archive_before_canonical` |
| `governance` | `docs/governance/IMPROVEMENT_FRAMEWORK_V2.md` | 30180 | 449 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/GROUNDING_SYNTHESIS_2026-06-02.md` | 28179 | 206 | `review_frontmatter_and_track_or_merge` |
| `research` | `research/ernie_swarm_variant_analysis_v4.txt` | 27549 | 1076 | `synthesize_or_archive_before_canonical` |
| `governance` | `docs/governance/ENTERPRISE_GOVERNANCE_MODEL.md` | 27510 | 409 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/compression_merge_ft_approaches.md` | 27443 | 526 | `review_frontmatter_and_track_or_merge` |
| `research` | `docs/research/IMPLEMENTATION_UPGRADE_RECOMMENDATIONS.md` | 26851 | 768 | `review_frontmatter_and_track_or_merge` |

## Rule

Canonical docs need frontmatter/provenance review and duplicate checks. Research intake files should be synthesized before becoming canonical policy. Task files require active-status review before tracking.
