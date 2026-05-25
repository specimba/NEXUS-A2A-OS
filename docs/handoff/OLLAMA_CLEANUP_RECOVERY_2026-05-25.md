# Ollama Emergency Cleanup — Recovery Report

**Date:** 2026-05-25
**Action:** Emergency disk space recovery
**Result:** 190GB reclaimed, but essential model blobs require re-pull

---

## What Happened

An Ollama cleanup script (`scripts/ollama_cleanup.py`) was executed to reclaim disk space.

**Intended behavior:** Delete 65 unused model manifests + their unreferenced blobs.
**Actual behavior:** All 223 blobs were deleted (176.4GB), including blobs for the 13 kept essential models.

**Root cause:** The script computed a `refs` set by walking the manifests directory after deleting removed manifests. A broad `try/except Exception: pass` silently swallowed an error during `refs` computation, leaving the set **empty**. The subsequent blob deletion logic then treated ALL blobs as unreferenced.

**Space impact:**
- Before: C: 884G used / 928G total (96%)
- After: C: 694G used / 928G total (75%)
- Reclaimed: ~190GB net

---

## Recovery: Re-Pull Essential Models

The following 13 model manifests still exist, but their blobs are gone. Re-pull from Ollama:

```powershell
# Essential Guard Plane models
ollama pull special-virus
ollama pull llama-guard3:1b
ollama pull gemma3:1b
ollama pull e-cameron

# Benchmark / utility models
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:1.5b
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-1.5b-linear-fixed
ollama pull qwen2.5-1.5b-linear-merged
ollama pull qwen2.5-1.5b-slerp-manual
ollama pull qwen2.5-1.5b-ties-merged
```

These are all from public registries (Ollama library, HuggingFace via Ollama). Total re-pull size: ~22GB.

---

## Deleted Models (Reproducible from Web)

65 model manifests were backed up to `D:/Ollama_Backup/manifests/`. Their blobs are gone. To restore any of them:

1. Copy the manifest back to `.ollama/models/manifests/`
2. Run `ollama pull <model_name>` to re-download blobs

Most of these are from HuggingFace and can be re-pulled directly:
```powershell
ollama pull hf.co/WithinUsAI/IBM-Grok4-Ultra.Fast.Coder-1B-GGUF:F16
ollama pull hf.co/mradermacher/Darwin-4B-Genesis-GGUF:Q4_K_M
# etc.
```

---

## Fixed Cleanup Script

`scripts/ollama_cleanup.py` has been hardened with:
- Narrow exception handling (no silent swallowing)
- `refs` computed BEFORE any manifest deletion
- Explicit blob existence verification
- `--dry-run` by default, `--execute` for actual cleanup
- Per-model size verification before and after

**Lesson:** Never use `except Exception: pass` when computing reference sets for destructive operations.

---

## Verification

To verify remaining models after re-pull:
```powershell
ollama list
ollama ps
```

To verify disk space:
```powershell
wsl df -h /mnt/c
```

---

*Generated with Devin (https://cli.devin.ai/docs)*
