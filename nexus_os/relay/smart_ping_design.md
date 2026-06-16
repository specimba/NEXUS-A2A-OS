# NEXUS OS — Smart Ping Interval System Design
## Version: 2026-06-09
## Status: Design Document (Ready for Implementation)

---

## Problem Statement

Current ModelRelay pings ALL models every 1-5 minutes regardless of whether anyone is using the system. This:
- Burns GPU cycles (Ollama model loading/unloading)
- Exhausts free provider quotas (especially GitHub 1500/day, Cloudflare 10k/day)
- Wastes API calls for providers that are DOWN (NVIDIA 404s, Google 429s)
- Generates 840+ health checks/hour for no reason during idle periods

**Goal:** Demand-driven health checks that scale from 15min (active) to 4 hours (idle).

---

## Architecture

```
[User Activity Monitor]          [ModelRelay Config]          [Providers]
        │                               │                          │
        │  activity_detected()          │                          │
        │──────────────►│ set_interval(ACTIVE)                   │
        │               │────────────►│ ping every 15 min        │
        │                               │                          │
        │  idle_timeout(30min)          │                          │
        │──────────────►│ set_interval(COOLDOWN)                 │
        │               │────────────►│ ping every 60 min        │
        │                               │                          │
        │  idle_timeout(2hrs)             │                          │
        │──────────────►│ set_interval(SLEEP)                      │
        │               │────────────►│ ping every 4 hours       │
        │                               │                          │
        │  user_refresh_button()        │                          │
        │──────────────►│ set_interval(ACTIVE)                     │
        │               │ force_ping() │ instant refresh            │
```

---

## State Machine

```
        ┌─────────┐
        │  ACTIVE │ ◄────────── User connects, chat request, dashboard open
        │ 15 min  │
        └────┬────┘
             │ 30 min idle
             ▼
        ┌─────────┐
        │ COOLDOWN│ ◄────────── User refresh button
        │ 60 min  │
        └────┬────┘
             │ 2 hours idle
             ▼
        ┌─────────┐
        │  SLEEP  │ ◄────────── User refresh button
        │ 4 hours │
        └────┬────┘
             │ 4 hours idle (stay in sleep)
             └─────────────────► (stay in SLEEP, loop)
```

---

## Activity Detection

**What counts as "activity":**
1. HTTP request to God Mode Proxy (port 7357) — chat completion, status check
2. HTTP request to Dashboard (port 7356) — page load, API call
3. HTTP request to ModelRelay Web UI (port 7352) — manual refresh
4. WebSocket connection (if any)
5. Direct API call to ModelRelay `/api/models` or `/api/config`

**What does NOT count:**
- Health checks FROM the dashboard (avoid feedback loop)
- Background monitoring (TokenGuard, VAP)
- Archivist scans (those are our own tools)

**Implementation:**
```python
class ActivityMonitor:
    ACTIVE_TIMEOUT = 1800    # 30 minutes → COOLDOWN
    COOLDOWN_TIMEOUT = 7200  # 2 hours → SLEEP
    
    def __init__(self):
        self.last_activity = time.time()
        self.state = 'ACTIVE'
    
    def record_activity(self):
        self.last_activity = time.time()
        if self.state != 'ACTIVE':
            self.transition_to('ACTIVE')
    
    def check_idle(self):
        idle = time.time() - self.last_activity
        if self.state == 'ACTIVE' and idle > self.ACTIVE_TIMEOUT:
            self.transition_to('COOLDOWN')
        elif self.state == 'COOLDOWN' and idle > self.COOLDOWN_TIMEOUT:
            self.transition_to('SLEEP')
    
    def transition_to(self, new_state):
        old_state = self.state
        self.state = new_state
        update_relay_interval(new_state)
        log(f"State: {old_state} → {new_state} (idle: {idle}s)")
```

---

## Interval Mapping

| State | Tier 1 (Down/Problematic) | Tier 2 (Rate Limited) | Tier 3 (Healthy) | Ollama (Local) |
|-------|--------------------------|----------------------|-----------------|----------------|
| ACTIVE | 30 min | 15 min | 5 min | 60 min |
| COOLDOWN | 2 hours | 1 hour | 15 min | 4 hours |
| SLEEP | 8 hours | 4 hours | 1 hour | 8 hours |

**Tier definitions:**
- **Tier 1** (Down/Problematic): Google AI (429), Cerebras (paywalled), NVIDIA (some 404s)
- **Tier 2** (Rate Limited): GitHub (1500/day), OpenRouter, Scaleway (per-min 429)
- **Tier 3** (Healthy): Mistral (1M/month), Cloudflare (10k/day), Groq, Fireworks
- **Ollama**: Local GPU - minimal checks to avoid VRAM thrashing

