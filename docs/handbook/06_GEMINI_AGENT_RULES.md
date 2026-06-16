# NEXUS OS — Gemini Agent Operational Rules

## 1. Tool Discipline Invariant (The Golden Rule)
- **NO SANITY TOOLS**: Under no circumstances should lazy-loaded Sanity tools (e.g., `Sanity_search_docs`, `deploy_schema`, `query_documents`) be invoked. These tools trigger recurrent loop bugs in tool parsing/selection logic.
- **Allowed Tools**: Only use native filesystem and command-execution tools:
  - `view_file`, `replace_file_content`, `multi_replace_file_content`, `write_to_file`
  - `list_dir`, `grep_search`
  - `run_command` (for running tests, checks, and process controls)

## 2. Hard Verification & Evidence-Gated Claims
- **Strict Honesty**: Do not mark items as completed `[x]` in `task.md` or claim success in `walkthrough.md` unless they have been executed, verified, and evidenced in the workspace.
- **Evidence Sources**: A change is only verified if:
  - It compiles successfully with zero warnings/errors.
  - Relevant unit tests pass (`pytest` or `run_tests.py` output returns exit code 0).
  - The live benchmark track (if affected) executes successfully.
- **Unearned Claims**: Do not assume Codex or other agents' commits count as Antigravity progress. Attribute work honestly.

## 3. Pytest & Test Runner Integration
- **Real Pytest First**: The custom test runner `tests/run_tests.py` has been updated to automatically detect and run tests via `pytest` if available. This ensures full fixture support (`vault`, `tracker`, `scorer`, `db`) and avoids mock shim failure.
- **Test Command**: Run `python tests/run_tests.py [subset]` to run tests. Do not run custom test loops.

## 4. Environment and Key Management
- **Key Location**: Masked keys and new API keys must be configured in `c:\Users\speci.000\Documents\NEXUS\.env.local` to prevent leaking them into untracked commits or source files.
- **Verification of Keys**: Before declaring an API key integrated, run a lightweight, non-writing script or query to verify the key receives a `200 OK` from the provider.

## 5. Loop Escape Protocol
- If you find yourself repeating the same tool call with minor modifications, **STOP**.
- Inspect the system prompt, guidelines, and target file contents.
- Do not attempt more than 3 consecutive failing tool calls before asking the user for clarification or providing a clean exit report.
