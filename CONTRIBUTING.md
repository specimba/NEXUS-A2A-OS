# Contributing to NEXUS OS

Thank you for your interest in contributing to NEXUS OS.

---

## Contributor License Agreement

By submitting a pull request or patch, you agree to the following terms:

1. **You grant** a perpetual, royalty-free license to the project owner to use your contribution under Apache 2.0.
2. **You retain** copyright to your original work.
3. **For commercial derivatives** of Nexus OS, proper attribution is required (see `LICENSE`).

---

## Development Workflow

All changes follow the **Git-Versioned Agent Workflow (GVAW v1.0)**:

### 1. Branch from `master`

```bash
git checkout master
git pull origin master
git checkout -b feature/your-feature-name
```

### 2. Make changes + write tests

All new features require a corresponding test in `NEXUS-TEST.py`.

```bash
# After editing modules
python3 Skills/nexus-os/NEXUS-TEST.py
# All tests must pass before committing
```

### 3. Commit format

```
[type]([scope]): [description]

[Optional body]

[type] values:
  feat    — new feature
  fix     — bug fix
  docs    — documentation only
  test    — test only
  perf    — performance improvement
  nexus   — NEXUS OS framework changes
```

Examples:
```
feat(gmr): add speculative routing proxy
fix(vault): correct KV compression anchor token boundary
nexus: P0b calibrate OR-Bench lane thresholds
docs: update README with new relay endpoints
```

### 4. Push and open PR

```bash
git push origin feature/your-feature-name
# Then open a pull request on GitHub
```

### 5. PR Requirements

- [ ] All tests pass (`python3 Skills/nexus-os/NEXUS-TEST.py`)
- [ ] No new linting errors
- [ ] PR description links to relevant issue or research

---

## Agent Commit Protocol

If you are an AI agent working in a sandbox, use this exact format:

```bash
git commit -m "feat(skill): add self-improvement v0.1.0

[agent: your-model-id]
[proposal: <proposal_id>]

Implements weekly reflection audit.
Passes KAIJU, ASBOM clean, TokenGuard 15k allocated."
```

**Pre-commit hook** (when active) validates proposal_id before allowing commit.

---

## Project Structure

```
Skills/nexus-os/
├── SKILL.md                 ← Skill manifest
├── NEXUS-TEST.py            ← 9/9 test suite
├── src/nexus_os/
│   ├── bridge/              ← Auth, JSON-RPC, MCP-Auth
│   ├── engine/              ← Intent routing, ToolGates
│   ├── governor/            ← Trust scoring, RigorLLM, ShieldGemma, AEGIS
│   ├── vault/               ← 8-channel memory, KV compression
│   ├── gmr/                 ← Speculative router, circuit breaker, TALE
│   ├── swarm/               ← deer-flow pool, auction allocation
│   ├── monitoring/          ← TokenGuard, TokenTracker
│   ├── skillsmith/          ← Auto-register skill discovery
│   ├── stresslab/            ← ISC-Bench TVD runner
│   ├── relay/                ← API relay, GSPP endpoints
│   ├── observability/        ← VAP proof chain
│   └── config/              ← Constitution
└── [other skills from /Skills]
```

---

## Running the Full Test Suite

```bash
cd /home/workspace
python3 Skills/nexus-os/NEXUS-TEST.py
```

Expected result: `9/9 PASS`

---

## Style Guide

- Python 3.10+
- Docstrings for all public classes and methods
- No hardcoded secrets — use environment variables
- Max line length: 100 characters

---

## Reporting Issues

Please include:
- Git commit (`git log -1 --oneline`)
- Test output (`python3 Skills/nexus-os/NEXUS-TEST.py`)
- Python version (`python3 --version`)

---

## Contact

- GitHub Issues: https://github.com/specimba/NEXUS-A2A-OS/issues
- Owner: specimba
