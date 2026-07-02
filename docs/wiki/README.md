---
id: NODE-MIG-README
authority_scope: local-canonical
origin_sha256: bf1e113fa3dee0c010bfd0b4d1f3b1caf2d6d58243a06fc30ac7fb7282f3f6a2
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B33563
---
# NEXUS ReviewGround Wiki Workspace

<!-- CANARY: ecbdfc7f80270623f93cb03e7d23470b -->
This folder is the planned local workspace for the ReviewGround / Obsidian / LLM-wiki lane.

## Intended Layout

```text
docs/wiki/
  raw/        immutable source captures
  briefs/     source summaries with hashes and evidence quality
  drafts/     generated pages awaiting review
  published/  approved wiki pages
  graph/      generated graph JSON, link checks, validation reports
  obsidian/   exported vault view
```

## Rules

- Raw sources are immutable once captured.
- Draft pages are not canonical.
- Published pages require frontmatter and review metadata.
- Generated wiki output is evidence, not automatic NEXUS truth.
- Canonical promotion still goes through NEXUS governance and audit gates.

## Immediate Source Assets

- `upload/wiki_pipeline.py`
- `C:\Users\speci.000\Downloads\DERDDRE\v4\handbook\07_WIKI_AND_REVIEWGROUND.md`
- `C:\Users\speci.000\Downloads\DERDDRE\v4\dashboard\static\src\pages\Wiki.jsx`
- `docs/handoff/NEXUS_VISIBLE_LAYERS_ACTIVE_INTEGRATION_BLUEPRINT_2026-05-26.md`

## Obsidian integration (2026-07-02)

The canonical intel vault is `nexus_os/archivist/wiki/` — open THAT folder
directly as an Obsidian vault. It carries a committed `.obsidian/` config
(graph color groups: dossiers green, sources amber, entities cyan, concepts
violet; core plugins only, no community plugins; `workspace.json` is
git-ignored per machine). Dossiers emit `[[wikilinks]]` to source and
concept stub pages, and `index.md` is the regenerated Map of Content —
graph view works with zero plugins.

The `obsidian/` subdirectory here (`docs/wiki/obsidian/`) is a deprecated
export slot: exporting copies would drift from the pipeline-written canon.
