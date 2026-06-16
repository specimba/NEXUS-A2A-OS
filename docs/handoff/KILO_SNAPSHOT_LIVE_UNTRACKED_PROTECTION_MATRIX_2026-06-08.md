# Kilo Snapshot Live-Untracked Protection Matrix - 2026-06-08

## Scope

Input: `docs/handoff/KILO_SNAPSHOT_BYTE_COMPARE_HIGH_VALUE_2026-06-08.json`.

This matrix covers files where Kilo has an older snapshot blob, the live filesystem file exists, and the current Git index does not track it. These are not restore targets. They are live work/assets that need protection, canonical intake, archive policy, or ignore policy.

Total live-untracked changed files: `828`.

CSV matrix: `docs/handoff/KILO_SNAPSHOT_LIVE_UNTRACKED_PROTECTION_MATRIX_2026-06-08.csv`.

Sensitive-looking paths remain redacted in this matrix. Review those locally before any public tracking or documentation.

## Risk Summary

| Risk | Count |
|---|---:|
| `P2_knowledge_data` | 624 |
| `P3_manual` | 115 |
| `P0_sensitive` | 46 |
| `P4_generated` | 26 |
| `P2_model_asset` | 11 |
| `P1_code_agent` | 6 |

## Proposed Action Summary

| Action | Count |
|---|---:|
| `research_intake_archive_or_canonicalize` | 225 |
| `dataset_benchmark_registry_preserve_do_not_track_blindly` | 221 |
| `canonical_doc_review_track_or_archive` | 173 |
| `review_script_then_track_or_archive` | 115 |
| `sensitive_hold_secret_scan_before_any_public_tracking` | 46 |
| `generated_cache_ignore_or_quarantine_after_review` | 26 |
| `model_registry_or_D_archive_do_not_git_track_weights` | 11 |
| `git_intake_review_high_value_source_or_agent_config` | 6 |
| `operator_task_review_track_if_active` | 5 |

## Prefix Summary

| Prefix | Count | Live MiB |
|---|---:|---:|
| `docs` | 187 | 6.11 |
| `datasets` | 143 | 7.14 |
| `benchmarks` | 135 | 35.19 |
| `research` | 129 | 34.42 |
| `models` | 88 | 0.42 |
| `logs` | 46 | 1.38 |
| `.agents` | 39 | 0.19 |
| `upload` | 38 | 1.46 |
| `evidence` | 11 | 0.25 |
| `tasks` | 6 | 0.02 |
| `nexus_os` | 3 | 0.01 |
| `tests` | 3 | 0.01 |

## Kind Summary

| Kind | Count |
|---|---:|
| `docs_or_research` | 403 |
| `data_or_benchmark` | 221 |
| `source_or_script` | 121 |
| `sensitive_path` | 46 |
| `generated_or_cache` | 26 |
| `model_or_weight` | 11 |

## First High-Value Non-Sensitive Rows

| Risk | Action | Path | Live bytes |
|---|---|---|---:|
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `nexus_os/__main__.py` | 2293 |
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `nexus_os/cli.py` | 4869 |
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `nexus_os/stresslab/__init__.py` | 212 |
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `tests/claw/test_config_integrity.py` | 3775 |
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `tests/claw/test_locks.py` | 3399 |
| `P1_code_agent` | `git_intake_review_high_value_source_or_agent_config` | `tests/claw/test_store.py` | 2903 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/README.md` | 5491 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/SKILL.md` | 29362 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/mcp-configure/SKILL.md` | 14809 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/mcp-configure/references/mcp-config-templates.md` | 8242 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/mcp-configure/references/mcp-ui-links.md` | 3693 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/1.8-summary.md` | 7750 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/1.9-editor-rules.md` | 10834 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/recipes.md` | 24065 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/android-client-sdk.md` | 4253 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/apex-server-sdk.md` | 750 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/browser-frameworks-sdk.md` | 1079 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/cpp-client-sdk.md` | 969 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/cpp-server-sdk.md` | 728 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/dotnet-client-sdk.md` | 1240 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/dotnet-server-sdk.md` | 3524 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/edge-sdks.md` | 1943 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/electron-client-sdk.md` | 908 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/erlang-server-sdk.md` | 889 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/flutter-client-sdk.md` | 1304 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/go-server-sdk.md` | 2245 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/haskell-server-sdk.md` | 919 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/ios-client-sdk.md` | 4782 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/java-server-sdk.md` | 3587 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/javascript-browser-sdk.md` | 2747 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/lua-server-sdk.md` | 1054 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/node-client-sdk.md` | 1017 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/node-server-sdk.md` | 3008 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/php-server-sdk.md` | 847 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/python-server-sdk.md` | 2921 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/react-native-sdk.md` | 2916 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/react-web-sdk.md` | 2911 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/roku-client-sdk.md` | 718 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/ruby-server-sdk.md` | 934 |
| `P2_knowledge_data` | `research_intake_archive_or_canonicalize` | `.agents/skills/onboardingv2/references/sdk/snippets/rust-server-sdk.md` | 866 |

## Operator Decision

- Do not purge Kilo yet.
- Do not git-add this whole matrix blindly.
- First protect `P1_code_agent` rows, then canonicalize docs/research/tasks, then create dataset/model archive manifests.
- Sensitive-hold rows require local secret scan before any public commit or cloud sync.
