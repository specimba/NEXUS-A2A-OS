# NEXUS × Intern A100 × HF × Discovery — combined research map

**Stamp:** long-session 2026-07-15  
**Machine:** nb-582b5f51 NEXUS-GPU-test2 A100-80G (operator renewed +2h → ~4h window)  
**Quota clarification:** Grok **weekly** chat quota ≠ GPU 算力点/续时长. GPU spend is renew-hours × 60点/小时 (you had 544 points remaining).

## 1. Hugging Face CLI / Hub
| Location | Status |
|----------|--------|
| Windows / Hermes host | **Installed** `huggingface_hub` 1.23.0 + datasets; whoami **specimba** |
| WSL python3 | No pip/ensurepip on default interpreter — use Windows python or A100 venv |
| A100 `/data/NEXUS/venvs/nexus_hf` | Install job driven via CDP (see logs/hf_simple_run.log, LONG_SESSION_REPORT) |
| Cache | Prefer `/data/NEXUS/hf_cache` on JuiceFS |

**Security:** HF token was pasted in chat — rotate after session if this log is shared. On A100 store only under `/data/NEXUS/.secrets/hf_token` mode 600.

## 2. Local NEXUS gold (Documents/NEXUS)
### datasets/
- adversarial, benign, finetune, threat_intel, safety_merge, v7, v7_lab_output, stress-related benches
- **DPO-ready:** `v7_dpo_pairs.jsonl`, `v7_dpo_pairs_fixed.jsonl`, summaries
- Guard train: `guard_train_data.jsonl`, fused_attack/benign train/test jsonl
- HF discovery scripts: `hf_guard_discovery.py`, `hf_dense_guard_discovery.py`, `deep_search_slm.py`
- Scripts: `compile_dpo_dataset*.py`, `dataset_fusion.py`, `v7_builder.py`, `guard_train.py`

### benchmarks/
- code_reasoning, eggroll, orchestrator_eval, stress_lab, digitalocean, opusman_eval, foundry-style packs
- stress_lab: chembench, fenrir_cyber, finance_governance, agentsynth templates, multi-model eggroll configs
- register_foundry_datasets.py, merge_manifest.json

### foundry_datasets/
- Mirrors benchmark families for Azure/Foundry registration path

### scripts/
- `dataset_forge/forge.py`, `finetune/gen_guard_dpo_pairs.py`, `stress/nexus_guard_stress_test.py`
- `compile_dpo_calibration_dataset.py`, chaos/autonomous generators
- `nexus_os/a800/`: orchestrator, data_pipeline, eval_pack, cleanereval, sera, rift

### D: cold storage / models
- `D:\NEXUS_MODELS` — benchmarks, datasets, experiments, gguf, loras, safetensors
- `D:\NEXUS_COLD` — migrations/quarantine
- `D:\MyModels`, `D:\safetensors_candidates`, ollama backups

## 3. Discovery portal
### /dataset
- SPA shell observed (short bodyLen in CDP) — may need auth/session inside portal; treat as **mountable dataset catalog** for A100 JuiceFS-adjacent data, not only HF.
- Action: use portal UI when logged-in to attach datasets to NEXUS-GPU-test2 rather than re-download everything.

