# Grok Task: NEXUS Guard SLM Benchmark Expansion

## Working Mode: CHECKPOINT-BASED
<!-- CANARY: 1bb1ae335bb7ede54560fdd11e53e6f6 -->
Grok loses context mid-task. Each chunk below is self-contained. Always finish a chunk completely, save its output, then signal `NEXT_CHUNK: <n>` at the bottom.

## STATE FILE
Write all progress to: `tasks/grok_benchmark_state.json`
Format: `{"last_completed_chunk": <n>, "reason": "<why stopped>", "results_dir": "research/grok_output/"}`

## CHUNK LIST (8 total, ~30 min each)

### Chunk 1: HuggingFace Discovery
Search HuggingFace for small (~1-3B parameter) safety classifier GGUF models NOT yet tested in guard_slm_report_v3.md (Bonsai-1.7B, Granite-3B-SFT, Llama-Guard-3, Qwen3Guard, SmolLM3, Llama 3.2 3B/1B, Gemma 3 1B tested).
- Use HuggingFace: search "safety classifier GGUF 2B 3B 1B llama guard"
- Exclude: >3.5B params, non-GGUF, broken repos
- Save: `research/grok_output/chunk1_hf_models.jsonl` (model_name, params, quantization, url, reason_to_test)

### Chunk 2: ModelScope Discovery
Search ModelScope.cn for small safety models (Chinese + English).
- Use web search: "modelscope safety classifier small model GGUF"
- Also search: "llama guard GGUF modelscope"
- Save: `research/grok_output/chunk2_modelscope.jsonl`

### Chunk 3: Reddit & Community Discovery
Search Reddit for real-world small guard model recommendations.
- Search: "reddit small llama guard GGUF safety classifier 2B 3B 2025 2026"
- Search: "reddit best small model content moderation offline"
- Focus on models people actually use in production
- Save: `research/grok_output/chunk3_reddit_recommendations.md`

### Chunk 4: Air-Gapped Docker Lab Design
Research Docker-based sterile lab for AI safety testing.
- Best practices: --cap-drop=ALL, --network=none, read-only rootfs
- Windows Docker Desktop: host.docker.internal for Ollama
- no-new-privileges, seccomp profiles
- Document a complete docker run command
- Save: `research/grok_output/chunk4_lab_design.md`

### Chunk 5: Smoke Test Candidates
From Chunk 1-3 results, select the 3 most promising models.
- Criteria: <3.5B params, GGUF available, SAFE/UNSAFE output format likely
- Note: these will be pulled and tested by the main agent later
- Save: `research/grok_output/chunk5_top_candidates.json`

### Chunk 6: Dockerfile + Entrypoint
Based on Chunk 4, write Dockerfile and docker-compose.yml
- Base python:3.13-slim
- Read-only mount for scripts/
- Output volume writeable
- No curl, wget, netcat, build-essential
- Entrypoint that validates isolation
- Save: `research/grok_output/chunk6_lab_docker/` directory

### Chunk 7: Test Procedure for Novel Sets
Design the exact test procedure for the novel_scenario_templates.py pipeline inside Docker.
- Which templates to generate (specify countPerTemplate)
- Which mutation types
- How to validate output is sterile (no host leaks)
- Save: `research/grok_output/chunk7_test_procedure.md`

### Chunk 8: Final Report
Merge all chunks into a single PDF-ready markdown report.
- Summary of discovered models
- Docker lab specification
- Test procedure
- Next steps for the main agent
- Save: `research/grok_output/guard_benchmark_expansion_phase2.md`

## INPUT FILES TO READ
- `datasets/guard_slm_report_v3.md` — current benchmark state, tested models
- `scripts/stresslab_v7/novel_scenario_templates.py` — what the novel pipeline generates
- `scripts/stresslab_v7/run_novel_pipeline.py` — how it runs

## RULES
1. Complete ONE chunk per session/message
2. Save output AFTER each chunk
3. Write state BEFORE stopping
4. If interrupted, read state file and resume at last_completed_chunk + 1
5. Do NOT modify any files outside `research/grok_output/` and `tasks/grok_benchmark_state.json`
6. Do NOT pull or install anything on the system
7. All work is research + writing only

## SIGNAL
When you finish a chunk, output: `NEXT_CHUNK: <n+1>` where n is the chunk you just completed.
When you finish all 8: `ALL_DONE`
