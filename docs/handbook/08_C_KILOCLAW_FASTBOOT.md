# C-KILOCLAW Fast Boot Guide

## Cloudflare-Powered Experimental Lab

**Target:** 15 minutes from zero to running  
**Base:** Cloudflare Workers + Sandbox SDK + OpenCode MCP  
**Models:** Workers AI (free tier), Grok 4.3 (partnership), Ernie, GLM 5.1, Kilo free  

---

## Step 1: Bootstrap Cloudflare

```bash
# Install Wrangler (already have it? skip)
npm install -g wrangler

# Login
wrangler login

# Verify
wrangler whoami
```

## Step 2: Create C-KILOCLAW Worker

```bash
# Scaffold
npx wrangler init c-kiloclaw --yes --git=false
cd c-kiloclaw

# Add Cloudflare Skills (agent context)
npx skills add https://github.com/cloudflare/skills

# Enable Sandbox SDK in wrangler.jsonc
cat > wrangler.jsonc << 'EOF'
{
  "name": "c-kiloclaw",
  "main": "src/index.ts",
  "compatibility_date": "2026-05-13",
  "observability": { "enabled": true },
  "migrations": [
    { "tag": "v1", "new_classes": ["KiloclawSandbox"] }
  ]
}
EOF
```

## Step 3: Write the Kiloclaw Agent

```typescript
// src/index.ts — C-KILOCLAW experimental agent runner
import { WorkerEntrypoint } from "cloudflare:workers";
import { Sandbox } from "cloudflare:sandbox";

export default class KiloclawAgent extends WorkerEntrypoint {
  async run(request: Request): Promise<Response> {
    const { code, model, timeout } = await request.json();
    
    // Sandbox SDK — secure code execution, zero local resource burn
    const sandbox = new Sandbox({ maxMemory: 256, timeout: timeout ?? 30 });
    const result = await sandbox.run(code);
    
    // VAP audit stub — log to D1 or KV
    await this.logExperiment({ code, result, model });
    
    return Response.json(result);
  }
  
  async logExperiment(data: any) {
    // Stub: wire to NEXUS VAP chain later
    console.log(JSON.stringify(data));
  }
}

// Durable Object for stateful experimental sessions
export class KiloclawSandbox {
  private state: Map<string, any>;
  
  constructor() { this.state = new Map(); }
  
  async fetch(request: Request) {
    // Long-running experiments survive restarts
    return new Response("sandbox ready");
  }
}
```

## Step 4: Configure OpenCode for C-KILOCLAW

Add to `.opencode.jsonc`:

```json
{
  "mcp": {
    "cloudflare": { "type": "remote", "url": "https://mcp.cloudflare.com/mcp", "enabled": true },
    "cloudflare-docs": { "type": "remote", "url": "https://docs.mcp.cloudflare.com/mcp", "enabled": true },
    "cloudflare-sandbox": { "type": "remote", "url": "https://sandbox.mcp.cloudflare.com/mcp", "enabled": true },
    "cloudflare-containers": { "type": "remote", "url": "https://containers.mcp.cloudflare.com/mcp", "enabled": true },
    "cloudflare-ai-gateway": { "type": "remote", "url": "https://ai-gateway.mcp.cloudflare.com/mcp", "enabled": true },
    "cloudflare-observability": { "type": "remote", "url": "https://observability.mcp.cloudflare.com/mcp", "enabled": true }
  },
  "skills": {
    "cloudflare": { "url": "https://github.com/cloudflare/skills", "enabled": true }
  }
}
```

## Step 5: Deploy

```bash
wrangler deploy
# → https://c-kiloclaw.<your-subdomain>.workers.dev
```

## Step 6: Test

```bash
# From OpenCode:
# "Run this Python experiment in C-KILOCLAW sandbox: import numpy as np..."
# Cloudflare Sandbox SDK executes it securely, no local CPU burn.
```

## Architecture

```
OpenCode (your terminal)
  │  MCP calls via .opencode.jsonc
  ▼
Cloudflare Edge
  ├── Sandbox SDK → secure code execution (C-KILOCLAW experiments)
  ├── Workers AI → free model inference
  ├── AI Gateway → model routing, cost tracking
  ├── Container MCP → disposable dev environments
  ├── D1/KV → experiment storage → VAP sync
  └── Observability → logs, traces, metrics
  │
  ▼
NEXUS Vault (sync via MCP bridge later)
```

## Model Routing

| Experiment Type | Model | Provider | Cost |
|----------------|-------|----------|------|
| Quick code | Workers AI @cf/meta/llama-3.2-3b | Cloudflare free | $0 |
| Reasoning | Grok 4.3 | xAI partnership | $0 |
| Experimental | Ernie, GLM 5.1, Kilo free | External API | $0 |
| Heavy | DFlash via Workers AI | Cloudflare | Free tier |

## C-KILOCLAW Principles

1. **Zero local resource burn** — everything runs on Cloudflare edge
2. **Disposable by design** — sandbox destroyed after each experiment
3. **VAP audit stub** — all experiments logged for NEXUS governance
4. **Model-agnostic** — swap models without changing code
5. **OpenCode-native** — all interaction via MCP from your terminal

---

*Next: Wire VAP audit sync, connect Pinecone/GPT-5 for KB, add Hyperbrowser for web experiments.*
