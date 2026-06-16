# Deep Investigation: Edict (三省六部制) Multi-Agent System

**Repository:** `https://github.com/specimba/edict` (forked from `cft0808/edict`)
**Investigated:** 2026-06-12
**Analyst:** NEXUS OS Core Agent
**Cross-ref:** NEXUSCLAW v1, NEXUSCLAW_GAP_ANALYSIS_ANTIGRAV_2026-06-12.md, AGENTS.md

---

## Executive Summary

Edict is a production-grade multi-agent orchestration system that uses **ancient Chinese imperial bureaucracy (三省六部制)** as its architectural metaphor. It features 12 specialized agents, strict permission matrices, a 9-state task machine, real-time dashboard, Redis Streams EventBus, Outbox Relay, 3-tier escalation scheduler, and complete audit trails (59 activities per task).

**Key insight for NEXUSCLAW:** Edict solves many of the same problems we identified in our gap analysis — but with a **hierarchical, institutional approach** rather than our flat, trust-based approach. The two systems are complementary: Edict provides the **organizational structure**, NEXUSCLAW provides the **governance, trust scoring, and memory architecture**. A synthesis would create a significantly more robust system.

---

## 1. Agent Architecture: 12 Roles with Strict Hierarchy

### 1.1 The Imperial Hierarchy

```
皇上 (User) → 太子 (Taizi) → 中书省 (Zhongshu) → 门下省 (Menxia) → 尚书省 (Shangshu) → 六部 (Parallel)
```

| Agent | Role | Responsibility | Can Call |
|---|---|---|---|
| **太子** `taizi` | Message sorting | Distinguish chat vs. work orders; create tasks | 中书省 only |
| **中书省** `zhongshu` | Planning | Analyze requirements, decompose into todos | 门下省, 尚书省 |
| **门下省** `menxia` | Review/Quality Gate | Review plans; approve (准奏) or reject (封驳) | 尚书省, 中书省 (for rework) |
| **尚书省** `shangshu` | Dispatch | Distribute to ministries, monitor progress, aggregate results | 六部 (礼/户/兵/刑/工/吏) |
| **礼部** `libu` | Documentation | Tech docs, API docs, specifications | None (leaf) |
| **户部** `hubu` | Data/Analytics | Data processing, reports, cost analysis | None (leaf) |
| **兵部** `bingbu` | Code/Engineering | Feature dev, bug fixes, code review | None (leaf) |
| **刑部** `xingbu` | Security/Compliance | Security scans, compliance checks, red lines | None (leaf) |
| **工部** `gongbu` | Infrastructure | CI/CD, Docker, deployment, automation | None (leaf) |
| **吏部** `libu_hr` | HR/Agent Management | Agent registration, permissions, training | None (leaf) |
| **早朝官** `zaochao` | Daily briefing | Morning news aggregation, scheduled broadcasts | None (leaf) |

### 1.2 Permission Matrix (Hard-Coded, Not Trust-Based)

```python
# From openclaw.json
{
  "agents": [
    {"id": "taizi", "allowAgents": ["zhongshu"]},
    {"id": "zhongshu", "allowAgents": ["menxia", "shangshu"]},
    {"id": "menxia", "allowAgents": ["shangshu", "zhongshu"]},
    {"id": "shangshu", "allowAgents": ["libu", "hubu", "bingbu", "xingbu", "gongbu", "libu_hr"]}
  ]
}
```

**Key difference from NEXUSCLAW:**
- Edict uses **institutional role-based permissions** (hierarchical, hard-coded)
- NEXUSCLAW uses **trust-score-based permissions** (dynamic, calculated from behavior)
- Edict's model is **deterministic and predictable** — an agent's capabilities are defined by its office
- NEXUSCLAW's model is **adaptive and resilient** — a compromised agent loses trust and access automatically

**Synthesis opportunity:** Use Edict's hierarchical routing as the **default organizational structure**, but add NEXUSCLAW's **trust scoring as a dynamic overlay** that can override or supplement role-based permissions. For example: a 兵部 (bingbu) agent with trust score < 30 cannot execute deployment tasks even if its role allows it.

