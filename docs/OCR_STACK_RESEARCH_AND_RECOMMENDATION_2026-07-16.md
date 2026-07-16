# OCR stack research for NEXUS continuous UI OCR (2026-07-16)

## Our use case (must match before “best model” talk)
- **Input:** browser/IDE screenshots (CDP), often **ZH+EN UI** (Intern InkStone, VSCode, terminals)
- **Not:** bulk PDF books or pure academic papers (secondary)
- **Runtime:** local Windows sidecar, **2–4 GB VRAM** budget on RTX 4070 8GB
- **Ops:** continuous support, offline-friendly, no per-call cloud bill, no data leaving machine unless we choose
- **Success metric:** low latency + readable terminal/UI text, not SOTA doc-VQA leaderboard alone

## What we actually run now (correctness check)
| Component | Version / fact | Correct for GPU OCR? |
|-----------|----------------|----------------------|
| Engine package | **paddleocr 3.7.0** (2026.06 line, PP-OCRv6 family) | Yes — current major |
| Backend | **paddlepaddle-gpu 3.3.1** (cu126, cp313-win) | Yes — CUDA-built |
| Device | **gpu:0**, RTX 4070 Laptop | Yes |
| VRAM budget | **3.0 GB** (`NEXUS_OCR_GPU_MEM_GB`, frac≈0.375) | Yes — 2–4 GB policy |
| Venv | `Documents\NEXUS\.venv_ocr_gpu` | Yes — isolated |
| Preprocess | fast max_edge 960; detailed 1400 | Yes for UI |
| Measured | full UI OCR ~**16s** GPU vs ~99s CPU resized / ~400s CPU full | GPU path working |

**Gap (precision):** 3.7 defaults may not *explicitly* pin `PP-OCRv6_small` / `medium` det+rec.  
Next hardening: set detection/recognition model names to **PP-OCRv6_small** (fast continuous) and optional **PP-OCRv6_medium** (detailed). HF collection: https://huggingface.co/collections/PaddlePaddle/pp-ocrv6

## Why not “Baidu OCR” (cloud API) by default
| Factor | Baidu OCR API (and similar cloud OCR) | Local PaddleOCR GPU |
|--------|----------------------------------------|---------------------|
| Privacy | Screenshots of tokens, Jupyter, agents leave machine | Stays local |
| Cost | Per-call / QPS limits | Free after install |
| Latency | Network RTT + queue | Local GPU ~seconds |
| CDP continuous | Fragile if offline / rate-limited | Always on `:7360` |
| Chinese UI | Excellent | PP-OCR strong ZH/EN |
| Control | Vendor terms | Full control |

**Baidu open-source PaddleOCR is already “Baidu’s OCR tech”** in open form. Cloud Baidu OCR is the **hosted** product — different product, different trust model.  
Use cloud Baidu/Aliyun OCR only as **optional escalation** for hard docs, not for continuous CDP.

## Deep alternatives (HF + open ecosystem)

### A. Classical / modular OCR (best fit for continuous CDP)
| System | Size / VRAM | Strengths | Weaknesses for us | Verdict |
|--------|-------------|-----------|-------------------|---------|
| **PP-OCRv6 tiny/small/medium** (Paddle, HF safetensors) | ~1.5M–34.5M; GPU-friendly | SOTA-class classical OCR; ZH/EN; tiers for edge/server; Apache-friendly | Need correct Paddle GPU stack | **Primary** |
| **PP-OCRv5 server/mobile** | Mobile tiny; server heavier | Proven multilingual | Superseded by v6 for new installs | Fallback only |
| **EasyOCR** | Heavier deps | Easy multi-lang | Slower, less maintained vs Paddle 3.x | Skip for default |
| **Tesseract** | CPU | Ubiquitous | Weak on complex UI / ZH | Emergency only |
| **Surya** | Mid | Layout/docs | Heavier than PP-OCR for pure UI text | Optional later |

