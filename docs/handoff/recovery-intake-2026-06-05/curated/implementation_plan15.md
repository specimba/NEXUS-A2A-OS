---
id: NODE-MIG-IMPLEMENTATION_PLAN15
authority_scope: historical-import
origin_sha256: b193e8411b576de5c0afbc01fd61879de87f4d884adff455968d9c1a70674239
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: native-kernel
approval_id: APP-MIG-C04A29
---
# Implementation Plan: Archivist Live Integrity Verification & Dump Integration

We will replace the static mocks in `/api/archivist` with a live scanner that reads markdown files from the NEXUS workspace and the `ARCHIVIST` downloads folder. It will execute the validation rules from `test_archivist_integrity-meta.py` and `test_archivist_integrity-grok.py`, calculate real truth-layer distributions, check for broken wiki links, identify structural contradictions, and update the Next.js Archivist Tab dynamically.

---

## User Review Required

> [!IMPORTANT]
> **Workspace Scanning Scope & Classification Fallbacks:**
> - The scanner will read `.md` files in `docs/` and the repo root `c:\Users\speci.000\Documents\NEXUS`, as well as files in the `C:\Users\speci.000\Downloads\ARCHIVIST` folder.
> - If a file does not have frontmatter or is missing `truth_layer`, we will classify it by location (e.g. `raw/` as `SOURCE`, `published/` as `CANONICAL`, root files as `CANONICAL`) to prevent everything showing up as failed/empty.
> - Contradictions will be detected for:
>   - Duplicate Node IDs (CRITICAL)
>   - Invalid confidence score ranges (CRITICAL)
>   - Stale/high-confidence `INFERRED` nodes (WARNING)
>   - Missing required fields like `canonical_ref` on `INFERRED`/`CANONICAL` nodes (WARNING)
>   - Broken `[[wiki-links]]` that don't match any scanned node ID or filename (WARNING)

---

## Proposed Changes

### Next.js API Route Backend

#### [MODIFY] [route.ts](file:///C:/Users/speci.000/Documents/NEXUS/src/app/api/archivist/route.ts)
- Replace static JSON return with a live Node.js file scanner:
  - Crawl `.md` files recursively in `c:\Users\speci.000\Documents\NEXUS/docs/` and root `c:\Users\speci.000\Documents\NEXUS/`.
  - Crawl `.md` files recursively in `C:\Users\speci.000\Downloads\ARCHIVIST/`.
  - Exclude `.git`, `.next`, `node_modules`, `.venv`, `venv`, and `.nexus_pi`.
  - Extract YAML frontmatter and file metadata.
- Implement the integrity validation rules:
  - Verify required fields: `id`, `truth_layer`, `created` or `provenance`, `verified`.
  - Validate confidence score range `[0.0, 1.0]`.
  - Validate `canonical_ref` matching known files.
  - Scan file bodies for wiki links `[[target]]` and verify if `target` exists.
- Implement contradiction detection:
  - Identify duplicate `id` keys.
  - Identify missing `provenance` on `SOURCE` nodes.
  - Identify missing `canonical_ref` on `INFERRED` or `CANONICAL` nodes.
- Calculate dynamic statistics for:
  - `truthLayers`
  - `authorityDistribution`
  - `curatorStats` (based on file modification dates)
  - `integrityFields` (`authority_scope`, `origin_sha256`, `policy_hash`, `sandbox_profile`, `approval_id`)
  - `releaseReadiness` (checks presence/cleanliness of critical files like `README.md`, `AGENTS.md`)
- Add VAP audit logging support by writing the verification result as a JSON audit log into `docs/wiki/graph/archivist_audit.json` when the `POST` verify action is called.

---

## Verification Plan

### Automated Tests
- We will write a TypeScript/Node script to test our scanner function:
  ```powershell
  bun run src/app/api/archivist/route.ts --test
  ```
  *(We can add a CLI-test toggle in the route code that runs if a specific env/flag is passed)*

### Manual Verification
- Start Next.js development server and verify the page updates in real-time.
- Click "Verify Integrity" on the Archivist dashboard tab, and ensure the toast displays the actual node count and verified issues list correctly.
