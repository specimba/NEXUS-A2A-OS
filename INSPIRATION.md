# NEXUS OS — Inspiration Research

Sourced from deep search 2026-04-20. Full references at bottom.

---

## Agent Orchestration Frameworks

### Top Tier — Production-grade, active development

| Framework | Language | License | Stars | Key Differentiator |
|-----------|----------|---------|-------|--------------------|
| **Agency Swarm** | Python | MIT | — | Extends OpenAI Agents SDK, explicit comm flows, type-safe tools |
| **AgentEnsemble** | Python | MIT | — | Async-first, 9 agent types (ReAct/Swarm/Pipeline/Debate/Router/Planner), hooks+retries |
| **Maestro** | Python | — | — | MCP server CLI, streaming API, DOCKER/K8s deploy |
| **MOCO** | Python | — | — | Multi-provider (Gemini/OpenAI/OpenRouter), FAISS memory, moco CLI |
| **Agentflow** | Python | — | v0.5.7.0 | 3-layer memory (short/convo/long-term), pg+redis checkpointer, graph DSL |
| **mesh** | Python | — | — | Mermaid visualization, Vel translation layer, token streaming |
| **pydantic-collab** | Python | — | — | Pydantic-typed agent graphs, topology validation, observability |
| **self-evolving-agent** | Python | MIT | — | OpenClaw-based, capability map + promotion gates, 6-mode system |

### Alternative — Notable patterns

| Framework | Notes |
|-----------|-------|
| **Agent Squad** | AWS-backed, SupervisorAgent for parallel coordination |
| **agenticaiframework** | 400+ modules, 237 components, enterprise-grade |
| **vibex-py** | YAML agent definitions, natural language handoffs, event stream |
| **OpenClaw** | Tailscale-first networking, mcporter MCP bridge, persistent agents |

---

## Memory Layer Systems

### Top Tier — Structured, production-ready

| System | Type | License | Language | Key Differentiator |
|--------|------|---------|----------|--------------------|
| **MemoryLayer** | Graph+Vector | — | Python | 60+ typed relationships, recursive LLM reasoning, MCP server |
| **MemMachine** | Episodic/Profile | Apache 2.0 | Python | Graph-based episodic, profile SQL, working memory |
| **Engram-Mem** | Dual (Vector+Graph) | MIT | Python | Qdrant + NetworkX, Ebbinghaus decay, federated search |
| **memweave** | Vector+Keyword | MIT | Python | SQLite only, BM25+vec hybrid, markdown files, offline |
| **0GMem** | Structured Graph | MIT | Python | Entity+temporal+semantic edges, LoCoMo 88.67% accuracy |
| **memvid** | Vector | — | Rust | Single-file immutable, sub-5ms recall, capsule contexts |
| **mnemora** | 4-type (W/S/E/P) | — | Python | AWS DynamoDB+Aurora pgvector+S3, LangGraph/LangChain/CrewAI |

### Alternative — Lighter weight

| System | Notes |
|--------|-------|
| **MemoryKit** | Local ChromaDB, recency+importance scoring, 5-line API |
| **bolnet/agent-memory** | SQLite+pgvector+Neo4j, 3-layer retrieval pipeline |

---

## Skill Crafting Systems

### Top Tier — Self-improving, automated synthesis

| System | License | Language | Key Differentiator |
|--------|---------|----------|--------------------|
| **EvoSkill** | MIT | Python 3.12+ | Evolutionary loop over agent configs, git-branch frontier |
| **SkillX** | — | Python | 3-level hierarchy (Planning/Functional/Atomic), automated KB construction |
| **SkillCraft** | — | Python 3.10+ | Benchmark for skill formation, caching, composition evaluation |
| **ACE (kortix-ai)** | — | Python | Skillbook of strategies, 20-35% perf improvement claimed |
| **SkillWeaver** | MIT | Python | Web agents, autonomous skill synthesis as APIs |
| **skill-evolution** | MIT | Python | Full lifecycle (create/reflect/evaluate/publish/install/fork/merge) for Claude Code |

### Alternative — OpenClaw ecosystem

| System | Notes |
|--------|-------|
| **self-evolving-agent** | OpenClaw runtime, capability-centric memory, promotion gates |
| **openclaw/skills** | Modular skill framework, `.learnings` dir, hooks system |

---

## Implementation Priority Order

### Phase 1 — Immediate (leverage existing Zo primitives)
1. **memory layer** → `memweave` (zero infra, SQLite, markdown-native — perfect for this env)
2. **skill crafting** → `skill-evolution` (Claude Code oriented, full lifecycle engine)
3. **heartbeat** → `heartbeat.md` (already drafted, integrate with NEXUS OS)

### Phase 2 — Core NEXUS integration
4. **GMR sub-agent spawn** → Wire `/zo/ask` API into `GMR.spawn()` method
5. **Vault → memweave** → Replace in-memory Vault with persistent memweave store
6. **skill-evolution** → Integrate into NEXUS OS `swarm` for automated skill discovery

### Phase 3 — Advanced orchestration
7. **MemoryLayer** → For graph-backed multi-hop reasoning over agent memories
8. **AgentEnsemble** → For async multi-agent pipelines with hooks
9. **EvoSkill** → For evolutionary improvement of NEXUS agent configs

---

## References

[^1]: Agency Swarm — https://github.com/VRSEN/agency-swarm
[^2]: AgentEnsemble — https://github.com/irfanalidv/AgentEnsemble
[^3]: Maestro — https://github.com/AI4quantum/maestro
[^4]: MOCO — https://github.com/moco-ai/moco
[^5]: Agentflow — https://github.com/10xHub/Agentflow
[^6]: mesh — https://github.com/rscheiwe/mesh
[^7]: pydantic-collab — https://github.com/boazkatzir/pydantic-collab
[^8]: self-evolving-agent — https://github.com/RangeKing/self-evolving-agent
[^9]: MemoryLayer — https://github.com/scitrera/memorylayer
[^10]: MemMachine — https://github.com/MemMachine/MemMachine
[^11]: memweave — https://github.com/sachinsharma9780/memweave
[^12]: 0GMem — https://github.com/0gfoundation/0gmem
[^13]: memvid — https://github.com/memvid/memvid
[^14]: Engram-Mem — https://github.com/docaohieu2808/Engram-Mem
[^15]: mnemora — https://github.com/mnemora-db/mnemora
[^16]: EvoSkill — https://github.com/sentient-agi/EvoSkill
[^17]: SkillX — https://github.com/zjunlp/SkillX
[^18]: SkillCraft — https://github.com/shiqichen17/SkillCraft
[^19]: ACE — https://github.com/kortix-ai/kortix-ace
[^20]: SkillWeaver — https://github.com/OSU-NLP-Group/SkillWeaver
[^21]: skill-evolution — https://github.com/hao-cyber/skill-evolution
