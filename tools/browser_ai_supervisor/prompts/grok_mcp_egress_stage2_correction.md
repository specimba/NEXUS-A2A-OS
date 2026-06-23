Your Stage 2 answer is not acceptable yet. Continue from it and repair the proposal.

Verified local facts from Codex:
- `nexus_os/bridge/browser_http_diagnostic.py` already has:
  - `BrowserDiagnosticPolicy`
  - `DEFAULT_ALLOWED_HOSTS`
  - `BLOCKED_HEADER_PREFIXES`
  - `_sanitize_headers`
  - `_is_private_or_local_host`
  - `validate_browser_diagnostic_request`
  - `BrowserHTTPDiagnosticRelay.prepare()`
  - `BrowserHTTPDiagnosticRelay.invoke()`
  - JSON-RPC path `/invoke`
  - A2A path `/a2a/tasks/send`
- `nexusctl gross-http` already supports:
  - dry-run default via `relay.prepare(...)`
  - `--live` via `relay.invoke(...)`
  - `--bridge-url` default `http://127.0.0.1:7354`
  - `--method GET|HEAD`
  - `--safe-preview-max`
  - `--audit-id`, `--scenario`, `--operator`
- Your proposed private-IP check is buggy because it catches the `ValueError` it raises inside `except Exception`.
- Your proposed `GovernedEgressRelay` duplicates the existing relay instead of reusing it.
- Your proposed tests are too weak: `assert result.status in ("planned", "executed", "error")` proves nothing.

Repair mission:
Produce a second-stage implementation package that minimally extends the existing `BrowserHTTPDiagnosticRelay`, without parallel incompatible classes.

Deliverables:
1. Exact flaws/gaps that remain in the real local files after acknowledging existing features.
2. Minimal patch design, preferably:
   - add optional `token_budget_checker` and `approval_checker` callables to `BrowserHTTPDiagnosticRelay`
   - add a structured `execute_governed(...)` method or similar wrapper that uses existing `prepare()` and `invoke()`
   - keep default dry-run behavior
   - live calls only after policy accepts and optional governance allows
3. Full proposed diff or full replacement functions against exact files:
   - `nexus_os/bridge/browser_http_diagnostic.py`
   - optional test file under `tests/bridge/`
   - only touch `nexusctl.py` if a real missing flag exists; do not re-add flags it already has.
4. Strong offline tests with fake transport:
   - dry-run allowed returns gross_arguments and no transport call
   - live allowed calls fake transport exactly once
   - host blocked calls fake transport zero times
   - method blocked calls fake transport zero times
   - auth/cookie/x-api-key headers stripped
   - token budget denied blocks before transport
   - approval required for non-read/high-risk wrapper blocks before transport
   - JSON-RPC/A2A bridge error is surfaced
5. Exact local verification command.
6. One operator-only live command using existing `nexusctl gross-http --live`, not a fake new CLI.

Do not output broad architecture prose. Output the repaired concrete package. If you need to say “advisory until Codex applies/tests,” say it once at the end.
