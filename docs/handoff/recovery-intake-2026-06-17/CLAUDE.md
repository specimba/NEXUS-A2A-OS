# CLAUDE.md — NEXUS OS Agent Protocol

**Note:** This file was reconstructed from log references (NEXUSv4planningCODEXlog-06.txt line 26847).
Original: 601 bytes, dated 2026-04-24 — content unrecoverable from archives.

## Purpose
Configuration for Claude Code (Anthropic CLI agent) operating in the NEXUS repository.

## Canonical Reference
For current agent operating protocol, see:
- `AGENTS.md` — Agent Operating Protocol (canonical, 167 lines)
- `01_PROJECT_STATE.md` — Current project state
- `knowledge.md` — Canonical Knowledge Base (385 lines, compiled 2026-06-13)

## Agent Rules (Reconstructed from Log Context)
- This repository is governed infrastructure
- Actions must be evidence-grounded, proposal-bound, test-gated, and auditable
- Read `01_PROJECT_STATE.md` first for canonical state
- Prefer filesystem state, tests, git history over chat memory
- Do not use `git add .`
- Core code changes require focused tests
- Security changes require hard-fail defaults
