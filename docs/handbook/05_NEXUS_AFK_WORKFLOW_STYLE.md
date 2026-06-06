# NEXUS AFK Workflow Style v1.0

## Session Metadata
- **Style:** `nexus-afk:time` — Planning / Orchestration / Debugging / Build
- **Duration:** 8 hours (12-7PM UTC+3)
- **State:** User AFK — Agent Autonomous — Evidence-Grounded
- **Output:** NEXUS_OS_V4_MASTER_PLAN.md (55KB, 15 sections, 12-week roadmap)
- **Data Sources Ingested:** 6 (Zo Chat, HERMES Swarm Pack, Docker Gordon Phase 1, NEXUS Main Repo, Security Audits, Terminal Poisoning Post-Mortem)
- **Research Domains:** 7 (Sandbox Systems, Cross-Agent Security, Hallucination Detection, Speculative Decoding, TWAVE/QWAVE/CHIMERA, E2E Encryption, Platform Strategy)
- **Architectures Designed:** 8 (Sandbox Abstraction, Multi-Layer Security, Slack Bot Network, Hallucination Framework, Speculative Decoding Engine, ACP Protocol, Governance Mesh, 6-Phase Roadmap)

---

## 1. Core Principle

> **When the user goes AFK, the agent does not stop. It expands the context horizon.**

The AFK workflow transforms downtime into strategic depth. Instead of waiting for instructions, the agent:
1. Ingests ALL available context (code, docs, chats, research, running infra)
2. Identifies gaps, conflicts, and opportunities across data sources
3. Synthesizes novel architectures from the tensions between sources
4. Produces deliverable artifacts — not chat noise

---

## 2. The 5-Phase AFK Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS AFK WORKFLOW LOOP                       │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │ SCAN     │──▶│ DIGEST   │──▶│ SYNTHESIZE│──▶│ PRODUCE  │     │
│  │          │   │          │   │          │   │          │     │
│  │Find ALL  │   │Read &    │   │Cross-ref │   │Write plan,│    │
│  │data      │   │catalog   │   │find gaps, │   │code, or  │     │
│  │sources   │   │every file│   │design     │   │docs      │     │
│  └──────────┘   └──────────┘   └──────────┘   └─────┬────┘     │
│                                                      │          │
│                                                      ▼          │
│                                               ┌──────────┐      │
│                                               │ VERIFY   │      │
│                                               │          │      │
│                                               │Check size,│     │
│                                               │integrity │     │
│                                               └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1: SCAN (First 15 minutes)
**Goal:** Inventory every available data source.

```python
# Mental checklist executed at T+0
sources = [
    # 1. File system
    "CWD full recursive listing",
    "Recent git log (--oneline -50)",
    "Git status (--short)",
    "Uncommitted files (git diff)",
    
    # 2. Runtime state
    "Running containers (docker ps)",
    "Running processes (Get-Process)",
    "Environment variables (relevant)",
    "Open ports",
    
    # 3. Chat/session history
    "Zo Computer chat logs",
    "Previous agent session logs",
    "Slack/Telegram unread",
    
    # 4. Documentation
    "AGENTS.md",
    "01_PROJECT_STATE.md",
    "knowledge.md",
    "docs/handbook/*.md",
    "All .md files modified in last 7 days",
    
    # 5. External links user provided
    "GitHub repos",
    "Web links (zo.computer, papers, etc.)",
]
```

**Output:** Sorted list of ALL files/links with sizes, dates, and relevance tags.

### Phase 2: DIGEST (Minutes 15-90)
**Goal:** Read and catalog every identified source. No synthesis yet — just capture.

```python
for source in prioritized_sources:
    if is_large_file(source):
        read(headers=True, sample_lines=50)
        # Use task tool for parallel exploration of directories
    elif is_source(source):
        read(entire_file=True)
        catalog({
            "path": source.path,
            "purpose": extract_purpose(source),
            "key_findings": extract_key_claims(source),
            "status": extract_status(source),  # working, broken, planned
            "dependencies": extract_deps(source),
        })
```

**Output:** A mental map of every component, its status, and its relationships.

### Phase 3: SYNTHESIZE (Minutes 90-240)
**Goal:** Find tensions, gaps, and opportunities BETWEEN sources.

This is the highest-value phase. The agent looks for:

