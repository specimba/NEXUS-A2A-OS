# Nexus OS - Sandbox Version
## Personal Working Copy for Testing & Development

**Location**: `NEXUS/sandbox/`  
**Purpose**: Isolated testing environment  
**Created**: 2025-03-21  
**Status**: Personal sandbox - safe to experiment

---

## What's Different Here?

This sandbox contains copies of core files with:
- **Mock credentials** pre-filled (safe to commit accidentally)
- **Test data** instead of real sessions
- **Simplified versions** for quick iteration
- **Experimental code** that may not be production-ready

---

## Quick Start

```bash
# Run mock server
python sandbox/mock_api_server.py

# Test GSPP converter
python sandbox/dg_to_gspp_test.py

# Run unit tests
pytest sandbox/tests/
```

---

## Sandbox-Specific Files

| File | Description |
|------|-------------|
| `.env.sandbox` | Pre-configured mock environment |
| `mock_data/` | Fake sessions and proposals |
| `experiments/` | Try-out code |
| `notes.md` | Personal scratchpad |

---

**Note**: This is MY personal working copy. Feel free to modify, break, and experiment here without affecting the main project.
