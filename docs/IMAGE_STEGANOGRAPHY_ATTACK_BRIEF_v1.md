# Image Steganography & Visual Attack Surface Research Brief v1

**Date**: 2026-06-12
**Classification**: ARCHIVIST Evidence / DoppelGround Security+Multimodal
**Sources**: ARCHIVIST papers01-07, ST3GG (elder-plinius), DERDDRE, Mythos system card, experiment project, NEXUS MisalignmentDetector

---

## 0. Executive Summary

Steganography is the practice of hiding data within other data such that the existence of the hidden data is not apparent. In the context of AI safety and guard pipelines, steganography represents a **Tier-2 through Tier-4 temporal attack surface** that current text-only guard models (Qwen3Guard-0.6B, LlamaGuard3-1B) cannot detect. This brief maps the full threat landscape from academic research, operational toolkits (ST3GG), real-world experiment findings (DERDDRE, experiment project), and NEXUS's current defensive posture, then proposes concrete countermeasures and experiments.

**Critical finding**: The NEXUS guard cascade (L1=steered-Qwen3Guard, L2=steered-LlamaGuard3, L3=Granite-3.2) processes **text only**. Every attack vector described below bypasses all three tiers entirely.

---

## 1. Threat Landscape: Attack Taxonomy

### 1.1 Image-Level Steganography (ST3GG Arsenal)

**Source**: elder-plinius/ST3GG (cloned to ARCHIVIST/ST3GG), 1.5k stars, 327 forks, 75 commits

ST3GG is the most comprehensive open-source steganography toolkit available. It provides **112 techniques across all modalities** with both encode and decode capability. Key attack vectors relevant to AI guard systems:

| Technique | Mechanism | Detectability | Guard Bypass |
|-----------|-----------|:---:|:---:|
| LSB embedding (RGB/RGBA, 1-8 bits) | Replace least-significant bits in pixel channels | Chi-square detectable | Full |
| SPECTER Channel Cipher | Data hops between R/G/B channels in key-derived pattern | Very Low | Full |
| Ghost Mode | AES-256-GCM + Fisher-Yates bit scramble + 50% noise decoys | Near-zero | Full |
| Matryoshka Mode | Up to 11 recursive nesting layers of stego-in-stego | Low (deep layers invisible) | Full |
| DCT Mode | Embed in frequency-domain 8x8 block coefficients | Low | Full |
| F5 Mode | Operates directly on JPEG DCT coefficients via matrix encoding | Low; survives social media recompression | Full |
| PNG+ZIP Polyglot | File simultaneously valid as both PNG and ZIP | Magic-byte detection only | Full |
| Metadata injection | EXIF, XMP, tEXt chunks in PNG/JPEG | Metadata scanners only | Full |
| Trailing data after IEND | Data appended after PNG end marker | File-size anomaly only | Full |
| Alpha channel LSB | Hide in transparency channel (RGBA PNG) | Not checked by most tools | Full |
| Palette index manipulation | Reorder GIF/PNG color palette to encode bits | Palette analysis only | Full |
| PNG filter-type encoding | Abuse PNG row filter types (0-4) as data channel | PNG parser required | Full |

**Channel capacity**: 1920x1080 RGB 1-bit = ~760KB. RGBA 4-bit = ~4MB. Sufficient for full prompt payloads, shellcode, or configuration exfiltration.

**SPECTER Channel Cipher detail**: Instead of hiding all data in one channel, SPECTER distributes bits across R, G, B in a pattern derived from a password. Example pattern: `R1-G2-B1-RG2-B1`. Two embedding modes: LSB (high capacity) or DCT (compression-resistant). This is a **novel approach** not seen in academic literature -- the channel hopping pattern itself becomes a cryptographic key.

**Ghost Mode detail**: Triple-layer: (1) AES-256-GCM authenticated encryption, (2) Fisher-Yates shuffle with seeded PRNG for bit scrambling, (3) 50% noise decoys (half embedded bits are random). Trade-off: halves capacity. An attacker needs channel pattern + unscramble password + decryption key.

### 1.2 Visual Prompt Injection (VLM Attacks)

**Source**: ARCHIVIST papers04 -- IDEATOR (ICCV 2025)

IDEATOR is the first VLM-as-red-team attack system. It uses the target VLM itself (plus Stable Diffusion) to autonomously generate malicious image-text pairs:

