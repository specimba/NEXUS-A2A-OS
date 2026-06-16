# Kilo Snapshot P2 Dataset/Benchmark Manifest - 2026-06-08

## Scope

Manifest for P2 dataset/benchmark rows and research data mirrors. This is a registry input only; it does not stage or move payloads.

- Rows: `262`
- Canonical candidates: `213`
- Duplicate mirror/reference rows: `49`
- Duplicate blob groups: `40`

## Prefix Counts

| Prefix | Rows |
|---|---:|
| `benchmarks` | 124 |
| `research` | 82 |
| `datasets` | 56 |

## Largest Payloads

| Role | Path | Bytes | Lines | Duplicate Group |
|---|---|---:|---:|---:|
| `canonical_candidate` | `benchmarks/stress_lab/nexus_frontier_v5_mcp_contamination.jsonl` | 2072452 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_mcp_contamination.jsonl` | 2072452 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_mcp_contamination.jsonl` | 2072452 | 3000 | 3 |
| `canonical_candidate` | `benchmarks/stress_lab/nexus_novel_cross_category_v4.jsonl` | 2054825 | 3000 | 1 |
| `canonical_candidate` | `benchmarks/stress_lab/nexus_frontier_v5_gray_area.jsonl` | 2032828 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_gray_area.jsonl` | 2032828 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_gray_area.jsonl` | 2032828 | 3000 | 3 |
| `canonical_candidate` | `benchmarks/stress_lab/nexus_frontier_v5_memory_poison.jsonl` | 1950161 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_memory_poison.jsonl` | 1950161 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_memory_poison.jsonl` | 1950161 | 3000 | 3 |
| `canonical_candidate` | `benchmarks/eggroll/scienceqa_foundry.jsonl` | 1947876 | 1000 | 1 |
| `canonical_candidate` | `benchmarks/do_kb/celestia_kb_baseline.jsonl` | 1872541 | 401 | 1 |
| `canonical_candidate` | `benchmarks/stress_lab/nexus_frontier_v5_gov_bypass.jsonl` | 1826084 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_gov_bypass.jsonl` | 1826084 | 3000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_gov_bypass.jsonl` | 1826084 | 3000 | 3 |
| `canonical_candidate` | `benchmarks/stress_lab/eggroll_code_reasoning_supplement.jsonl` | 1755651 | 3500 | 1 |
| `canonical_candidate` | `datasets/benign_from_cyber.jsonl` | 1680468 | 1000 | 1 |
| `canonical_candidate` | `benchmarks/stress_lab/nexus_frontier_v5_jailbreak.jsonl` | 1532591 | 2000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/RED-BLUE-PURPLE/nexus_frontier_v5_jailbreak.jsonl` | 1532591 | 2000 | 3 |
| `duplicate_mirror_reference` | `research/papers01/RED-BLUE-PURPLE/nexus_frontier_v5_jailbreak.jsonl` | 1532591 | 2000 | 3 |

## Rule

Track manifests, schemas, and small representative samples first. Do not track duplicate JSONL mirrors under both `benchmarks/` and `research/`; choose one canonical data location and reference duplicates by `live_blob`.