---

## 2. Task State Machine: 9 States with Institutional Enforcement

### 2.1 State Flow

```
Pending → Taizi → Zhongshu → Menxia → Assigned → Doing/Next → Review → Done/Cancelled
```

```python
_STATE_FLOW = {
    'Pending':  ('Taizi',   '皇上',    '太子',    '待处理旨意转交太子分拣'),
    'Taizi':    ('Zhongshu','太子',    '中书省',  '太子分拣完毕，转中书省起草'),
    'Zhongshu': ('Menxia',  '中书省',  '门下省',  '中书省方案提交门下省审议'),
    'Menxia':   ('Assigned','门下省',  '尚书省',  '门下省准奏，转尚书省派发'),
    'Assigned': ('Doing',   '尚书省',  '六部',    '尚书省开始派发执行'),
    'Next':     ('Doing',   '尚书省',  '六部',    '待执行任务开始执行'),
    'Doing':    ('Review',  '六部',    '尚书省',  '各部完成，进入汇总'),
    'Review':   ('Done',    '尚书省',  '太子',    '全流程完成，回奏太子转报皇上'),
}
```

### 2.2 State Machine Protections

From `kanban_update.py`:
- **Illegal transitions rejected:** `Doing → Taizi` is blocked
- **Audit trail:** Every transition is logged with timestamp, from, to, remark
- **Auto-dispatch:** State change triggers automatic agent dispatch via `_STATE_AGENT_MAP`
- **Snapshot on stable states:** Before risky transitions, a snapshot is saved for rollback

### 2.3 Comparison with NEXUSCLAW BrainstormEngine

| Feature | Edict State Machine | NEXUSCLAW BrainstormEngine |
|---|---|---|
| **Structure** | Fixed 9-state pipeline | Dynamic 4-phase (PROPOSE→DISCUSS→VOTE→RESOLVE) |
| **Enforcement** | Hard-coded, no skipping | Trust-weighted, can be bypassed with high consensus |
| **Review gate** | Mandatory (门下省 must approve) | Optional (dissent required for high-risk) |
| **Parallelism** | 六部 execute in parallel | Brainstorm is sequential deliberation |
| **Rollback** | Auto-rollback to snapshot on stall | Manual resolution via vote |
| **Human intervention** | Stop/Cancel/Resume at any state | Override via governance agent (trust ≥ 90) |

**Synthesis opportunity:** Use Edict's state machine for **structured workflow tasks** (code deployment, security review, document creation) where institutional process matters. Use NEXUSCLAW's BrainstormEngine for **exploratory/research tasks** where open deliberation and consensus-building are valuable. The Orchestrator can choose the appropriate workflow based on task type and risk level.

---

## 3. Audit Trail: 59 Activities Per Task — Complete Observability

### 3.1 The Four Data Sources

Edict fuses **4 data streams** into a unified activity timeline:

1. **flow_log** (10 entries): State transitions (Taizi → Zhongshu → Menxia)
2. **progress_log** (11 entries): Agent progress reports with text, todos, tokens, cost, elapsed
3. **todos** (11 entries): Task decomposition snapshots
4. **session JSONL** (26 entries): Agent thinking processes, tool calls, results

### 3.2 Session JSONL — The "Black Box" Solution

This is the most innovative feature. Edict reads OpenClaw's internal session logs (`~/.openclaw/agents/{agent_id}/sessions/*.jsonl`) and parses:

- `assistant` messages → thinking chains (💭 reasoning)
- `tool_result` messages → tool execution outputs (bash, file_read, etc.)
- `user` messages → human feedback or intervention

```python
def _parse_activity_entry(item):
    msg = item.get('message', {})
    role = str(msg.get('role', '')).strip().lower()
    
    if role == 'assistant':
        return {
            'kind': 'assistant',
            'thinking': '💭 Agent考虑到...',
            'tools': [{'name': 'bash', 'input_preview': 'cd /src && npm test'}]
        }
    if role in ('toolresult', 'tool_result'):
        return {
            'kind': 'tool_result',
            'tool': 'bash',
            'exitCode': 0,
            'output': '✓ All tests passed (123 tests)',
            'durationMs': 4500
        }
```