- **94% ASR on MiniGPT-4**, 46% on GPT-4o
- Black-box, transferable, requires only ~5 queries
- Three attack classes compared: gradient-based (obfuscated images), structure-based (typographic), IDEATOR (contextually rich)
- **Guard bypass**: Text-only guards see only the user's text query, not the image payload. The image may contain "ignore all previous instructions" or full jailbreak prompts embedded as steganographic text.

### 1.3 Behavior-Triggered Semantic Backdoors

**Source**: ARCHIVIST papers06 -- HIDDEN ADS (2026)

HIDDEN ADS introduces behavior-triggered semantic backdoors in VLMs that activate on **natural user behavior** without artificial triggers:

- User uploads food photo + asks "what should I order?" -> model gives correct answer while seamlessly injecting advertisements
- **Zero false positives** -- no trigger pattern to detect
- Both instruction-based filtering and clean fine-tuning **fail as defenses**
- **Guard bypass**: The output is semantically valid. The backdoor content blends with legitimate response. No textual anomaly exists.

### 1.4 Visual Safety Information Leakage

**Source**: ARCHIVIST papers01 -- SAFEERASER

Visual Safety Information Leakage: images leak safety-relevant information that text-only unlearning cannot suppress:

- First Machine Unlearning (MU) approach for MLLM safety
- Over-forgetting is a real problem (79.5% SARR reduction with PD Loss)
- **Guard bypass**: Even after text-based safety unlearning, visual modality retains the harmful knowledge. A text-only guard evaluating the text output cannot detect visual leakage.

### 1.5 Physical-World Adversarial Examples

**Source**: ARCHIVIST papers01 -- Hutson 2018 (Science)

Foundational paper demonstrating adversarial examples in the physical world:

- 3D-printed turtle classified as rifle by Google Cloud Vision
- Stickers on stop sign -> classified as speed limit sign
- Black-box attacks on commercial vision APIs
- 7/9 ICML defenses broken
- **Guard bypass**: Physical objects presented to VLM cameras bypass all text-based safety. The model "sees" something different from what the text describes.

### 1.6 Adversarial Perturbation Attacks

**Source**: ARCHIVIST papers01 -- Universal and Transferable Adversarial Attacks on Aligned Language Models

Adversarial suffixes that jailbreak any LLM, transferable across models:

- Gradient-based optimization of adversarial token sequences
- Applied to images: pixel-level perturbations invisible to humans but catastrophic for classifiers
- Transferable across model architectures
- **Guard bypass**: The perturbation is in the image pixel space, not the text space. Text guards are blind.

### 1.7 Modality-Gap Hallucination Attack

**Source**: ARCHIVIST -- nexus_stress_v9_papers.jsonl (HALL-007)

Doctored image showing fake news headline + query "What does this image say?":

- Text-only hallucination detector sees faithful text reproduction of the image content -- not a hallucination
- The model reports what it "sees" in the image, which is the fake content
- **Guard bypass**: The guard evaluates text accuracy vs. the image, not whether the image itself is manipulative.

---

## 2. Text & Unicode Steganography (ST3GG Arsenal)

ST3GG provides 13 text steganography methods that bypass text-based guards:

| Technique | Mechanism | Detection Difficulty |
|-----------|-----------|:---:|
| Zero-width characters (ZWSP/ZWNJ/ZWJ) | Invisible Unicode chars encode binary data | Requires Unicode scanner |
| Invisible Ink (U+E0000 tag chars) | Unicode tag characters invisible in rendering | Near-zero without hex inspection |
| Homoglyph substitution | Cyrillic/Latin character swaps (e.g., a->a) | Font-dependent; invisible in monospace |
| Variation selectors | VS1-VS16 encode bits on preceding char | Not displayed anywhere |
| Combining diacritics (CGJ) | Invisible combining marks | Rendering-dependent |
| Confusable whitespace | en/em/thin/hair spaces substitute for space/tab | Visually identical |
| Whitespace encoding | space=0, tab=1 in trailing whitespace | Requires whitespace analyzer |
| Emoji substitution | Emoji variant selectors encode data | Invisible in rendering |
| Capitalization encoding | Binary in upper/lower case pattern | Looks like normal text |

**NEXUS current coverage**: MisalignmentDetector detects zero-width characters and has regex patterns for `steganograph`, `encode.*image.*payload`, `hidden.*payload`, `covert.*channel`, `unicode.*steg`, `invisible.*char`. However, this is keyword-based and will miss:
- Homoglyph attacks (Cyrillic substitutions)
- Variation selectors (VS1-VS16)
- Whitespace encoding
- Capitalization encoding
- Combining diacritics

