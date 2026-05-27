# Integrate Zo Grok-Swarm into Grok's persistent_grok_agent.py

Drop-in patch for your sandbox. No new pip deps required.

---

## 1. Files to copy into Grok's sandbox

| Source (here on Zo) | Destination (in Grok sandbox) |
|---|---|
| `docs/grok-coordination/clients/nexus_swarm_client.py` | `/home/workdir/artifacts/nexus_swarm_client.py` |

That's the only file. Stdlib-only. ~7 KB.

---

## 2. Environment variables Grok needs

```
NEXUS_SWARM_TOKEN     = <bearer token operator generated in Zo Settings -> Advanced>
NEXUS_SWARM_URL       = https://specimba.zo.space/api/grok-swarm   (default; can omit)
NEXUS_SWARM_SANDBOX_ID = grok-prod-001                              (any stable id you want)
```

Important: `NEXUS_SWARM_TOKEN` must match the `GROK_SWARM_TOKEN` secret on Zo's side. Operator (speci) creates it once and pastes into both environments.

---

## 3. Patch persistent_grok_agent.py

Current state (broken — imports a stub that doesn't exist):

```python
from swarm_claw_client import SwarmClawClient
# ...
self.swarm = SwarmClawClient()
```

Replace with:

```python
from nexus_swarm_client import NexusSwarmClient, NexusSwarmError
# ...
try:
    self.swarm = NexusSwarmClient(sandbox_id=self.research_id)
except NexusSwarmError as e:
    logger.error(f"Swarm disabled: {e}")
    self.swarm = None
```

In `run_forever`, replace the stub heartbeat with a real one:

```python
# At the top of each loop iteration
if self.swarm:
    try:
        self.swarm.heartbeat(status="running", note=f"cycle {self.cycle_count}")
    except NexusSwarmError as e:
        logger.warning(f"Heartbeat failed (continuing): {e}")
```

Replace `_report_to_swarm` body:

```python
def _report_to_swarm(self, result):
    if not self.swarm:
        return
    try:
        if result.get("status") == "ERROR":
            self.swarm.report_failed(self.research_id, reason=result.get("error", "unknown"), cycle=self.cycle_count)
        else:
            self.swarm.report_progress(self.research_id, cycle=self.cycle_count,
                                       partial_result=result, notes="cycle complete")
    except NexusSwarmError as e:
        logger.warning(f"Swarm report failed (continuing): {e}")
```

---

## 4. New: pull-task-on-idle pattern

The big win: instead of running one fixed `research_id` forever, Grok claims tasks from the queue:

```python
def run_forever(self):
    while self.should_continue():
        # Pull next task from queue (or keep current claim)
        if not self.current_task or self.current_task_done:
            task = self.swarm.claim_next() if self.swarm else None
            if task is None:
                logger.info("Queue empty; sleeping 60s")
                time.sleep(60)
                continue
            self.current_task = task
            self.current_task_done = False
            self.cycle_count = 0

        # Run one cycle on the active task
        result = self._run_one_cycle_for_task(self.current_task)
        self.cycle_count += 1

        # Report progress every cycle
        if self.swarm:
            self.swarm.report_progress(
                self.current_task["id"],
                cycle=self.cycle_count,
                partial_result=result,
            )

        # Check completion
        if result.get("done") or self.cycle_count >= self.current_task.get("max_cycles", 4):
            if self.swarm:
                self.swarm.report_done(
                    self.current_task["id"],
                    final_result=result,
                    cycles_used=self.cycle_count,
                )
            self.current_task_done = True

        time.sleep(30)
```

---

## 5. Smoke test from inside Grok sandbox

```bash
export NEXUS_SWARM_TOKEN="<token>"
python3 /home/workdir/artifacts/nexus_swarm_client.py    # selftest, no network
python3 -c "
from nexus_swarm_client import NexusSwarmClient
c = NexusSwarmClient(sandbox_id='grok-smoke-test')
print('status:', c.status())
print('heartbeat:', c.heartbeat(note='smoke test'))
print('next task:', c.claim_next())
"
```

Expected:
- `status:` returns counts (likely all zero on first run) + last_heartbeat
- `heartbeat:` returns `{ok: true, heartbeat: {...}}`
- `next task:` returns `None` until operator adds tasks

---

## 6. Failure modes and what they mean

| Error | Cause | Fix |
|---|---|---|
| `NexusSwarmError: NEXUS_SWARM_TOKEN not set` | Env var missing in Grok sandbox | Set it from secret |
| `HTTP 401 ...` | Token mismatch between Zo and Grok | Re-sync the secret |
| `HTTP 502 ...` | zo.space restarting | Wait 30s and retry; client should auto-backoff |
| `Network error ... timed out` | Sandbox has no outbound HTTPS | Use Tailscale or proxy (Phase 3) |
| `task_id and status required` | Bad payload from a `report` call | Fix the caller — task_id is mandatory |

---

## 7. What this gives Grok

- **Persistence across resets** — claim leases survive sandbox restarts. When Grok wakes up, `claim_next` returns either the same task (still leased) or the next priority task.
- **No more crash-on-import** — the stub `SwarmClawClient` is replaced with a real, tested client.
- **External meta-controller** — Zo sees heartbeats and queue state; operator can intervene by adding/removing queue files directly.
- **Provider-agnostic** — Grok keeps full control of which LLM provider it uses; coordinator never touches model calls.
