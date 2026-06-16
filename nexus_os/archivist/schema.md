# NEXUS Archivist Schema v1.0
## Based on Karpathy LLM Wiki Architecture (gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
## Adapted for NEXUS OS Multi-Agent System

---

## Core Philosophy

The NEXUS Archivist is a persistent, compounding knowledge base maintained by LLM agents. Unlike RAG (which rediscovers knowledge on every query), the wiki **accumulates and cross-references knowledge** so that synthesis is already done when questions are asked.

**Three Layers:**
1. **Raw Sources** — Immutable pointers to files in ARCHIVIST, PAPERS, NEXUSlogs, Documents/NEXUS
2. **The Wiki** — LLM-generated markdown: entity pages, concept pages, indexes, logs
3. **This Schema** — Agent behavior rules, conventions, and workflows

---

## Directory Structure

```
nexus_os/archivist/
├── schema.md              ← This file (behavior protocol)
├── archivist.py            ← Ingestion/maintenance engine
├── wiki/
│   ├── index.md            ← Content catalog (updated every ingest)
│   ├── log.md              ← Chronological operation log (append-only)
│   ├── boot.md             ← Fast sync for new agents (auto-generated)
│   ├── entities/           ← Entity pages (models, providers, agents, projects)
│   │   ├── models.md       ← All discovered models with scores
│   │   ├── providers.md    ← Provider status and configuration
│   │   ├── agents.md       ← Agent definitions and roles
│   │   └── projects.md     ← Project state and history
│   ├── concepts/           ← Concept pages (benchmarks, security, architecture)
│   │   ├── benchmarking.md ← Intelligence scoring methodology
│   │   ├── security.md     ← Security posture and findings
│   │   ├── architecture.md ← System architecture overview
│   │   └── governance.md   ← Governance rules and KAIJU gates
│   └── sources/            ← Source summaries (one per major source directory)
│       ├── archivist.md    ← ARCHIVIST directory summary
│       ├── papers.md       ← PAPERS directory summary
│       ├── nexuslogs.md    ← NEXUSlogs directory summary
│       └── gross.md        ← D:\GROSS confidential project summary
```

---

## Conventions

### File Format
- All wiki pages are **Markdown** with optional YAML frontmatter
- Frontmatter tags: `date`, `category`, `status`, `sources`, `confidence`
- Cross-references use `[[wiki-link]]` syntax (Obsidian-compatible)
- Code blocks for commands, configs, API responses

### Status Tags
- `active` — Currently maintained, up-to-date
- `stale` — Needs review (older than 30 days)
- `contradicted` — Newer sources conflict with this page
- `draft` — New page, not yet verified
- `archived` — No longer relevant, kept for history

### Confidence Levels
- `verified` — Directly observed or tested
- `indirect` — From logs, secondary sources
- `estimated` — Inferred, may need validation
- `deprecated` — Superseded by newer information

---

## Workflows

### Ingest Workflow

When new sources arrive or on scheduled scan:

1. **Scan** — Recursively scan all 4 directories + D:\GROSS
2. **Categorize** — Sort by file type, date, content category
3. **Summarize** — For new/changed files, extract key information
4. **Update Entities** — Add new entities, update existing ones
5. **Cross-Reference** — Add [[wiki-links]] between related pages
6. **Flag Contradictions** — Mark when new data conflicts with old
7. **Update Index** — Regenerate `index.md` with new entries
8. **Log Entry** — Append to `log.md` with timestamp and summary
9. **Update Boot** — Regenerate `boot.md` for fast agent sync

**Command:** `python archivist.py ingest [--force]`

### Query Workflow

When an agent asks a question:

1. **Read Index** — Find relevant pages from `index.md`
2. **Drill Down** — Read specific entity/concept pages
3. **Synthesize** — Combine information, note confidence levels
4. **Cite Sources** — Reference `[[page]]` and raw source paths
5. **Optionally File** — If the answer is valuable, save as new wiki page

### Lint Workflow

Periodic health check (weekly or on demand):

