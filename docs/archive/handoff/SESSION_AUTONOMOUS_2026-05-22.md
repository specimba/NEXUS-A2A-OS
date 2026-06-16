---
id: NODE-MIG-SESSION_AUTONOMOUS_2026_05_22
authority_scope: experimental
origin_sha256: 29862294face92b4a3f1ff9cda8aa67fd1cc53837f7d375925becd6afca4af3e
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-7CDFD1
---
<!-- CANARY: 8a9c5a2a3202f6dc6887cd4c1f38be6c -->
{
  "timestamp": "2026-05-22T22:38:00",
  "agent": "opencode",
  "session_type": "autonomous",
  "status": "awaiting_user_return",
  "total_evaluations": 2352,
  "accomplished": [
    "BOUNCER benchmark: 3 RP models x 2 prompts x 92 queries = 552 evaluations (0 crashes)",
    "BOUNCER v3 prompt: Fixed 2 FPs (weather, chocolate cake) → 0 FPs",
    "Special-Virus v7 score: 68% → 96% (28pp improvement from prompt engineering alone)",
    "Guard ensemble with Special-Virus: 1200 evaluations, 0 FPs, beats Bonsai on Vacuum (72% vs 68%)",
    "600 mutated scenario benchmark: 79.2% overall detection rate",
    "22-model comparison table updated in guard_slm_report_v3.md",
    "Neo_T-Virus identified as completion-only (no chat template) - unsuitable",
    "Docker sterile lab built, mergekit installed"
  ],
  "files_created_or_updated": [
    "docs/research/BOUNCER_RP_MODEL_ANALYSIS_2026-05-22.md",
    "datasets/guard_slm_report_v3.md (updated with 22-model table + ensemble comparison)",
    "datasets/bouncer_bench_robust.py (v2 - checkpointed, crash-proof)",
    "datasets/bouncer_bench_v3_fixed.py (v3 - FP-fixed prompt)",
    "datasets/guard_ensemble_special_virus.py",
    "datasets/bench_mutated.py",
    "datasets/bouncer_checkpoints/ (all checkpoint files)",
    "models/guards/guard_ensemble_report_special_virus.json",
    ".nexus_pi/state/session_compact.json"
  ],
  "key_discoveries": {
    "best_1B_guard": "Special-Virus-3.2-1B + BOUNCER v3 prompt",
    "results": "75% TAMAS, 96% v7, 0 FPs, 79.2% on 600 mutated",
    "prompt_lesson": "Explicitly listing SAFE categories improved UNSAFE detection by 28pp (paradoxical calibration effect)",
    "guard_ensemble": "Matches Bonsai on MCP (94.7%), Gov (100%), Gray (88%); beats on Vacuum (72% vs 68%)"
  },
  "pending_work": [
    "Build NEXUS-SLERP-X merge (mergekit installed, needs HF model conversion)",
    "Full novel pipeline with mutation (needs qwen2.5:1.5b pull)"
  ]
}