### /scp
- Richer page bodyLen≈5.8k; SCP shared compute packs / collaborative resources.
- Links sample count: 8
- Body head (OCR/DOM):
```
新建对话 论文工具 课题空间 科研应用 科学工具 科学数据 科学计算 最近对话 Workspace and Model Capabilities Inquiry Review and combine novel approaches from list 查看全部 31 科学工具广场 SCP 工具 · Skills 技能包 · 为科研 AI Agent 与工作流提供可组合的原子能力 新建Skill 查看详情 查看完整公告 蛋白质设计工具集 从 PDB 检索、结构比对到 AlphaFold 调用 — 11个 SCP 工具和 4 个 Skills 完整覆盖蛋白质设计 Agent 流程。 15 项能力 4 条工作流 24k 调用 查看专题 材料发现与晶体计算 Materials Project、AFLOW、PySCF、LAMMPS 一体接入，从性质约束生成晶体到 DFT 验证、MD 模拟。 18 项能力 3 条工作流 9.2k 调用 查看专题 气候系统与天气建模 ERA5、Copernicus、USGS 数据接入，结合 ClimaX、GraphCast 推理与可视化输出，搭建完整气候建模流程。 12 项能力 2 条工作流 6.4k 调用 查看专题 文献综述自动化 PubMed、arXiv、Semantic Scholar 检索，支持综述生成、引用脉络可视化，一键产出结构化研究综述。 10 项能力 3 条工作流 32k 调用 查看专题 SCP 生命科学 VenusFactory 蛋白质工程 AI 全流程工程，蛋白质突变与功能预测 SCP 通用 SciGraph 跨学科知识图谱查询服务，专为 AI 辅助科研设计 SKILL 生命科学 多组学整合 多组学数据整合分析，输出跨癌症功能富集报告 SKILL 地球科学 大气科学计算 气象参数输入，标准大气指标计算与输出 学科领域 全部领域 生命科学 地球科学 神经科学 材料科学 化学 物理 数学 通用 用途类型 全部类型 文献检索 计算工具 模型服务 数据库 湿实验操作 知识库 SCP 45 Skills 211 调用量 SciGraph 这是一款面向科学研究的统一知识查询服务，集成了生命科学、地球科学、材料科学、数学物理等多个学科领域的知识图谱数据，支持多学科知识检索、实体关系查询、领域知识问答等操作，为AI辅助科学研究提供强大的知识支撑。 通用 数据库 浙江大学 130.5K 35 DrugSDA-Tool DrugSDA-Tool 是面向药物分子筛选、设计与分析的综合性辅助工具集，集成了基于 Open Babel、RDKit、BioPython 等多种开源库的核心功能，支持数据检索与下载、格式转换、蛋白质结构修复、分子规范化处理、分子结构解析、分子相似度计算、结合口袋属性分析等关键操作。 生命科学 数据库 计算工具 北京大学 85.1K 15 ToolUniverse ToolUniverse-MCP 是基于AI-工具交互协议构建的标准化工具生态平台，通过为科学工具、数据资源与AI模型之间的无缝通信提供了一个通用接口，让研究人员能够更专注于科学问题本身，高效推进从假设生成到结果验证的全周期研究。整合涵盖生物医学数据库查询、科学计算、文献检索、实验设计等领域的数百个工具。 通用 数据库 知识库 上海人工智能实验室 21.2K 15 GWAS-KG 这是一款面向基因组学与变异分析的知识图谱查询服务，集成了基因、变异位点、疾病表型、GO功能注释等多维度生物医学知识，为全基因组关联研究提供强大的知识支撑。 生命科学 数据库 广州国家实验室 9.9K 1 InternAgent InternAgent 自建了覆盖化学、生物学、材料科学、药物发现以及多领域交叉应用的百余个科学计算工具体系。其中，核心工具 InternAgent-DeepResearch面向复杂科研任务，能够通过动态结构化知识流实现智能搜索与规划。该系统将研究问题拆解为具备依赖关系的子任务，并在执行过程中进行并行探索、层级分解与自适应优化，最终生成结构严谨、内容翔实、逻辑自洽的科研报告。 通用 计算工具 文献检索 上海人工智能实验室 9.7K 9 Scholar-KG 这是一款面向多学科科研论文的统一智能检索服务。它覆盖多个学科的海量论文，支持以自然语言检索相关论文，并同步返回命中论文的细粒度知识图谱与原文内容，帮助科研人员快速完成文献调研、知识查找与证据溯源，为AI辅助科学研究提供强大的论文知识底座。 通用 文献检索 上海人工智能实验室 5.9K 7 VenusFactory VenusFactory是以智能体为中心的蛋白质工程 AI 基础设施，支持代码、笔记本（notebook）、图形界面（GUI）和智能体（Agent）操作。该平台基
```

## 4. A / B / C coverage (80GB-aware)
| Track | Meaning | Session posture |
|-------|---------|-----------------|
| **A** | Upgrade torch for FSDPModule/new trl | Ready if import train fails hard |
| **B** | Keep torch 2.4.0+cu124; pin trl | Prefer if DPOTrainer fails only on API skew |
| **C** | Freeze stack; build data/eval/HF cache/configs | **Always running** — DPO pairs, stress_lab, portal datasets |

Observed earlier: torch **2.4.0+cu124**, A100-80GB smoke OK.

## 5. Novel 80GB experimental menu (vs 8GB local)
1. **Full-batch Guard-SLM DPO** on `v7_dpo_pairs_fixed.jsonl` (OOM on 8GB; fits 80GB with headroom)
2. **Dual-track:** SFT on fused_benign+attack then DPO preference (trl) with large grad accum disabled
3. **Stress-lab → preference:** convert eggroll/orchestrator stress jsonl to chosen/rejected pairs
4. **HF sample → scale:** imdb32 pipeline validates JuiceFS HF path; scale to UltraChat/OpenHermes subsets
5. **Qwen2.5-7B LoRA DPO** as quality ceiling; 0.5B/1.5B as fast regression canaries
6. **Eval matrix:** stress_lab chem/cyber/finance + code_reasoning foundry packs on A100 overnight-friendly runs
7. **Portal SCP packs** as extra corpora when local D: is cold

## 6. Execution protocol (remaining GPU hours)
1. Confirm HF venv whoami on A100 (`/data/NEXUS/venvs/nexus_hf`)
2. Rsync/copy selected local packs → `/data/NEXUS/datasets/nexus_local/` (v7_dpo, guard, stress samples)
3. Write `configs/dpo_a100_guard_v7.yaml` matching 80GB
4. One **dry-run** train 20 steps before full
5. Log all under `/data/NEXUS/logs/` + session4 CHECKPOINT

## 7. Grok usage hygiene
- Prefer text inventories + OCR distill; minimize full UI vision
- No AFK loops
- Artifacts: `Downloads\NEXUSlogs\_runs\GROK\YYYYMMDD\` or `NEXUS_*.txt` only at NEXUSlogs root