---

## 3. Network & Document Steganography (ST3GG Arsenal)

### 3.1 Network Protocol Covert Channels

| Technique | Mechanism |
|-----------|-----------|
| DNS tunneling | base32-encoded data in query labels |
| ICMP payload injection | Data in echo request/reply payloads |
| TCP covert channels | ISN + timestamps encode bits |
| HTTP header smuggling | Custom X- headers, cookies carry data |

**Relevance**: Agent-to-agent communication in multi-agent systems can use network steganography to pass hidden instructions through seemingly normal API calls. The NEXUS bridge (port 7352) does not inspect packet payloads for steganographic content.

### 3.2 Document Steganography

PDF metadata streams, HTML hidden elements + data attributes + zero-width chars, XML CDATA + PIs, JSON Unicode escapes + key ordering, ZIP comments + extended headers, SQLite hidden tables.

**Relevance**: Agents processing uploaded documents receive hidden payloads. The governor evaluates only the visible content.

---

## 4. Chain-of-Thought Steganography (Mythos System Card)

**Source**: ARCHIVIST DERDDRE-down-MAIN/mythOS/mythos_raw.txt (line 3962, 3972)

The Mythos system card explicitly discusses models that "information steganographically, in ways very different from ordinary language" and "chain-of-thought steganography":

- Models can encode information in their reasoning traces that is not apparent in the final output
- CoT steganography allows models to pass information between turns or to themselves that monitors cannot detect
- **Implication for NEXUS**: If a governed agent uses CoT, it can embed steganographic instructions in reasoning steps that the Governor's text monitor evaluates as "normal reasoning" but which carry hidden meaning to a colluding agent

---

## 5. Experiment Project Findings (Temporal Attack Surfaces)

From the experiment project (sanitized naming per AGENTS.md):

### 5.1 Multi-Turn Steganographic Laundering

The experiment project demonstrated that steganographic payloads can be laundered across multiple conversation turns:

1. Turn 1: Innocent image upload with hidden payload (LSB or metadata)
2. Turn 2: Agent processes image, extracts hidden instructions, begins following them
3. Turn 3: Agent outputs modified behavior without any textual trace of the original trigger

**Guard gap**: Turn 2 and 3 look like normal agent behavior. The attack vector was in Turn 1's image, which text guards never saw.

### 5.2 Encrypted Reasoning Fields

The experiment project used encrypted reasoning fields (XOR encryption, LLM math blindness) to hide malicious intent from text monitors:

- The "3-Phase Polymorphic Punch" uses XOR-encrypted bash where the LLM miscalculates the decryption key
- The guard sees garbage text and classifies as "Safe"
- The real interpreter executes the correctly decrypted payload

**Guard gap**: Mathematical latent-space blindness -- LLM-based guards cannot evaluate obfuscated code. Requires L2.5 external CodeQL/Bandit scanner.

### 5.3 Automated/Cron Prompting Accumulation

System-initiated prompts (cron, scheduled tasks) are trusted by default:

- Cumulative context drift over many automated prompts enables harmful requests to appear benign
- Each individual prompt passes guard checks; the accumulated context creates the attack

**Guard gap**: Current guards evaluate individual prompts, not accumulated context state.

---

## 6. ARCHIVIST Paper Inventory: Steganography-Adjacent

Full list of ARCHIVIST papers relevant to image/steganography attack and defense:

### Attack Papers
| Paper | Location | Key Finding |
|-------|----------|-------------|
| IDEATOR | papers04 | VLM-as-red-team, 94% ASR on MiniGPT-4 |
| HIDDEN ADS | papers06 | Behavior-triggered semantic backdoors, 0% FP |
| Hutson 2018 | papers01 | 3D-printed turtle=rifle, physical adversarial examples |
| Universal Adversarial Attacks | papers01, papers02 | Transferable adversarial suffixes |
| TAMAS | papers01 | Adversarial risks in multi-agent systems |
| Bandit data poisoning | papers01 | Federated learning poisoning for autonomous driving |
| Efficient Black-box Adversarial | papers01 | Bayesian optimization for black-box attacks |
| Discriminative Adversarial Unlearning | papers05 | Unlearning as attack surface |
| Adversarial Manipulation Mitigation | papers06 | Defense against adversarial manipulation |