```python
synthesis_patterns = [
    # Pattern 1: Duplication
    "Same component in multiple places → unification opportunity",
    
    # Pattern 2: Contradiction
    "Source A says X, Source B says not-X → investigation needed",
    
    # Pattern 3: Missing link
    "Component A outputs to nowhere, Component B needs input from nowhere → bridge opportunity",
    
    # Pattern 4: Latent capability
    "Tool exists but is not wired into any workflow → activation opportunity",
    
    # Pattern 5: Security gap
    "Data flows across trust boundaries without controls → hardening needed",
    
    # Pattern 6: Platform lock-in
    "Hardcoded Windows/Linux paths → cross-platform abstraction needed",
    
    # Pattern 7: Research-to-code gap
    "Paper/concept exists but no implementation → engineering opportunity",
]
```

**Output:** A gap analysis document with ranked opportunities.

### Phase 4: PRODUCE (Minutes 240-420)
**Goal:** Write the deliverable. This should be 70% of total time.

Structure for an AFK plan document:
```
1. Executive Summary (1 paragraph)
2. Current State Assessment (tables, status badges)
3. Problem Analysis (what's broken and why)
4. Proposed Architecture (diagrams, interfaces, data flow)
5. Implementation Plan (phased, estimated effort)
6. Risk Register (what could go wrong)
7. Appendices (source index, references)
```

Rules:
- **No fluff.** Every paragraph should justify its existence.
- **Prefer tables and diagrams** over prose for complex relationships.
- **Show code** for key interfaces (abstract base classes, protocols, algorithms).
- **Estimate effort** in days, not hours.
- **Identify dependencies** between phases.
- **End with "Next Steps"** — what the user should do when they return.

### Phase 5: VERIFY (Final 30 minutes)
**Goal:** Confirm the artifact is complete and correct.

```python
checks = [
    "File size > 10KB? (if not, likely incomplete)",
    "All promises in the intro fulfilled in the body?",
    "All data sources cross-referenced?",
    "No contradictions within the document?",
    "Actionable next steps defined?",
    "Risk register populated?",
    "No placeholder/TODO text left in final output?",
]
```

**Output:** A verified, deliverable artifact.

---

## 3. Tool Selection Rules

| Situation | Tool | Why |
|-----------|------|-----|
| Large directory exploration | `task` with `explore` subagent | Parallelizes file reads, returns summary |
| Content search across files | `grep` | Fast regex search, returns line numbers |
| File pattern search | `glob` | Fast path matching |
| Quick file read | `read` with offset/limit | No subprocess overhead |
| Multi-file read | Multiple `read` calls in parallel | Batched in one message |
| Research | `websearch` then `webfetch` | Prioritize search before fetching |
| Writing | `write` | Creates new files |
| Editing | `edit` (exact string replacement) | Surgical changes |
| Complex multi-step research | `task` with `research` subagent | Dedicated context, returns summary |
| State tracking | `todowrite` | Only for complex multi-step tasks |

---

## 4. Communication Style

### When the user is AFK:
- **Log progress** to a session document (this file)
- **Do not ask questions** — infer intent from existing context
- **Do not stop for warnings** — note them in the risk register
- **Do prompt for passwords/secrets** — note them as blocked items

### When the user returns:
```
Subject: <Session Summary>

Accomplished:
- <3-5 bullet points of concrete deliverables>
- <file sizes, locations>

Blocked (needs you):
- <any items requiring credentials or decisions>

Ready to:
- <next action if user gives go-ahead>
```

---

## 5. The OsmanClaw? Naming Convention

Per the user's directive, all agent/worker/bot entities in this system
follow the `OsmanClaw?` naming pattern:

- The name is `OsmanClaw?` (capital O, capital C, literal `?` at end)
- The `?` signifies: *always questioning, always verifying*
- No agent output is accepted at face value without evidence
- Every action is gated by: "Is this the right thing to do?"

This applies to:
- Worker processes in the sandbox system
- Slack bot identities
- Background daemons
- Inference worker labels

---

## 6. Session Integrity Checks

At the end of every AFK session:

```python
integrity_check = [
    "✅ No credentials/keys written to artifacts",
    "✅ No destructive commands run without documentation",
    "✅ All external data sources cited",
    "✅ All code/architecture designs justified",
    "✅ Risk register populated for uncertain claims",
    "✅ Deliverable is self-contained (no external links as primary source)",
    "✅ Workflow document updated for repeatability",
]
```

---

## 7. Template for Future Sessions

Save as `docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md`
and reference it at the start of every AFK session:

```
I will now follow the NEXUS AFK Workflow Style (docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md).
Scanning all data sources...
```