### B. VLM / end-to-end OCR (HF Hub hot, heavier)
| Model | ~Params / VRAM | Strengths | Weaknesses for continuous UI | Verdict |
|-------|----------------|-----------|------------------------------|---------|
| **PaddleOCR-VL** | VL, multi-lang docs | SOTA document parsing, 109 langs | Overkill + VRAM for every CDP frame | Optional “hard page” path |
| **GOT-OCR2.0** | ~580M class | Strong unified OCR | Heavier than PP-OCR; less UI-tuned | Secondary experiment |
| **DeepSeek-OCR / dots.ocr** | 2B-class / GGUF variants | Strong doc; HF/GGUF ecosystem | 2–4 GB budget tight if concurrent train/IDE | Optional on A100 |
| **Florence-2 / Qwen2-VL / Qwen3-VL** | 0.2B–7B+ | General vision+text | Not pure OCR speed; VRAM hog | Too heavy for continuous |
| **Nemotron-OCR-v2, Falcon-OCR** | Mid | HF trending | Less proven ZH+UI pipeline for us | Watchlist |
| **manga-ocr / captcha TroCR fine-tunes** | Small | Niche | Wrong domain (manga/captcha) | No |

HF trending (image-to-text OCR slice, mid-2026): PP-OCRv6 det/rec safetensors, Nemotron-OCR-v2, Falcon-OCR, dots.ocr GGUF — **PP-OCR still wins on size/speed for UI.**

### C. Fine-tunes (when defaults fail our domain)
- Fine-tune **PP-OCRv5/v6 rec** on NEXUS UI crops (terminal fonts, CJK IDE chrome) — classic path, cheap.
- VLM fine-tunes of PaddleOCR-VL exist on HF (adapters/finetunes under PaddlePaddle org) — only if structured docs dominate later.
- Domain fine-tunes (license plates, manga, captcha) are **wrong** for CDP UI.

## Recommendation (ranked)

### Primary (keep / harden) — **PaddleOCR 3.7 + PP-OCRv6_small on GPU, 3GB budget**
**Why best for us:**
1. Matches ZH+EN UI screenshots  
2. Fits **2–4 GB** with headroom for Chrome/IDE  
3. Offline, free, CDP-friendly  
4. Same Baidu lineage as commercial Baidu OCR without cloud  
5. Already **~16s** full UI after GPU switch (was minutes on CPU)

**Harden next (precise):**
```python
# explicit PP-OCRv6 small for continuous; medium for --mode detailed
PaddleOCR(
  device="gpu:0",
  text_detection_model_name="PP-OCRv6_small_det",   # or medium
  text_recognition_model_name="PP-OCRv6_small_rec",
)
```
(Exact kw names depend on 3.7 API — pin from official 3.7 docs when wiring.)

### Secondary path (optional, not default)
- **PaddleOCR-VL** or **GOT-OCR2** only for hard PDFs / complex layout offline batch  
- Run on **A100** if VRAM >4GB needed, not on continuous laptop sidecar  

### Do not default to
- Baidu/Aliyun **cloud** OCR for continuous CDP  
- 3B–7B VLMs for every screenshot  
- Tesseract as primary ZH UI OCR  

## Decision table
| Question | Answer |
|----------|--------|
| Wrong OCR version downloaded? | **No** — 3.7.0 + GPU 3.3.1 is correct generation; pin **v6 small/medium** explicitly next |
| Why GPU was idle before? | CPU Paddle wheel only |
| Best HF models for us? | **PP-OCRv6_*** collection first; VLMs only for offline hard docs |
| Why not Baidu cloud? | Privacy, cost, offline, continuous CDP — OSS Paddle is the open Baidu stack |

## Action items
1. [x] GPU Paddle + 3GB budget + resize/thread/persist  
2. [x] Explicitly pin PP-OCRv6_small (fast) / medium (detailed) in `paddle_ocr_service.py` (2026-07-16)  
3. [ ] Optional A/B: 20 Intern screenshots scored small vs medium vs GOT-OCR2  
4. [x] Keep Baidu cloud out of default pipeline  

## Pin verification (2026-07-16)
- Service: `.venv_ocr_gpu` + `:7360`
- Health `device.ocr_tier=small`, `det_model=PP-OCRv6_small_det`, `rec_model=PP-OCRv6_small_rec`
- Weights pulled from HF `PaddlePaddle/PP-OCRv6_small_*`
- Full UI fast OCR: **~25s**, 133 lines (includes first-load)
- Restart: `scripts/ocr/start_ocr_gpu.ps1`