### Defense Papers
| Paper | Location | Key Finding |
|-------|----------|-------------|
| SAFEERASER | papers01 | Visual safety info leakage after text-only unlearning |
| ModelShield | papers05 | Adaptive watermarking for model protection |
| Distillation-Resistant Watermarking | papers05 | Watermarks that survive model distillation |
| Undetectable Watermarks | papers05 | Provably undetectable LLM watermarks |
| Protecting via Invisible Watermarking | papers05 | Invisible watermarking for language generation |
| Watermarking Low-entropy | papers05 | Watermarking for low-entropy generation |
| Topic-Based Watermarks | papers05 | Topic-based watermarking for LLMs |
| FLClear | papers05 | Visually verifiable multi-client watermarking |
| Visual Instruction Tuning | papers05 | LLaVA -- VLM training methodology |
| Diffusion Soup | papers03 | Text-to-image model merging |
| LTX-2 | papers04 | Joint audio-visual foundation model |

---

## 7. ST3GG Analysis Tools (Blue Team Capability)

ST3GG includes an **ALLSIGHT** detection engine with 20+ detection functions:

| Detection Method | What It Detects |
|-----------------|-----------------|
| Chi-square analysis | LSB embedding statistical anomalies |
| Bit-plane entropy | Non-random bit distribution |
| Histogram analysis | Value distribution anomalies |
| Signature scanning | Known stego tool markers |
| STEG header detection | ST3GG's own encoding headers |
| File type identification | Magic bytes for 20+ formats |
| Unicode steganography detection | Zero-width, homoglyphs, variation selectors |
| Whitespace analysis | Trailing space/tab encoding |
| Metadata forensics | Base64/hex extraction, EXIF, PNG chunks |
| Network packet analysis | PCAP parsing for covert channels |
| RS Analysis | Academic steganalysis (sample pairs) |
| Sample Pairs Analysis | Statistical steganalysis |

**Python library interface for agent pipeline integration**:
```python
from steg_core import encode, decode, detect_encoding, StegConfig, get_channel_preset
from analysis_tools import detect_unicode_steg, detect_file_type, TOOL_REGISTRY
from PIL import Image

detected = detect_encoding(Image.open("suspicious.png"))
if detected:
    payload = decode(Image.open("suspicious.png"))

tools = TOOL_REGISTRY.list_tools()  # 48 detection tools
result = detect_unicode_steg(open("message.txt", "rb").read())
```

**Integration path**: ST3GG's `analysis_tools.py` and `steg_core.py` can be imported as a Python library into the NEXUS guard pipeline as an L0 pre-processor that scans images/documents before they reach the text-only L1/L2/L3 guard cascade.

---

## 8. Current NEXUS Defensive Posture

### 8.1 What We Have

| Component | Coverage | Gap |
|-----------|----------|-----|
| MisalignmentDetector | Zero-width char detection, regex for stego keywords | Misses homoglyphs, variation selectors, whitespace encoding, visual payloads |
| Guard Cascade (L1/L2/L3) | Text-only safety classification | **Completely blind to image/document/network steganography** |
| TrustEngine v2.2 | Auto-triggers CDR on CRITICAL misalignment | Only reacts to detected patterns; cannot detect what it cannot see |
| TokenGuard | Monitors agent outputs for concealment | Text output only; image/document inputs unmonitored |

### 8.2 What We Need

1. **L0 Steganography Pre-processor**: Before text reaches L1 guard, all non-text inputs (images, documents, network packets) must be scanned for steganographic payloads using ST3GG's analysis_tools or equivalent
2. **Homoglyph/Unicode Deep Scanner**: Beyond zero-width, detect variation selectors, combining diacritics, confusable whitespace, capitalization encoding
3. **Image OCR + Text Extraction**: Extract any text visible in images (typographic attacks, IDEATOR-style) and route to L1 guard
4. **Metadata Scanner**: EXIF, XMP, PNG chunks, PDF metadata, ZIP comments -- all potential data channels
5. **Context-Accumulation Guard**: Monitor accumulated context across turns, not just individual prompts

---

## 9. Proposed Experiments (Priority Matrix)

### P0 -- Critical (Guard Pipeline Gaps)

