# Nexus Plugin Hygiene Policy

## Purpose
Reduce token waste and connector noise by keeping plugin use workspace-scoped, explicit, and task-driven.

## Keep
| Plugin | Use |
|---|---|
| GitHub | PRs, commits, reviews, issue references, release grounding, branch and backup gates. |
| Build Web Apps | Nexus Control Center, GeniusTurtle UI, dashboard/frontend work, React/Next UI reviews. |
| Linear | Roadmap, milestones, external-team task handoff, status updates when Linear is active. |
| Slack | Drafting updates, reading team channels, publishing concise execution summaries. |
| Cloudflare | Optional deployment target for Workers, Pages, or MCP hosting after explicit selection. |

## Disabled By Default
| Plugin | Reason |
|---|---|
| Atlassian Rovo | GitHub, Linear, and Markdown are the current Nexus sources of truth. |
| Superpowers | No concrete exposed capability is needed for current Nexus workflow. |
| Test Android Apps | Nexus, TWAVE, and GeniusTurtle have no Android app scope right now. |
| CodeRabbit | Redundant with GitHub plus Codex review gates until PR volume grows. |
| Render | Not the selected deployment target; Cloudflare/local FastAPI is preferred for this phase. |

## Use Rules
- Default prompt should mention no plugins.
- Mention exactly one plugin when the task requires it.
- Mention two plugins only for cross-system work.
- Do not invoke external plugins for local filesystem inspection.
- Do not use deployment plugins until local tests and contract checks pass.

## Enforcement
- Coordinator must prefer local files, git state, Nexus skills, and tests.
- If a disabled-by-default plugin is requested, first verify that its capability is explicitly required.
- If a task can be solved locally without a plugin, solve it locally.