**Critical gap in NEXUSCLAW:** We have no equivalent of session JSONL fusion. Our MessageBus logs message delivery, but not the **internal reasoning** of agents. Edict's approach shows how to achieve "white box" observability without modifying the agent runtime.

**Synthesis opportunity:** Add `SessionFusion` to ARCHIVIST's import stage. For each agent task, read the agent's session log (if available), parse thinking/tool calls, and index into EPISODIC/SEMANTIC memory channels. This gives us the full 59-activity trace that Edict achieves.

---

## 4. Scheduler: 3-Tier Escalation with Auto-Rollback

### 4.1 The Escalation Algorithm

```python
# Runs every 60 seconds
for each task:
    elapsed = NOW - lastProgressAt
    if elapsed < stallThresholdSec (180s):
        continue  # Recently active, skip
    
    if retryCount < maxRetry (1):
        # STAGE 1: Retry
        retryCount += 1
        dispatch_for_state(task, current_state, trigger='taizi-scan-retry')
        log: "Stalled 180s, auto-retry #N"
    elif escalationLevel < 2:
        # STAGE 2: Escalate
        escalationLevel += 1
        target = menxia (if L=1) or shangshu (if L=2)
        wake_agent(target, "Task stalled, please intervene")
        log: "Escalated to {target}"
    elif autoRollback:
        # STAGE 3: Auto-rollback
        task.state = snapshot.state  # Previous stable state
        retryCount = 0
        escalationLevel = 0
        dispatch_for_state(task, snapshot.state, trigger='taiji-auto-rollback')
        log: "Auto-rollback to {snapshot.state}"
```

### 4.2 Snapshot System

Before each risky transition, Edict saves a snapshot:

```python
'snapshot': {
    'state': 'Assigned',
    'org': '尚书省',
    'now': '等待派发...',
    'savedAt': '2026-03-01T...',
    'note': 'scheduled-check'
}
```

If rollback triggers, the task reverts to this snapshot state.

### 4.3 Comparison with NEXUSCLAW TaskRouter

| Feature | Edict Scheduler | NEXUSCLAW TaskRouter |
|---|---|---|
| **Trigger** | Time-based (60s scan) | Event-based (task submission) |
| **Stall detection** | Fixed threshold (180s) | No explicit stall detection |
| **Retry** | Max 1 retry with backoff | Depends on strategy (DIRECT, BROADCAST, etc.) |
| **Escalation** | 3 levels (retry → menxia → shangshu → rollback) | No escalation levels |
| **Rollback** | Auto-rollback to snapshot | No snapshot/rollback mechanism |
| **Cost tracking** | Tokens + cost + elapsed per progress report | No cost tracking |

**Synthesis opportunity:** Add Edict's **3-tier escalation** to NEXUSCLAW TaskRouter as a background monitor. For tasks routed via REDUNDANT or BRAINSTORM strategies, spawn a monitor that:
1. Checks progress every N seconds
2. Retries if no progress (up to maxRetry)
3. Escalates to higher-trust agents if retries fail
4. Rolls back to previous stable state if escalation fails
5. Logs all actions to worklog with governance event type

---

## 5. EventBus: Redis Streams + Outbox Relay

### 5.1 Architecture

```
Agent → EventBus (Redis Streams) → Gateway (WebSocket) → Dashboard
         ↓
    Orchestrator (subscribes to all events)
         ↓
    Outbox Relay (persistent, at-least-once delivery)
```

### 5.2 Event Topics

```
task.created
task.planning.request
task.review.request
task.review.result
task.dispatch
agent.thought.append
agent.todo.update
task.status
heartbeat
```

### 5.3 Outbox Pattern

```python
# From edict/backend/app/models/outbox.py
class OutboxEvent:
    event_id: str  # uuid
    trace_id: str  # task-uuid
    topic: str
    payload: dict
    status: str  # pending | delivered | failed
    retry_count: int
    created_at: str
```