1. **Find Orphans** — Pages with no inbound links
2. **Check Stale** — Pages older than 30 days without updates
3. **Find Contradictions** — Pages marked `contradicted`
4. **Missing Pages** — Important concepts without dedicated pages
5. **Broken Links** — Wiki links pointing to non-existent pages
6. **Generate Report** — List of issues and recommended actions

**Command:** `python archivist.py lint [--fix]`

### Sync Workflow

When a new agent joins the system:

1. **Read Boot** — Agent reads `boot.md` (60-second overview)
2. **Read Index** — Agent reads `index.md` for full catalog
3. **Read Schema** — Agent reads `schema.md` for conventions
4. **Targeted Deep Dive** — Agent reads specific entity/concept pages
5. **Start Contributing** — Agent can now query and optionally update wiki

**Boot file is auto-generated on every ingest for freshness.**

---

## Raw Source Map

| Wiki Page | Raw Sources | Scan Pattern |
|-----------|-------------|--------------|
| `sources/archivist.md` | `C:\Users\speci.000\Downloads\ARCHIVIST` | `**/*` (exclude archive/) |
| `sources/papers.md` | `C:\Users\speci.000\Downloads\PAPERS` | `**/*.pdf` |
| `sources/nexuslogs.md` | `C:\Users\speci.000\Downloads\NEXUSlogs` | `**/*.txt` |
| `sources/gross.md` | `D:\GROSS` | `**/*.md` (read-only, confidential) |
| `entities/models.md` | ModelRelay API | `GET /api/models` |
| `entities/providers.md` | `.modelrelay.json` | Provider configs |
| `entities/agents.md` | `ARCHIVIST/agents/`, `DERDDRE/agents/` | `**/*.md` |
| `entities/projects.md` | `ARCHIVIST/implementation_plan*.md` | `**/*.md` |
| `concepts/benchmarking.md` | `PAPERS/papers06/`, `BENCHarenaguidhowto.txt` | Benchmark papers |
| `concepts/security.md` | `GROSS/`, `ARCHIVIST/SECURITY_*` | Security reports |
| `concepts/architecture.md` | `01_PROJECT_STATE.md`, `AGENTS.md` | Canonical docs |

---

## Agent Rules

### What You MUST Do
- Update the wiki when you discover new information
- Add log entries for significant operations
- Cross-reference related pages with `[[links]]`
- Maintain confidence levels honestly
- Preserve append-only log discipline
- Update `boot.md` after major changes

### What You MUST NOT Do
- Modify raw sources (they are immutable)
- Delete wiki pages (mark as `archived` instead)
- Commit sensitive data (keys, tokens) to wiki
- Overwrite log.md (only append)
- Fabricate information not grounded in sources
- Skip updating the index when adding pages

### For External Agents (Browser, CLI, Other Platforms)
- Read `boot.md` first for 60-second system overview
- Read `index.md` second for content catalog
- Use `schema.md` to understand conventions
- All wiki pages are plain markdown — no special tools needed
- Cross-platform compatible: works in any editor or browser

---

## Integration with NEXUS OS

### Dashboard Integration
- Dashboard queries `archivist.py` for model/provider status
- Wiki pages rendered as HTML in dashboard tabs
- `boot.md` shown as "System Overview" panel

### ModelRelay Integration
- Model changes auto-trigger `archivist.py ingest --models`
- New models added to `entities/models.md`
- Score changes logged in `log.md`

### God Mode Proxy Integration
- Routing decisions logged in `log.md`
- Top model performance tracked in `entities/models.md`
- Provider tier changes logged

### GROSS Integration (Confidential)
- `sources/gross.md` is read-only reference
- No GROSS details exposed in public wiki pages
- GROSS findings summarized at high level only
- Full GROSS data stays in D:\GROSS (confidential)

---

## Version History
- v1.0 (2026-06-09) — Initial schema based on Karpathy LLM Wiki
- Based on: gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Adapted for: NEXUS OS multi-agent operating system
- Author: NEXUS OS Auditor (DeepSeek V4 Pro)