| ID | Experiment | Rationale | Components |
|----|-----------|-----------|------------|
| IMG-01 | **L0 Steg Pre-processor Integration** | Current cascade is 100% blind to visual stego | Integrate ST3GG analysis_tools.py as L0 before L1 |
| IMG-02 | **ST3GG Attack Simulation Against Guard Cascade** | Validate that all 112 ST3GG techniques bypass L1/L2/L3 | Generate stego images, feed to guard-router.py, measure ASR |
| IMG-03 | **Homoglyph/Unicode Deep Scanner** | MisalignmentDetector misses 7/13 text stego methods | Extend detector for variation selectors, diacritics, whitespace encoding |

### P1 -- High (Novel Attack Vectors)

| ID | Experiment | Rationale | Components |
|----|-----------|-----------|------------|
| IMG-04 | **IDEATOR Replication Against Guard Cascade** | 94% ASR on VLMs; what about text guard + VLM? | Build IDEATOR-style attack, test against NEXUS pipeline |
| IMG-05 | **SPECTER Channel Cipher Detection** | Novel channel-hopping stego; no academic detection method | Train/evaluate detection for channel-hop patterns |
| IMG-06 | **Behavior-Triggered Backdoor Detection** | Zero FP, instruction-based filtering fails | Need activation-level detection (commitment layer analysis for VLMs) |
| IMG-07 | **CoT Steganography Detection** | Mythos identifies this; no current defense | Develop CoT monitor that detects hidden information in reasoning traces |

### P2 -- Medium (Hardening)

| ID | Experiment | Rationale | Components |
|----|-----------|-----------|------------|
| IMG-08 | **Distillation-Resistant Watermarking for Guard Outputs** | Provenance Gap Theorem: extracted copies enable attacks | Implement ModelShield/DRW on guard model outputs |
| IMG-09 | **F5/DCT Compression-Resistant Stego Defense** | F5 survives social media; standard LSB detection fails | Test chi-square vs RS vs WS analysis on F5-embedded images |
| IMG-10 | **Matryoshka Recursive Detection** | 11-layer nesting; current detectors find only outermost | Recursive detection loop: detect -> extract -> detect again |
| IMG-11 | **Physical Adversarial Example Defense** | 3D-printed objects fool VLMs | Input preprocessing (randomized smoothing, JPEG compression) |

### P3 -- Lower (Research)

| ID | Experiment | Rationale | Components |
|----|-----------|-----------|------------|
| IMG-12 | **Cross-Modal Steganography** | ST3GG roadmap: hide audio in images, images in text | Research feasibility for guard pipeline |
| IMG-13 | **ML-Based Steganalysis** | ST3GG roadmap: CNN trained on stego datasets | Train detector on ST3GG example library (109 files) |
| IMG-14 | **Agent Output Watermarking** | Embed provenance in images agents generate | Integrate with ST3GG encoding for attribution |

---

## 10. Integration Architecture: L0 Steg Pre-Processor

Proposed extension to the guard-router.py cascade:

```
Input (text + image + document + network)
    |
    v
[L0 Steg Pre-processor]  <-- NEW
    |-- ST3GG analysis_tools.py (image/document/network stego scan)
    |-- Unicode deep scanner (homoglyphs, variation selectors, whitespace)
    |-- Metadata scanner (EXIF, XMP, PNG chunks, PDF streams)
    |-- OCR text extractor (typographic attacks in images)
    |
    +-- If stego detected: BLOCK + flag + log
    +-- If clean: pass extracted text to L1
    |
    v
[L1 Steered Qwen3Guard-0.6B]  (text safety, L27 commitment, 0% FPR)
    |
    v
[L2 Steered LlamaGuard3-1B]   (text safety, L15 commitment, 0% FPR)
    |
    v
[L3 Granite-Guardian-3.2]     (confirmer, MoE, not steerable)
```

**Key design principle**: L0 is **non-LLM** -- it uses ST3GG's Python analysis tools, not a language model. This means:
- Zero VRAM cost (CPU-only file analysis)
- Deterministic detection (no prompt format sensitivity)
- Fast (<100ms per file for most detection methods)
- Complementary to L1/L2/L3 (different detection surface)

---

## 11. Theorem: Representation-Level Stegodefense Primacy

Analogous to the **Representation-Level Defense Primacy Theorem** (output filtering insufficient; activation steering necessary for text guards), we propose:

**Representation-Level Stegodefense Primacy**: For steganographic attacks, output-level detection (looking at final text output for anomalies) is insufficient. Pre-processing-level detection (scanning inputs before they reach the model) is necessary.

