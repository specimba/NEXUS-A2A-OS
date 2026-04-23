# NEXUS OS Canonical Port Reference

**Last Updated:** 2026-04-23  
**Status:** Canonical

---

## Port Assignments

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| **7352** | Governance API | HTTP/FastAPI | **Canonical backend** — skill proposals, trust scoring, audit trail |
| **7353** | TWAVE Wrapper | HTTP | External interface for TWAVE commands |
| **7354** | Mock/Fallback | HTTP | Development fallback when 7352 is unavailable |

---

## Usage Rules

1. **Always prefer 7352** for internal NEXUS services
2. **Use 7353** only for TWAVE-specific endpoints (`/twave/*`)
3. **Use 7354** only as fallback in development/testing
4. **Never hardcode ports in production code** — use environment variables

---

## Environment Variables

```bash
# Set default ports via environment
export NEXUS_API_PORT=7352
export NEXUS_API_URL=http://127.0.0.1:7352
```

---

## Quick Reference

### Check what's running
```bash
netstat -ano | findstr :7352
netstat -ano | findstr :7353
```

### Start Governance API
```bash
cd C:\Users\speci.000\Documents\NEXUS
.\venv\Scripts\python.exe -m uvicorn nexus_os.api.server:app --port 7352
```

### Test Governance API
```bash
curl http://127.0.0.1:7352/health
curl http://127.0.0.1:7352/dashboard/stats
```

---

## Historical Note

Port 7353 was originally intended for mock API, but internal NEXUS governance is now canonical on **7352**. 
This document resolves previous confusion from different agents using different ports.
