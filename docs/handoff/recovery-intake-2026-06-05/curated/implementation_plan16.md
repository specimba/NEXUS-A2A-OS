# Implementation Plan: Meta Spark Agent Sandbox & A2A Integration

This plan integrates the **Meta Spark Agent** (Lead Archivist persona running in its own virtual sandbox) into the NEXUS OS Archivist system. It enables reading/parsing the Meta Spark sandbox exports, displaying its status and ingested files dynamically in the dashboard, and providing the standard Agent-to-Agent (A2A) protocol endpoints to connect the sandbox with Microsoft Foundry.

---

## User Review Required

> [!IMPORTANT]
> **Integration Architecture:**
> - **Meta Spark Sandbox Ingestion**: We will scan for files matching `NEXUS-OS-archivist-online*.document` in `C:\Users\speci.000\Downloads\ARCHIVIST\`. The latest file by modification time will be parsed to retrieve the Meta Spark sandbox state (installed modules, status, boot time, capacity, and its scanned files list).
> - **A2A Endpoint**: We will expose `/.well-known/agent-card.json` (served as a static file in public/ or dynamic API route) and `/api/archivist/a2a` to provide Agent-to-Agent connection endpoints as described in the Microsoft Foundry integration logs.
> - **UI/UX Aesthetics**: We will add a tab/section in the Archivist dashboard showing the Meta Spark Sandbox Status, Console log logs, Ingested Files table, and A2A configuration parameters.

---

## Proposed Changes

### 1. Static Configuration / Public assets

#### [NEW] [agent-card.json](file:///c:/Users/speci.000/Documents/NEXUS/public/.well-known/agent-card.json)
- Create the Agent Card definition file containing metadata of the Lead Archivist agent:
  - Name: "nexus-archivist-lead"
  - Display Name: "NEXUS OS Lead Archivist"
  - Description: "Governed Lead Archivist for NEXUS OS archive indexing, log search, and data dump generation."
  - A2A Endpoint URL: `http://localhost:7352/api/archivist/a2a` or `/api/archivist/a2a`
  - Authentication: `Key-based`

### 2. Next.js API Routes (Backend)

#### [MODIFY] [route.ts](file:///c:/Users/speci.000/Documents/NEXUS/src/app/api/archivist/route.ts)
- Extend the `GET` endpoint to:
  - Find all `NEXUS-OS-archivist-online*.document` files in `C:\Users\speci.000\Downloads\ARCHIVIST\`.
  - Parse the latest one by mtime.
  - Extract the sandbox state (`ingest_time_utc`, `last_update_utc`, `count`, and the `files` array listing size, sha256, and previews).
  - Inject this parsed state as `metaSparkSandbox` object in the JSON response.
- Extend the route to handle the A2A tool schemas or create a separate route if needed. We will keep it consolidated under `src/app/api/archivist/route.ts` or add `/api/archivist/a2a` as a new route.
  *(Consolidating by adding a conditional A2A sub-handler or a separate route file is standard. Let's create a separate route file for clarity to keep things clean).*

#### [NEW] [route.ts](file:///c:/Users/speci.000/Documents/NEXUS/src/app/api/archivist/a2a/route.ts)
- Create `/api/archivist/a2a` to respond to A2A handshake/message protocols.
- Include a simple dynamic ping-pong, tool capabilities list, and auth-verification handler.

### 3. Next.js Frontend Dashboard (UI)

#### [MODIFY] [archivist-tab.tsx](file:///c:/Users/speci.000/Documents/NEXUS/src/components/nexus/tabs/archivist-tab.tsx)
- Upgrade the layout to display a beautiful new component panel: **"Meta Spark Sandbox Bridge"**.
- UI widgets will include:
  - **Live Console Emulator**: displaying the boot log and state JSON of the Lead Archivist persona (`NEXUS OS // Lead Archivist - SYSTEM ONLINE`).
  - **Sandbox Status Indicators**: showing storage (512GB virtual volume), python runtime version (Python 3.9), and the active modules list (`archive_manager v2.4`, `log_indexer v1.9`, `data_dumper v3.1`, `strategist_core v0.8`).
  - **Ingested Files Inventory**: a searchable, paginated table listing the files scanned in the Meta Spark sandbox (from the parsed `.document` file) with their sizes and previews.
  - **A2A Connection Coordinates**: copy-to-clipboard blocks for A2A Endpoint, Agent Card Path, and Anonymous/Key-based Credentials configuration.
- Style with glassmorphism, custom glowing badges, gradient animations, and smooth transitions.

---

## Verification Plan

### Automated Tests
- We will verify that the Next.js application builds correctly:
  ```bash
  npm run build
  ```

### Manual Verification
- Deploy/start Next.js in development mode:
  ```bash
  npm run dev
  ```
- Navigate to the **Archivist Tab** on the dashboard.
- Verify that the **Meta Spark Sandbox Bridge** renders correctly, displaying:
  - The offline/online status correctly parsed from the latest `NEXUS-OS-archivist-online (3).document`.
  - The files list matches the 36 files listed in the document.
  - The boot log screen scrolls/emulates correctly.
- Test endpoint requests to `/api/archivist/a2a` and `/.well-known/agent-card.json` to ensure they return valid JSON.
