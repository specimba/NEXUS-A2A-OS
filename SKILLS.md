# SKILLS.md — NEXUS OS Skills Registry

## Mission

Track agent capabilities, skill assignments, and proficiency levels across the NEXUS OS ecosystem.

## Skill Categories

| Category | Description | Examples |
|----------|-------------|----------|
| governance | Policy enforcement, trust scoring, compliance | KAIJU gates, trust formulas, VAP |
| security | Vulnerability scanning, sanitization, audit | TerminalSanitizer, BOUNCER, gitleaks |
| orchestration | Task routing, swarm coordination, 24/7 ops | NEXUSCLAW, Hermes, GMR |
| memory | Channel management, consolidation, ARCHIVIST | 8-Channel Memory, LightMem, dossier synthesis |
| bridge | External API integration, MCP, protocol adapters | ModelRelay, MCP servers, SDK wrappers |
| research | Evidence gathering, paper processing, benchmarking | DoppelGround, NEXUS-Bench, PAPERS pipeline |
| ui | Dashboard, visualization, operator interfaces | GeniusTurtle, GLM 5.1, Next.js |

## Proficiency Levels

- **0.0-0.3**: Novice — supervised execution only
- **0.3-0.6**: Competent — can execute with review
- **0.6-0.8**: Proficient — autonomous execution in lane
- **0.8-1.0**: Expert — can mentor other agents

## Skill Worklog

NEXUSCLAW maintains a worklog for every agent action. Entries are written to:
- **8-Channel Memory** (EPISODIC, TASK, META channels) for agent context continuity
- **ARCHIVIST queue** for long-term dossier synthesis
- **Markdown worklogs** (AGENTS.md, SKILLS.md, SOUL.md) for human audit

Format: `timestamp | agent_id | intent → status | duration_ms | task_id`
