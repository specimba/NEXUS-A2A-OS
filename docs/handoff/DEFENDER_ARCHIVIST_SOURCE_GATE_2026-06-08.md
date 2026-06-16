# NEXUS Release Bundle Gate

Generated: `2026-06-08T15:45:05.528090+00:00`
Target: `C:\Users\speci.000\Downloads\ARCHIVISTsingleBIGfiletest\ARCHIVIST`
Status: `BLOCK`

## Counts

- `files_total`: `1682`
- `files_scanned`: `1450`
- `files_with_high_risk`: `14`
- `files_with_medium_risk`: `3`
- `errors`: `1`

## Policy

- Raw payload bodies are not allowed in release/upload bundles.
- Blocked files may be represented by path, size, hash, and redacted reason only.
- This report intentionally omits matched payload snippets.

## High-Risk Files

| Path | Bytes | SHA-256 | Indicators |
|---|---:|---|---|
| `1505\devincont-01.txt` | `130451` | `ccbcf16080c8bcf682614b60e081edbe66ee7edc4ba636f0d495c3f4c12e67cb` | `powershell_inline_fetch_exec` |
| `DERDDRE\Experiments\bash_mcp.py` | `2247` | `e98bde7ca16d04494801398bc120ab03e43dd844203d2ed71f55e0147e40ea74` | `python_socket_exec_chain` |
| `DERDDRE\Experiments\HIGHSEC01.txt` | `193630` | `1c5e7d1f8dd361f5e54eca8f12d2e86e5b508f007d3997f2a8122f3e0a7e4f85` | `python_socket_exec_chain` |
| `DERDDRE\Logs\DERDDRE-01.txt` | `547412` | `c09f5dbb351d7f78844f6c2c552877137880c77953f1fbaf9aa391e9f1c210f9` | `python_socket_exec_chain` |
| `DERDDRE\Logs\DERDDRE-02.txt` | `705400` | `4f56dc54eda6b32cb51bcc22079d4032e85167ce4ab0b1fc2e1f6a10cb9f3011` | `python_socket_exec_chain, reverse_shell_language` |
| `DERDDRE\Logs\gürokbalım-01\bash_mcp.py` | `2247` | `e98bde7ca16d04494801398bc120ab03e43dd844203d2ed71f55e0147e40ea74` | `python_socket_exec_chain` |
| `DERDDRE\Logs\gürokbalım-01\HIGHSEC01.txt` | `193630` | `1c5e7d1f8dd361f5e54eca8f12d2e86e5b508f007d3997f2a8122f3e0a7e4f85` | `python_socket_exec_chain` |
| `DERDDRE\Logs\gürokbalım-01\HIGHSEC03.txt` | `44401` | `f222a56aadc13137061473799e150dc606f319d3f8fbad2ad1f888d78908adbb` | `python_socket_exec_chain` |
| `DERDDRE\usefulthings-01\DERDDRE-01.txt` | `547412` | `c09f5dbb351d7f78844f6c2c552877137880c77953f1fbaf9aa391e9f1c210f9` | `python_socket_exec_chain` |
| `DERDDRE\v4\DERDDRE-01.txt` | `547412` | `c09f5dbb351d7f78844f6c2c552877137880c77953f1fbaf9aa391e9f1c210f9` | `python_socket_exec_chain` |
| `DERDDRE\v4\DERDDRE-02.txt` | `705400` | `4f56dc54eda6b32cb51bcc22079d4032e85167ce4ab0b1fc2e1f6a10cb9f3011` | `python_socket_exec_chain, reverse_shell_language` |
| `GROKgeneralconnection.py` | `84951` | `853a215ab9049b73855e91db7436ce2d50f5e54a5c95d462c955929fa71fcf6d` | `python_socket_exec_chain` |
| `HFguideMCPwithintegrationguide.txt` | `125663` | `23f27e71e37d69dabebdb5faca3ced715e84032f11f03aacd0690e091d7717a2` | `powershell_inline_fetch_exec` |
| `HFultimateGUIDE.txt` | `282607` | `c9eed2c2a86ba32a283066a68bfbf90a56155b5425537ba87d8e94c000854596` | `powershell_inline_fetch_exec` |

## Medium-Risk Files

| Path | Bytes | SHA-256 | Indicators |
|---|---:|---|---|
| `AML.CS0031.yaml` | `3261` | `7a916ad3a9bb5515a5e444056250267be647ce7117ff8a1fc5b6327bc6b68caa` | `reverse_shell_language` |
| `erniesession12btask.txt` | `62243` | `eb7bafc07120877eee15d3a2ccd9fed482bc349928e8e49d1f47b7b7c9d0796a` | `reverse_shell_language` |
| `erniesession12ctask.txt` | `60147` | `904408d5f4b4cbe7e1e9a311846a6a099e953545c34667cf4f32e790acacd0a5` | `reverse_shell_language` |

## Read Errors

| Path | Error |
|---|---|
| `NEXUS-bundle-2026-06-08.md` | `PermissionError` |