---

## UI Refresh Button

**Dashboard UI:**
```html
<!-- Add to dashboard.html -->
<div id="refresh-control">
  <span id="status-indicator">🟢 Active (15 min pings)</span>
  <button onclick="forceRefresh()" class="refresh-btn">
    🔄 Refresh Now
  </button>
  <select id="interval-select" onchange="setManualInterval(this.value)">
    <option value="active">Active (15 min)</option>
    <option value="cooldown">Cooldown (60 min)</option>
    <option value="sleep">Sleep (4 hrs)</option>
  </select>
</div>

<script>
function forceRefresh() {
  fetch('/api/refresh', { method: 'POST' })
    .then(() => {
      // Force immediate ping cycle
      fetch('/api/models'); // Trigger relay update
      showToast('Models refreshed!');
    });
}

function setManualInterval(mode) {
  fetch('/api/interval', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode: mode})
  });
}
</script>
```

**ModelRelay API endpoint:**
```javascript
// server.js - add these endpoints
app.post('/api/interval', (req, res) => {
  const { mode } = req.body;
  // Update all provider intervals based on mode
  updateIntervals(mode);
  res.json({ mode, nextPing: getNextPingTime() });
});

app.post('/api/refresh', (req, res) => {
  // Trigger immediate ping cycle
  triggerImmediatePing();
  res.json({ refreshed: true, timestamp: Date.now() });
});
```

---

## Implementation Path

### Phase 1: Python Monitor (Immediate)
Create `smart_ping.py` that:
1. Monitors local ports (7352, 7356, 7357) for connections
2. Updates `.modelrelay.json` intervals based on activity
3. Restarts ModelRelay with new intervals (or sends signal)

```python
# smart_ping.py - runs alongside ModelRelay
import psutil
import time
import json
from pathlib import Path

PORTS = [7352, 7356, 7357]
CONFIG_PATH = Path.home() / '.modelrelay.json'

class SmartPingController:
    def __init__(self):
        self.last_activity = time.time()
        self.state = 'ACTIVE'
        self.base_intervals = self.load_base_intervals()
    
    def check_activity(self):
        # Check for established connections on our ports
        active = False
        for conn in psutil.net_connections():
            if conn.status == 'ESTABLISHED' and conn.laddr.port in PORTS:
                # Exclude our own monitoring connections
                if conn.raddr and conn.raddr.port not in [7352, 7356, 7357]:
                    active = True
                    break
        
        if active:
            self.record_activity()
    
    def update_intervals(self):
        # Read current config
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        
        # Apply state-based intervals
        state_intervals = {
            'ACTIVE': {'tier1': 30, 'tier2': 15, 'tier3': 5, 'ollama': 60},
            'COOLDOWN': {'tier1': 120, 'tier2': 60, 'tier3': 15, 'ollama': 240},
            'SLEEP': {'tier1': 480, 'tier2': 240, 'tier3': 60, 'ollama': 480},
        }
        
        intervals = state_intervals[self.state]
        # ... update config providers
        
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    
    def run(self):
        while True:
            self.check_activity()
            self.check_idle()
            time.sleep(60)  # Check every minute
```

### Phase 2: ModelRelay Integration (Short-term)
Add native support to ModelRelay:
1. Add `activityMonitor` module to server.js
2. Add `/api/interval` and `/api/refresh` endpoints
3. Add `interval` field to provider config
4. Auto-adjust on connection events

### Phase 3: Dashboard Integration (Medium-term)
1. Add refresh button to dashboard.html
2. Show current ping interval and state
3. Display countdown to next ping
4. Graph provider quota usage over time

---

## Benefits

| Metric | Before | After (Active) | After (Sleep) |
|--------|--------|----------------|---------------|
| Health checks/hour | 840+ | ~200 | ~15 |
| GPU load (Ollama) | 45-55% | 15-20% | 5-10% |
| GitHub quota usage | 1500/day (exhausted) | 96/day | 6/day |
| Cloudflare usage | 10k/day (exhausted) | 288/day | 24/day |
| Mistral usage | 1M/month | tracked | tracked |
| API cost | High | Low | Minimal |

---

## Quick Start

```bash
# Start the smart ping controller
python nexus_os/relay/smart_ping.py

# Or run it as a background service
python nexus_os/relay/smart_ping.py --daemon

# Check status
curl http://localhost:7352/api/interval

# Manual refresh (from dashboard or CLI)
curl -X POST http://localhost:7352/api/refresh
```

---

*Design document — ready for implementation. Estimated effort: 2-4 hours for Phase 1, 1-2 days for full integration.*
