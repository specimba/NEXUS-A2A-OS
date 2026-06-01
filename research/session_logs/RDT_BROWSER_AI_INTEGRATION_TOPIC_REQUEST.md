# R&D Research Topic Request: Browser-Based AI Integration

**Requestor:** Speci (R&D Lead)  
**Classification:** SECRET LABS — R&D Backend Team  
**Status:** Research Topic — Awaiting Deep Dive  
**Date:** 2026-05-13  

---

## 1. Research Question

> How can NEXUS OS integrate browser-based, non-API AI systems (Grok xAI sandbox, Gemini Coder, Qwen Coder) into governed, automated workflows — despite these systems having no REST API, only browser/message-activated interfaces — without relying on conventional API credit budgets?

---

## 2. Background & Assets

### Confirmed Assets

| Asset | Type | Access Level | Details |
|-------|------|-------------|---------|
| **Grok xAI 4.3** | Partnership | ✅ API + Sandbox + Project Folders | `api.x.ai/v1` OpenAI-compatible. Partnership includes extra permissions, sandbox access, project foldering. |
| **Gemini Coder** | Browser | Free (browser-only) | Google's free browser coding environment |
| **Qwen Coder** | Browser | Free (browser-only) | Alibaba's free browser coding environment |
| **Grok 4.3 API** | REST API | ✅ Via partnership | `grok-4.3` model, 2M context, tools, vision. Standard OpenAI SDK compatible. |
| **xAI MCP Server** | Community | Open source | `github.com/joemccann/xai-mcp-server` — wraps Grok as MCP tools |
| **Hyperbrowser** | Service | ✅ Available | Browser automation for agents |
| **WebContainers** | Platform | Browser-native | StackBlitz's in-browser code execution |

### Key Insight

The premise says "no API" — but **Grok actually HAS an API** (`https://api.x.ai/v1`) through the partnership. The sandbox + project foldering are additive features ON TOP of API access. The real challenge is integrating:

1. The browser-only systems (Gemini Coder, Qwen Coder)
2. The sandbox capabilities (code execution environments)
3. Message-triggered scheduling (not REST-polled)

---

## 3. Research Vectors

### Vector A: API Integration (Grok — Already Viable)

Grok 4.3 is accessible via standard OpenAI-compatible API:

```
Endpoint: https://api.x.ai/v1
Models: grok-4.3, grok-4-1-fast-reasoning, grok-4-20-beta-reasoning
Auth: XAI_API_KEY (partnership)
Features: Tools, vision, web search, code execution, 2M context
```

Community MCP servers already exist for Grok:
- `github.com/joemccann/xai-mcp-server` — Chat, vision, image gen, search, video
- `github.com/merterbak/Grok-MCP` — Agentic tool calling, code execution
- `github.com/LyoSU/grok-search-remote-mcp` — Web/X search as MCP

**Integration path:** Standard MCP → NEXUS bridge. No special workaround needed.

### Vector B: Browser-Only Systems (Gemini Coder, Qwen Coder)

These have no public API. Approaches ranked by legitimacy:

| Approach | Risk | Effort | Description |
|----------|------|--------|-------------|
| **B1: Official API check** | None | Low | Check if Google AI Studio / Alibaba have hidden/free API endpoints. Gemini API exists (`generativelanguage.googleapis.com`). Qwen has API via Alibaba Cloud. |
| **B2: Browser automation** | Low | Medium | Use Hyperbrowser + Playwright to interact with web UI programmatically. Feed outputs into NEXUS pipeline. Legitimate automation. |
| **B3: MCP bridge** | Low | Medium | Build an MCP server that wraps browser automation as standard tools. Outputs become MCP resources consumable by any agent. |
| **B4: WebContainer sandbox proxy** | Low | High | WebContainers run in-browser but can be orchestrated from outside. Proxy inputs/outputs through WebContainer API. |

### Vector C: Sandbox-Integrated Scheduling

The message-triggered, scheduled task initiator problem:

| Approach | Description |
|----------|-------------|
| **C1: Composio triggers** | GitHub events, Gmail labels, Slack messages → webhook → NEXUS → Grok API call |
| **C2: Zo scheduled agents** | Zo's built-in scheduling → A2A task → NEXUS execution |
| **C3: Notion AI agent bridge** | Notion's task system + Opus 4.7 → triggers → Grok sandbox |
| **C4: Custom webhook receiver** | Lightweight FastAPI endpoint on Fly.io → receives messages → routes to correct sandbox |

---

## 4. Proposed Integration Architecture

```
                    TRIGGER SOURCES
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ GitHub   │  │ Slack    │  │ Gmail    │  │ Scheduled│
  │ Webhook  │  │ Message  │  │ Label    │  │ Agent    │
  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │              │              │              │
       └──────────────┼──────────────┼──────────────┘
                      │              │
              ┌───────▼──────────────▼────────┐
              │       COMPOSIO EVENT BUS       │
              │  (Triggers → Webhook → Route)  │
              └───────────────┬────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │       NEXUS OS GATEKEEPER      │
              │  KAIJU evaluate → TokenGuard   │
              │  VAP log → Route to executor    │
              └───────────────┬────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ GROK API     │   │ BROWSER AUTO │   │ FREE API     │
  │ (Partnership)│   │ (Hyperbrowser)│   │ (Gemini/Qwen)│
  │ 4.3 / MCP    │   │ Gemini Coder │   │ AI Studio    │
  │ Sandbox      │   │ Qwen Coder   │   │ etc.         │
  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  NEXUS VAULT   │
                    │  Result store  │
                    │  VAP audit log │
                    └────────────────┘
```

---

## 5. Research Deliverables Requested

| # | Deliverable | Priority |
|---|-------------|----------|
| 1 | Full API surface audit of Grok partnership (actual endpoints, rate limits, sandbox features) | P0 |
| 2 | Gemini Coder / Qwen Coder — verify if hidden/free API endpoints exist or if browser automation is the only path | P0 |
| 3 | MCP server integration path for Grok 4.3 (existing community MCP → NEXUS MCP bridge) | P0 |
| 4 | Composio ↔ Scheduled Agents ↔ Sandbox message routing design | P1 |
| 5 | WebContainer API feasibility study for in-browser execution orchestration | P1 |
| 6 | Security analysis: risks of browser-automation-based integration vs native API | P1 |
| 7 | Cost comparison: "unlimited" browser vs API credit vs partnership perpetual access | P2 |

---

## 6. Key Constraints

- **No API credit budgets** for browser-based systems — the value proposition IS unlimited access
- **Partnership assets** (Grok sandbox, project folders) must be preserved and enhanced, not bypassed
- **All integrations must pass KAIJU gates** — no ungoverned access to any model
- **Gray area techniques** documented but flagged — all production integrations must be defensible
- **Message/schedule triggering** must work without human intervention for autonomous workflows

---

## 7. Related Resources

| Resource | URL |
|----------|-----|
| Grok API Docs | `docs.x.ai/developers/quickstart` |
| xAI MCP Server | `github.com/joemccann/xai-mcp-server` |
| Grok-MCP (full featured) | `github.com/merterbak/Grok-MCP` |
| WebContainers API | `webcontainers.io/ai` |
| OpenSandbox (Alibaba) | `github.com/alibaba/OpenSandbox` |
| Hyperbrowser Docs | `hyperbrowser.ai/docs` |
| Composio Triggers | `docs.composio.dev/docs/triggers` |
| NEXUS GitHub Sync | `github.com/specimba/nexusalpha` |

---

*Research Topic prepared for SECRET LABS deep dive.*  
*Return date: TBD — Speci coordinating multiple concurrent lab investigations.*
