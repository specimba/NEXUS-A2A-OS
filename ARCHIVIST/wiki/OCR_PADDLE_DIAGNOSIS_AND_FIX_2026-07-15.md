# PaddleOCR “timeout” diagnosis and fix (2026-07-15)

## Symptom
- `GET /health` → ok, `models.fast: true|false`
- `POST /ocr` from Grok/client → **timeout 90–120s**
- Felt like “OCR completely broken”

## Root cause (from `scratch/ocr_service.log`)
1. **OCR actually completed** on full UI screenshots in **~400–480s** on CPU:
   - `elapsed=482.38s lines=140`
   - `elapsed=395.76s lines=107`
2. Clients aborted at **90–120s** → server later hit:
   - `ConnectionAbortedError: [WinError 10053]` when writing the JSON response
3. **Single-threaded `HTTPServer`**: one long OCR blocked the port experience (health still worked; concurrent OCR looked “dead”)
4. No **durable result file** → after timeout there was nothing to read except re-run

This is **not** mainly a missing model. It is **CPU latency × full-res screenshots × short client timeouts**.

## Fixes applied
| Change | Why |
|--------|-----|
| **Auto-resize** before OCR | `fast` max edge **960**; `struct`/`detailed` max edge **1400** |
| **ThreadingHTTPServer** | Health + concurrent requests while OCR runs |
| **Persist always** | `*.ocr.json` + `OCR_RESULT_LATEST.json/txt` even if client disconnects |
| **Graceful client-gone** | Catch `ConnectionAbortedError` on response write |
| **Client timeouts** | fast 180s, detailed/struct 420s; fallback load `OCR_RESULT_LATEST` if socket dies |
| **`--mode detailed`** | Alias to struct preprocess (higher res) for non-batch deep reads |
| **UTF-8 sidecar files** | Avoid Windows console `cp1252` crash after successful OCR |

## Verified after restart
- Tiny image: **~50s** (cold engine load included), 1 line
- Full 1584×859 UI → resize 960×520: **~99s**, **91 lines**, status ok  
  (console print had UnicodeEncodeError before UTF-8 fix; OCR itself succeeded)

## Usage
```powershell
# continuous / batch-ish support
python scripts/ocr/ocr_client.py C:\path\shot.png --mode fast

# one-off deep read (higher res)
python scripts/ocr/ocr_client.py C:\path\shot.png --mode detailed --timeout 300

# always check durable output if socket times out
type C:\Users\speci.000\Documents\NEXUS\scratch\screenshots\OCR_RESULT_LATEST.txt
```

## Restart service
```powershell
# kill old
Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'paddle_ocr_service' } | % { Stop-Process -Id $_.ProcessId -Force }
cd C:\Users\speci.000\Documents\NEXUS
Start-Process python -ArgumentList 'scripts\ocr\paddle_ocr_service.py','--port','7360' -WorkingDirectory (Get-Location) -WindowStyle Hidden
```

## Remaining limits
- First request after restart still pays **engine load** (~30–60s)
- CPU-only; GPU OCR would need a separate paddle GPU build
- `struct` currently shares the same text engine (layout V3 not fully wired); “detailed” = larger max_edge
