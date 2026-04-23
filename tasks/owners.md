# NEXUS OS — Team Ownership Matrix v3.2
# Accurate as of 2026-04-23

## Philosophy
Every compartment is a research lab. Every team gives suggestions, reports,
optimizations, deep searches, and brainstorms. No one is "just an executor."

## Team Matrix

| Rank | Team                  | Core Strength                          | Primary Responsibility                                                | Backup        | Max Tasks |
|------|-----------------------|-----------------------------------------|-----------------------------------------------------------------------|---------------|-----------|
| 1    | **SPECI**             | One above all                           | Strategy, final decisions, overall coordination                       | —             | 2         |
| 2    | **NEO**               | Engineer mind + detective precision      | Docker/VM control, local Linux safety, pipeline improvement, deep analytics | CODEX         | 3         |
| 3    | **CODEX**             | Fastest implementer + plan runner        | Execute ready plans, TASK layer, daily/cron automations, scheduled jobs | NEO           | 4         |
| 4    | **META**              | Best researcher + scientific advisor     | Deep research, scientific coordination, high-detail analysis         | GLM Team      | 3         |
| 5    | **GROK 4.3**          | High specialized expert team            | Complex planning, solution creation, technical reality check           | Research Lab  | 3         |
| 6    | **GLM5 / GLM5.1**     | Full-stack dashboard masters             | Dashboard development (2 prototypes → future fusion)                   | META          | 3         |
| 7    | **Zo Cloud Comp**     | Cloud solutions + OpenClaw               | Cloud infra, active layer comm, autonomous advantages, T4 16GB VRAM     | Windows       | 2         |
| 8    | **Kiro / Kilocode**   | Custom Azure agent creators              | OPUSman + Grok 4.2 agents, benchmark + training (Swiss pocket knife)   | NEO           | 2         |
| 9    | **QWEN3.6 + DEEPSEEK**| Expert technical reviewers              | Final review, deep code/architecture analysis (last line of defense)   | GROK 4.3      | 2         |
| 10   | **Antigravity Gemini**| Security + governance specialist        | Security checks, governance validation, finding odd parts            | SPECI         | 2         |
| 11   | **Kimi 2.6**          | Slow but extremely valuable             | Deep reasoning when stabilized (high quality, low speed)             | META          | 1         |
| 12   | **Mimo v2.5 + Mimo Claw** | Cutting-edge latest models          | Fast swarm sessions, convenient high-speed jobs                       | CODEX         | 2         |
| 13   | **OPENcode Models**   | High-volume autonomous capacity         | Future collective autonomous task sharing                            | CODEX         | —         |

## Infrastructure

### Canonical Ports
- 7352 → Governance API (PRIMARY)
- 7353 → TWAVE wrapper (read-only)
- 7354 → Mock/fallback (dev only)

### Local Models (Ollama — Zero Cost)
- Primary: qwen2.5-coder:7b, gemma4:e2b, nemotron-3-nano:4b
- Special: deepseek-r1:8b (reasoning), osman-fast (hot path)
- Strategy: Local-first. Cloud only when tier demands it.

### Cloud Resources
- Zo Computer: primary cloud compute + OpenClaw installation center
- Lightning.ai T4: 16GB VRAM free tier for benchmark/training runs

## Task Queue Rules
1. Only SPECI creates new tasks
2. All agents check tasks/pending/ before any work
3. Claim via task_queue.py
4. Never work outside the official task queue
5. No agent creates branches or changes architecture independently

## Cold Start
Run coldstart_install.py once → then uvicorn on 7352 → read COLDSTART_BOOT.txt