The Outbox Relay ensures events are delivered at-least-once, even if the consumer is temporarily down.

### 5.4 Comparison with NEXUSCLAW MessageBus

| Feature | Edict EventBus | NEXUSCLAW MessageBus |
|---|---|---|
| **Backend** | Redis Streams | Pure Python (in-memory + optional persistence) |
| **Delivery** | At-least-once (Outbox Relay) | Best-effort (in-memory) |
| **Topics** | Named topics with wildcards | Direct, broadcast, thread reply, system, external |
| **Real-time** | WebSocket push to dashboard | No WebSocket integration |
| **Persistence** | Redis + Outbox DB | Optional JSON log |
| **Decoupling** | Full pub/sub decoupling | Tight coupling (direct agent references) |

**Synthesis opportunity:** Add a **Redis Streams adapter** to NEXUSCLAW MessageBus as an optional backend. For production deployments, use Redis Streams + Outbox Relay. For local/dev, use the existing in-memory implementation. This gives us both simplicity and scalability.

---

## 6. Dashboard: 10-Panel Real-Time Kanban

### 6.1 Panels

1. **旨意看板 (Kanban)** — Task status columns, filtering, search, heartbeat badges
2. **省部调度 (Monitor)** — Task counts per department, agent health cards
3. **任务流转详情 (Task Detail)** — 59-activity timeline, full flow chain
4. **奏折阁 (Memorials)** — Completed tasks archived with 5-stage timeline
5. **旨库 (Templates)** — 9 preset templates with parameter forms
6. **官员总览 (Officials)** — Token consumption ranking, activity stats
7. **天下要闻 (News)** — Daily tech/finance news aggregation
8. **模型配置 (Models)** — Per-agent LLM switching, hot-reload (~5s)
9. **技能配置 (Skills)** — Remote skill management (GitHub URLs)
10. **上朝仪式 (Ceremony)** — Daily opening animation with stats
11. **朝堂议政 (Court Discussion)** — Multi-agent LLM debate around topics

### 6.2 Dashboard Tech Stack

- **Frontend:** React 18 + TypeScript + Vite + Zustand (13 components)
- **Backend:** Pure Python stdlib `http.server` (~2300 lines, zero dependencies)
- **API:** REST + WebSocket
- **Data refresh:** 15-second polling loop (`scripts/run_loop.sh`)

### 6.3 Comparison with NEXUS Dashboard

| Feature | Edict Dashboard | NEXUS Dashboard |
|---|---|---|
| **Framework** | React + Vite + Zustand | Next.js (253 files) + custom components |
| **Backend** | Python stdlib (zero deps) | Next.js API routes + Prisma |
| **Real-time** | WebSocket + 15s polling | Not yet implemented |
| **Agent health** | Heartbeat badges (🟢🟡🔴) | Not yet implemented |
| **Task干预** | Stop/Cancel/Resume buttons | Not yet implemented |
| **Token tracking** | Per-agent consumption | Not yet implemented |
| **Skills UI** | Remote skill add/remove | Not yet implemented |
| **Model switching** | Per-agent hot-swap | ModelRelay handles globally |

