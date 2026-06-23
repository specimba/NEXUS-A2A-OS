# PAPERS09 + MODEL CURATION BRIEF — 2026-06-21

Source inventory verified:
- `/mnt/c/Users/speci.000/Downloads/ARCHIVIST/PAPERS/papers09`
- `/mnt/c/Users/speci.000/Downloads/ARCHIVIST/2006fancyMODELSandNewPaPeRs.txt`

## Verified Inventory

- 80 PDFs confirmed
- 1 TXT confirmed
- 8 PNG workflow/ref-table images confirmed
- 1 extra TXT methods file confirmed

## Curation: High-Upside Clusters for NEXUS

### 1. Reasoning + Planning
- How Transformers Learn to Plan via Multi-Token Prediction
- Training Large Language Models to Reason in a ...
- VibeThinker-3B Exploring the Frontier of Verifiable Reasoning
- Deciphering Trajectory-Aided LLM Reasoning
- L1 Controlling How Long A Reasoning Model Thinks

NEXUS relevance: Brain API routing, model-selection policy, cost-aware reasoning budgets.

### 2. Safety + Jailbreak Defense
- SafeDecoding Defending against Jailbreak Attacks
- GUARD-SLM Token Activation-Based Defense Against ...
- SoK Evaluating Jailbreak Guardrails for Large Language Models
- SoK Robustness in Large Language Models against Jailbreak Attacks
- Jailbreak and Guard Aligned Language Models
- Adversarial Reframing A Framework for Targeted ...
- State-Dependent Safety Failures in Multi-Turn Language Model Interaction
- Assessing Automated Prompt Injection Attacks in Agentic ...

NEXUS relevance: Governor/KAIJU gates, AEGIS filters, prompt-injection defenses, guard-pipeline tuning.

### 3. SWE / Agentic Coding
- SWE-LEGO PUSHING THE LIMITS OF SUPERVISED ...
- SWE-Master Unleashing the Potential of Software ...
- SWE-TRACE OPTIMIZING LONG-HORIZON SWE ...
- SWE-World Building Software Engineering Agents in ...
- FastContext Training Efficient Repository Explorer for ...
- daVinci-Env Open SWE Environment Synthesis at Scale
- Pull Requests as a Training Signal for Repo-Level Code Editing

NEXUS relevance: NEXUSCLAW worker quality, task-router capability taxonomy, benchmark inputs.

### 4. Memory + Context Compression
- AllMem A Memory-centric Recipe for Efficient ...
- Hybrid Associative Memories
- Context Compression for LLM Agents
- Scratchpad Patching Decoupling Compute from ...
- TokSuite MEASURING THE IMPACT OF TOKENIZER ...

NEXUS relevance: Vault memory channel tuning, MemPalace/Squeez upgrade signal.

### 5. Efficiency / Speculative Decoding / Benchmarks
- Fast Inference from Transformers via Speculative Decoding
- SPEED-Bench A Unified and Diverse Benchmark for Speculative Decoding
- Lightning OPD Efficient Post-Training for Large ...
- Risk Under Pressure Compute-Aware Evaluation of ...
- Roofline An Insightful Visual Performance Model

NEXUS relevance: GMR circuit breaker thresholds, TWAVE lane suitability, benchmark hygiene.

### 6. Math + Code Specialist Models
- AceReason-Nemotron Advancing Math and Code
- QWEN2.5-MATH TECHNICAL REPORT
- HARDER IS BETTER BOOSTING MATHEMATICAL ...

NEXUS relevance: domain-routing map in ModelRelay/GMR.

### 7. GLM-5 + Agentic Engineering
- GLM-5 from Vibe Coding to Agentic Engineering

NEXUS relevance: external advisor lane, dashboard/backend integration target.

## New Models / API-Ready Curation

### LongCat API
- Endpoint: https://api.longcat.chat/openai/v1 and /anthropic/v1
- Compatibility: OpenAI + Anthropic formats
- Model: LongCat-2.0-Preview
- Quota: Beta limited
- Ready-to-use codex/opencode config documented in txt

### Microsoft FastContext-1.0-4B-SFT
- Repo: https://github.com/microsoft/fastcontext
- HF: https://huggingface.co/microsoft/FastContext-1.0-4B-SFT
- NEXUS lane candidate: local agent/repo-context worker via Ollama lane 11436

### SWE-Lego + SWE-Review-8B + Terminal-Lego-Qwen3-8B
- HF: https://huggingface.co/SWE-Lego
- NEXUS relevance: SWE task decomposition and review lane

### VibeThinker-1.5B / 3B
- HF: https://huggingface.co/WeiboAI/VibeThinker-1.5B
- HF: https://huggingface.co/WeiboAI/VibeThinker-3B
- Paper: https://arxiv.org/pdf/2606.16140
- NEXUS lane candidate: lightweight reasoning edge model

### Nanbeige4.1-3B
- HF: https://huggingface.co/Nanbeige/Nanbeige4.1-3B
- Paper: https://arxiv.org/pdf/2602.13367
- Status: small generalist with reasoning/alignment/actions claims

### TFPI / Thinking-Free Policy Initialization
- Paper: https://arxiv.org/pdf/2509.26226
- HF: https://huggingface.co/collections/xx18/tfpi
- NEXUS relevance: distillation-safe reasoning routes and control-plane efficiency

### Nex-N2 family
- HF: https://huggingface.co/huihui-ai/Huihui-Nex-N2-mini-abliterated
- HF: https://huggingface.co/edougawa/Nex-N2-mini-Abliterated
- K8s/GGUF/abliterated variants noted; policy-relevant artifact set
- NEXUS action: audit only, do not import without provenance review

### WildClawBench + MolmoMotion-4B-H3-F30
- Dataset: https://huggingface.co/datasets/internlm/WildClawBench
- Model: https://huggingface.co/allenai/MolmoMotion-4B-H3-F30
- NEXUS relevance: benchmark and embodied/agentic research inputs

### Gemma-4-E4B-it-Heretic-QAT-GGUF
- HF: https://huggingface.co/SC117/gemma-4-E4B-it-heretic-QAT-GGUF
- NEXUS action: treat as untrusted third-party GGUF; no automatic adoption

## Recommended NEXUS Actions (Bounded)

1. Add to model curation registry:
   - LongCat-2.0-Preview
   - FastContext-1.0-4B-SFT
   - VibeThinker-3B
   - Nanbeige4.1-3B
   - Nex-N2-mini variants (audit only)

2. Create one intake task:
   - papers09 title-to-lane mapping table
   - LongCat provider entry in registry
   - FastContext local Ollama test entry

3. Defer until approved:
   - full PDF extraction
   - code/model imports
   - provider key handling

## Risk Notes

- No destructive action taken
- No PDF text extracted in this pass due to runtime block
- Model links are evidence inputs only; no execution or download commands run
- Nex-N2/Gemma QAT GGUF variants require provenance and safety review before NEXUS registry adoption
