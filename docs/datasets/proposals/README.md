# NEXUS Dataset Proposals — Output Index

This folder holds weekly dataset ideation from the `Zo-NEXUS-Dataset-Ideation` automation.

## What lives here

One file per ISO week:

```
docs/datasets/proposals/YYYY-Www.md
```

Each file contains **3 concrete dataset ideas**, grounded in actual files under `src/nexus_os/`.

## File shape

```markdown
# NEXUS Dataset Proposals — 2026-Www (Mon DD – Sun DD)

## Grounding scan
Modules touched this week: <list from git log>
Open detection / governance code referenced: <file paths>

## Proposal 1: <name>
- **Source**: <where the data comes from — public dataset, scraped, synthetic, etc.>
- **Schema**:
  ```
  field: type   description
  ...
  ```
- **Why NEXUS cares**: <2 lines, tied to a specific module>
- **Estimated effort**: S / M / L (with rough hour band)
- **First slice**: <smallest useful version to build first>

## Proposal 2: ...

## Proposal 3: ...

## Trade-offs to flag for speci
- <decisions where the agent does not have authority>
```

## Cadence

Weekly, Sundays at 10:00 Istanbul time. One file per week. Two-week gaps (no file) mean the automation failed and needs attention.

## Filter rules

- **No external API calls beyond ModelRelay.** No HuggingFace login, no scraping behind auth walls.
- **No download attempts.** Proposals are specs, not data acquisition.
- **No commit to `src/`.** All output goes under `docs/datasets/proposals/`.