**Synthesis opportunity:** Edict's dashboard is **much simpler** than our Next.js stack but **more functional** for agent operations. We should:
1. Add a **lightweight agent health panel** to our existing dashboard
2. Integrate **WebSocket** for real-time task updates (using our MessageBus as backend)
3. Add **stop/cancel/resume** buttons for task lifecycle management
4. Display **trust scores** alongside agent health badges (our unique advantage)
5. Show **token cost tracking** per agent per task (leverage ModelRelay's usage data)

---

## 7. Skills Management: Remote Skills from GitHub

### 7.1 Three Methods to Add Skills

1. **Dashboard UI** — Select agent, enter skill name + GitHub URL
2. **CLI** — `python3 scripts/skill_manager.py add-remote --agent menxia --name mmx_cli --source https://raw.githubusercontent.com/.../SKILL.md`
3. **API** — `POST /api/add-remote-skill` with agentId, skillName, sourceUrl

### 7.2 Skill Storage

Skills are stored as Markdown files (SOUL.md format) in `agents/{agent_id}/skills/` and are automatically synced to agent workspaces via `install.sh`.

### 7.3 Comparison with NEXUSCLAW

| Feature | Edict Skills | NEXUSCLAW Skills |
|---|---|---|
| **Source** | GitHub raw URLs | Local filesystem only |
| **Format** | Markdown (SOUL.md) | Python modules + JSON |
| **Distribution** | Remote download | Manual copy |
| **Versioning** | Manual update via CLI | No versioning |
| **Scope** | Per-agent | System-wide (skill library) |

**Synthesis opportunity:** Add **remote skill registry** to NEXUSCLAW. Store skill definitions in a GitHub repository (or our own `skills/` directory), allow agents to dynamically fetch skills based on task requirements. This aligns with the **AutoSkill** and **SkillRL** papers from our NEXUSCLAW analysis.

---

## 8. LinUCB Router: Intelligent Agent Selection

### 8.1 Algorithm

Edict uses **LinUCB (Linear Upper Confidence Bound)**, a contextual bandit algorithm, for intelligent agent selection:

```python
# scripts/linucb_router.py
class LinUCB:
    def __init__(self, n_features, alpha=1.0):
        self.A = np.eye(n_features)  # Feature covariance matrix
        self.b = np.zeros(n_features)  # Reward vector
        self.alpha = alpha  # Exploration parameter
    
    def select(self, context):
        # context: task features (type, complexity, urgency, ...)
        theta = np.linalg.solve(self.A, self.b)
        p = np.dot(theta, context) + self.alpha * np.sqrt(np.dot(context, np.linalg.solve(self.A, context)))
        return p  # Upper confidence bound score
    
    def update(self, context, reward):
        self.A += np.outer(context, context)
        self.b += reward * context
```

### 8.2 Comparison with NEXUSCLAW TaskRouter

| Feature | Edict LinUCB | NEXUSCLAW TaskRouter |
|---|---|---|
| **Algorithm** | Contextual bandit (explore/exploit) | Rule-based (risk + trust + load) |
| **Features** | Task type, complexity, urgency, agent history | Risk level, agent capabilities, trust score |
| **Learning** | Yes (updates from rewards) | No (static rules) |
| **Exploration** | Explicit (alpha parameter) | Implicit (REDUNDANT strategy) |
| **Cold start** | Needs warm-up data | Works immediately |

**Synthesis opportunity:** Replace or augment NEXUSCLAW TaskRouter's **capability-based routing** with a **LinUCB layer** that learns from historical task outcomes. For each task type, maintain a LinUCB model that selects the best agent based on:
- Task features (from task description)
- Agent features (trust score, success rate, load)
- Historical rewards (task completion quality, time, cost)

This aligns with the **RouteLLM** paper from our NEXUSCLAW analysis (P2 — Routing/Cost).

---

## 9. File Lock: Multi-Agent Concurrency Guard

### 9.1 Implementation

Edict has a dedicated `scripts/file_lock.py` for preventing concurrent writes:

```python
class FileLock:
    def __init__(self, path):
        self.path = path
        self.lockfile = path + ".lock"
    
    def acquire(self, timeout=10):
        # Uses OS-level file locking (fcntl on Linux, msvcrt on Windows)
        # Exponential backoff if lock is held
    
    def release(self):
        # Remove lockfile
```

### 9.2 Comparison with NEXUSCLAW

| Feature | Edict FileLock | NEXUSCLAW (current) |
|---|---|---|
| **Concurrency** | File-level locking | None (SQLite DB lock only) |
| **Timeout** | 10s with backoff | No timeout handling |
| **Cross-platform** | Yes (fcntl/msvcrt) | Not implemented |
| **Scope** | Any file operation | SQLite only |

**Synthesis opportunity:** This directly addresses our **Gap #5 (SQLite database lock)** from the antigravity analysis. Add `nexus_os/nexusclaw/utils/file_lock.py` with cross-platform file locking. Use it for:
- ARCHIVIST daemon file processing
- Vault memory channel writes
- Worklog appends
- Agent configuration updates

---
## 10. Configuration Sync: Agent Workspace Provisioning

### 10.1 `install.sh` Automation

Edict's `install.sh` performs a complex provisioning process:

1. Create all 12 agent workspaces
2. Write SOUL.md (personality + workflow rules + data cleaning specs) to each
3. Register agents + permission matrix to `openclaw.json`
4. **Symbol-link data directories** (`data/`, `scripts/`) into each workspace
5. Set agent-to-agent communication visibility (`sessions.visibility all`)
6. **Sync API keys** from configured agent to all agents
7. Build React frontend (optional)
8. Initialize data directories + first sync
9. Restart Gateway

### 10.2 Key Insight: Symbol Links for Data Consistency

```bash
# From install.sh
ln -s $PROJECT_DIR/data $AGENT_WORKSPACE/data
ln -s $PROJECT_DIR/scripts $AGENT_WORKSPACE/scripts
```

This ensures all agents see the same data and scripts without duplication.

### 10.3 Comparison with NEXUSCLAW AgentPool

| Feature | Edict install.sh | NEXUSCLAW AgentPool |
|---|---|---|
| **Provisioning** | Automated, 12 agents | Manual registration |
| **Personality** | SOUL.md per agent | No personality system |
| **Data sharing** | Symbol links | No shared data concept |
| **API key sync** | Automatic | No key management |
| **Visibility** | Configurable (`all`) | Trust-gated messaging |

**Synthesis opportunity:** Add **Agent Provisioning** to NEXUSCLAW. When the Orchestrator starts, auto-create agent profiles from a template directory (like Edict's `agents/`). Each agent gets:
- SOUL.md equivalent (personality + capabilities + lane assignments)
- Symbol-linked access to shared resources (ARCHIVIST, Vault, ModelRelay)
- Trust score initialized from role (六部 = 50, 门下省 = 70, 尚书省 = 80, 太子 = 90)
- Auto-registered in AgentPool with capabilities extracted from SOUL.md

---

## 11. Cost Transparency: Every Action Has a Price

### 11.1 Progress Log Cost Tracking

Every agent progress report includes:

```json
{
  "tokens": 4500,
  "cost": 0.0045,
  "elapsed": 120
}
```

The dashboard aggregates these into:
- Total tokens per task
- Total cost per task
- Total elapsed time per task
- Per-agent token consumption ranking

### 11.2 Comparison with NEXUSCLAW

| Feature | Edict | NEXUSCLAW |
|---|---|---|
| **Token tracking** | Per progress report | No tracking |
| **Cost tracking** | USD per report | No tracking |
| **Time tracking** | Seconds per report | No tracking |
| **Dashboard** | Per-agent ranking, per-task totals | Not implemented |
| **Budget limit** | Not implemented | No limit |

**Synthesis opportunity:** Integrate with ModelRelay's existing usage tracking. For each agent task routed through ModelRelay, capture:
- Input tokens, output tokens, total tokens
- Model used, cost per token, total cost
- Time elapsed (from request to response)

Store this in a **cost ledger** in the Vault (TASK or META channel). Use it for:
- Budget alerts (per agent, per task, per day)
- Agent performance metrics (cost per unit of work)
- LinUCB router feature (cost as a negative reward)

---

## 12. Critical Gaps in Edict (Where NEXUSCLAW is Stronger)

### 12.1 No Trust System

Edict's permissions are **role-based and static**. If an agent is compromised or behaves badly, there's no mechanism to reduce its access. The permission matrix is in `openclaw.json` and requires manual editing.

**NEXUSCLAW advantage:** Our trust scoring system (tanh formula, 11 elements, anti-grinding) dynamically adjusts agent capabilities based on behavior. A compromised agent automatically loses access.

### 12.2 No Memory Architecture

Edict has **no persistent memory system** beyond the task JSON files. Agents don't learn from past tasks, don't have episodic memory, and don't consolidate knowledge.

**NEXUSCLAW advantage:** Our 8-Channel Memory (SENSORY, WORKING, EPISODIC, SEMANTIC, PROCEDURAL, TRUST, TASK, META) with trust-gated writes and LightMem consolidation provides a full cognitive memory architecture.

### 12.3 No Security Scanning

Edict has a 刑部 (xingbu) agent for security reviews, but no **automated secret scanning** or **credential exposure detection**.

**NEXUSCLAW advantage:** Our planned SecretVault + secret_scanner (Gap #6) provides automated credential protection.

### 12.4 No Model Governance

Edict allows per-agent model switching, but has no **governance framework** for model selection, no **constitution** for allowed/banned behaviors, and no **benchmark** for model performance tracking.

**NEXUSCLAW advantage:** Our Governor module with `constitution.yaml` (16 rules), NEXUS-Bench (5 tracks), and trust-score-gated model access provides institutional governance.

### 12.5 No Port/Resource Management

Edict runs on a fixed port (7891) with no awareness of port conflicts or resource allocation. Our antigravity log showed that NEXUS Bridge on port 7354 was killed by GROSS — Edict would have the same problem.

**NEXUSCLAW advantage:** Our planned PortRegistry (Gap #1) provides resource-aware orchestration.

### 12.6 No Environmental Entropy Management

Edict creates 12 agent workspaces but has no concept of cleaning up unused agents, managing disk space, or tracking "agent entropy."

**NEXUSCLAW advantage:** Our planned Agent Environment Manager (AEM) tracks and manages the 68+ dot-directories in the user's home.

---

## 13. Synthesis: The NEXUSCLAW-Edict Integration Map

### 13.1 What to Adopt from Edict (Immediate P1-P2)

| Edict Feature | NEXUSCLAW Integration | Priority | Effort |
|---|---|---|---|
| **State machine** (9 states, institutional) | Add `WorkflowEngine` to Orchestrator with Edict-like pipeline states | P1 | 3h |
| **Permission matrix** (hierarchical roles) | Extend `AgentPool` with `role` field + `can_message()` check | P1 | 2h |
| **Session JSONL fusion** | Add `SessionFusion` to ARCHIVIST import stage | P2 | 4h |
| **3-tier escalation** | Add `EscalationMonitor` to TaskRouter background thread | P2 | 3h |
| **Snapshot/rollback** | Add `TaskSnapshot` to TaskRouter before risky transitions | P2 | 2h |
| **File lock** | Add `FileLock` utility for cross-platform concurrency | P2 | 1h |
| **LinUCB router** | Add `LinUCBRouter` as alternative routing strategy | P3 | 4h |
| **Cost tracking** | Integrate ModelRelay usage data into Vault cost ledger | P2 | 2h |
| **Dashboard panels** | Add agent health, task lifecycle, token tracking to Next.js dashboard | P3 | 6h |
| **Remote skills** | Add `RemoteSkillRegistry` to skill system | P3 | 3h |
| **Agent provisioning** | Add `AgentProvisioner` from template directory | P3 | 4h |
| **Redis Streams adapter** | Add `RedisMessageBus` backend option | P3 | 4h |

### 13.2 What NEXUSCLAW Provides to Edict (If We Were to Contribute)

| NEXUSCLAW Feature | Edict Enhancement | Value |
|---|---|---|
| **Trust scoring** | Replace static permissions with dynamic trust gates | Resilience against compromised agents |
| **8-Channel Memory** | Add persistent agent memory across tasks | Agents learn from past work |
| **ARCHIVIST pipeline** | Ingest all 59 activities per task into searchable dossiers | Knowledge management |
| **Constitution + NEXUS-Bench** | Add model governance and performance benchmarking | Quality assurance |
| **SecretVault + scanner** | Protect API keys in agent environments | Security hardening |
| **PortRegistry** | Prevent port conflicts between services | Infrastructure reliability |
| **SystemHealthProbe** | Monitor all 12 agents and dashboard health | Operational reliability |
| **ConfigSyncEngine** | Keep agent configs synchronized across 12 workspaces | Configuration management |

---

## 14. Actionable Recommendations for NEXUSCLAW P1

Based on this deep investigation, here are the **top 5 highest-impact** integrations for our current P1 work:

### 14.1 #1: Add StateMachineWorkflow to Orchestrator (3h)

**Rationale:** Edict's 9-state pipeline is its most powerful feature. For NEXUSCLAW, add a `StateMachineWorkflow` class that supports:
- `Pending → Planning → Review → Approved → Assigned → Executing → Review → Done`
- Mandatory review gate (like 门下省) before execution
- Auto-dispatch on state transition
- Illegal transition rejection
- Snapshot before risky transitions

**Code location:** `nexus_os/nexusclaw/workflow_engine.py`

### 14.2 #2: Extend AgentPool with Roles + Permission Matrix (2h)

**Rationale:** Complement trust-based messaging with role-based defaults. Add:
- `role` field to `AgentRecord` (e.g., `orchestrator`, `planner`, `reviewer`, `executor`, `governance`)
- `role_permissions` dict mapping roles → allowed message targets
- `can_message(from_role, to_role)` check that ORs with trust-based check
- Default roles for our 5 NEXUSCLAW subsystems (orchestrator, router, bus, brainstorm, pool)

**Code location:** `nexus_os/nexusclaw/agent_pool.py`

### 14.3 #3: Add TaskSnapshot + Auto-Rollback to TaskRouter (2h)

**Rationale:** Before routing a task via BRAINSTORM or REDUNDANT strategy, save a snapshot. If the task stalls (no progress for N seconds), auto-revert to the snapshot and retry with a different strategy or agent.

**Code location:** `nexus_os/nexusclaw/task_router.py`

### 14.4 #4: Add SessionFusion to ARCHIVIST (4h)

**Rationale:** Parse agent session logs (if available) to extract thinking chains and tool results. This gives us the "white box" observability that Edict achieves. Start with OpenCode/Codex session JSONL format, then generalize.

**Code location:** `nexus_os/archivist/import_stage.py` (new `SessionFusion` class)

### 14.5 #5: Add Cross-Platform FileLock Utility (1h)

**Rationale:** Direct fix for our SQLite deadlock issue. Use `fcntl` (Linux/macOS) and `msvcrt` (Windows) for OS-level file locking.

**Code location:** `nexus_os/nexusclaw/utils/file_lock.py`

---

## 15. Evidence Checklist

| Claim | Evidence | Status |
|---|---|---|
| 12-agent hierarchy | README.md, edict_agent_architecture.md | ✅ Verified |
| 9-state machine | task-dispatch-architecture.md section 2.1 | ✅ Verified |
| 59 activities per task | task-dispatch-architecture.md section 2.3 | ✅ Verified |
| Session JSONL fusion | task-dispatch-architecture.md section 2.3 | ✅ Verified |
| 3-tier escalation | task-dispatch-architecture.md section 2.4 | ✅ Verified |
| Permission matrix | README.md, openclaw.json | ✅ Verified |
| Redis Streams EventBus | edict_agent_architecture.md section 3 | ✅ Verified |
| Outbox Relay | edict/backend/app/models/outbox.py | ✅ Verified |
| LinUCB router | scripts/linucb_router.py | ✅ Verified |
| File lock | scripts/file_lock.py | ✅ Verified |
| Cost tracking | task-dispatch-architecture.md progress_log schema | ✅ Verified |
| 10-panel dashboard | README.md, screenshots/ | ✅ Verified |
| Remote skills | README.md, docs/remote-skills-guide.md | ✅ Verified |
| Symbol-link data sharing | install.sh | ✅ Verified |
| No trust system | openclaw.json (static permissions) | ✅ Verified |
| No memory system | No memory module in file tree | ✅ Verified |

---

*This investigation confirms that Edict is a highly sophisticated, production-oriented multi-agent system with institutional design patterns that directly address our NEXUSCLAW gaps. The synthesis of NEXUSCLAW's governance/trust/memory with Edict's hierarchy/state-machine/observability would create a uniquely powerful system.*