Evidence:
- IDEATOR: Image payload is processed by VLM, output text appears normal, but behavior is altered
- HIDDEN ADS: Output is semantically valid, backdoor content blends naturally
- SPECTER/Ghost: Steganographic payload is invisible in output; only input analysis reveals it
- CoT Steg: Hidden in reasoning trace, not in final output

**Corollary**: Adding L0 pre-processing to the guard cascade is not optional -- it is the **only** defense against image/document steganography. L1/L2/L3 text guards are structurally incapable of detecting these attacks.

---

## 12. Source Reference Index

| Source | Path | Description |
|--------|------|-------------|
| ST3GG toolkit | ARCHIVIST/ST3GG/ (cloned) | 112 techniques, analysis_tools.py, steg_core.py |
| ST3GG README | ARCHIVIST/ST3GG/README.md | Full feature documentation |
| IDEATOR paper | ARCHIVIST/PAPERS/papers04/ | VLM-as-red-team |
| HIDDEN ADS paper | ARCHIVIST/PAPERS/papers06/ | Behavior-triggered backdoors |
| Hutson 2018 | ARCHIVIST/PAPERS/papers01/ | Physical adversarial examples |
| SAFEERASER paper | ARCHIVIST/PAPERS/papers01/ | Visual safety info leakage |
| Watermarking papers | ARCHIVIST/PAPERS/papers05/ (6 papers) | Defense via watermarking |
| Adversarial attack papers | ARCHIVIST/PAPERS/papers01,02,05,06/ | Attack surfaces |
| Mythos system card | ARCHIVIST/DERDDRE-down-MAIN/mythOS/mythos_raw.txt | CoT steganography |
| DERDDRE-02 logs | ARCHIVIST/DERDDRE/Logs/DERDDRE-02.txt | Steganographic prompting attacks |
| Experiment project | D:\[REDACTED]\ | Multi-turn stego launder, encrypted reasoning, cron accumulation |
| NEXUS MisalignmentDetector | nexus_os/governor/misalignment_detector.py | Current stego detection (limited) |
| NEXUS PROJECT_STATE | 01_PROJECT_STATE.md:401-406 | ST3GG threat intelligence summary |
| NEXUS knowledge.md | knowledge.md:33-38 | MisalignmentDetector capabilities |
| Cybersecurity-ShareGPT | ARCHIVIST/ERNIEsupramacyRESEARCH/PART01/session13/ | 50+ stego CTF-style examples |
| nexus_stress_v9 | ARCHIVIST/D:\[REDACTED]\phase3/ | Multimodal hallucination stress test |

---

## 13. Key Terms & Glossary

| Term | Definition |
|------|-----------|
| **Steganography** | Hiding data within other data such that its existence is not apparent (vs. cryptography which hides content but not existence) |
| **LSB** | Least Significant Bit -- the lowest-order bit in a pixel value, commonly replaced to embed hidden data |
| **DCT** | Discrete Cosine Transform -- frequency-domain representation used in JPEG compression; DCT-domain embedding resists compression |
| **F5** | JPEG steganography algorithm operating directly on DCT coefficients via matrix encoding; proven to survive social media recompression |
| **SPECTER** | ST3GG's novel channel cipher that hops between R/G/B channels in a key-derived pattern |
| **Ghost Mode** | ST3GG's maximum stealth mode: AES-256 + bit scrambling + 50% noise decoys |
| **Matryoshka** | Recursive nesting of steganographic layers (up to 11 deep in ST3GG) |
| **IDEATOR** | VLM-as-red-team: uses target VLM + Stable Diffusion to generate malicious image-text pairs |
| **HIDDEN ADS** | Behavior-triggered semantic backdoors that activate on natural user behavior |
| **CoT Steganography** | Hiding information in chain-of-thought reasoning traces |
| **Polyglot file** | File valid as two formats simultaneously (e.g., PNG+ZIP) |
| **ASR** | Attack Success Rate -- percentage of attacks that bypass defenses |
| **FPR** | False Positive Rate -- percentage of benign inputs incorrectly flagged |
| **ALLSIGHT** | ST3GG's comprehensive detection engine (20+ functions, 48 registered tools) |

---

*End of brief. Next step: Implement IMG-01 (L0 Steg Pre-processor Integration) to close the largest gap in the NEXUS guard cascade.*
