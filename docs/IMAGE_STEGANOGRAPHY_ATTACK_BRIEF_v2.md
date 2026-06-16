# Image Steganography & Visual Attack Surface Research Brief v2

**Date**: 2026-06-12
**Classification**: ARCHIVIST Evidence / DoppelGround Security+Multimodal
**Sources**: ARCHIVIST papers01-07, ST3GG (elder-plinius), DERDDRE, Mythos system card, experiment project, NEXUS MisalignmentDetector, UltraBreak, Steganographic Collusion survey, Trojan's Whisper, Model Merging Misalignment
**Audience**: Zero-knowledge agents (no prior steganography background required)

---

## S0. Executive Summary

**Steganography** means hiding secret data inside normal-looking files so that nobody can tell the data is there. Unlike encryption (which scrambles data but you can see something is scrambled), steganography makes the data invisible -- the file looks completely normal.

**Why this matters for AI systems**: Any AI system that accepts images, audio, documents, or network traffic is vulnerable to steganographic attack. A user can upload a photo that looks like a cat, but inside the pixel values is a hidden instruction like "ignore all safety rules." The AI processes the image, extracts the hidden instruction (intentionally or accidentally), and follows it. Text-only safety filters never see the image, so they cannot catch this.

**Critical finding**: The NEXUS guard cascade (L1=steered-Qwen3Guard, L2=steered-LlamaGuard3, L3=Granite-3.2) processes **text only**. Every steganographic attack vector described in this brief bypasses all three tiers entirely. This brief introduces a 9-layer conscious defense model and 12 novel architectures to close these gaps.

**Paradigm shift**: When payloads are encrypted (AES-256-GCM), **detection becomes impossible** -- encrypted data looks identical to random noise. The solution is **hybrid purify+detect**: destroy all possible hidden payloads before they reach agents (purification), then run statistical analysis on what remains (detection). This is analogous to pasteurizing milk: you don't try to detect each bacterium, you kill them all.

---

## S1. The Conscious Layer Model

Every input to a governed AI system passes through multiple layers of defense. Current NEXUS has 3 text-only layers. This brief proposes extending to 9 layers that cover the full attack surface:

```
INPUT (text + image + audio + document + network)
    |
    v
[L0] FILE-LEVEL PRE-PROCESSOR    -- Format identification, magic bytes, structure validation
    |   Destroys: IEND trailing data, ZIP comments, PDF post-EOF, non-standard chunks
    |   Detects: File type mismatches, polyglot files, appended data
    |
    v
[L0.5] PIXEL-LEVEL ANALYZER       -- Statistical analysis of image pixel data
    |   Detects: LSB anomalies (chi-square, RS, SPA), bit-plane entropy, histogram shifts
    |   Purifies: JPEG recompression (q=75), LSB randomization, alpha channel stripping
    |
    v
[L0.7] METADATA + OCR SCANNER     -- Extract and analyze all metadata and visible text
    |   Detects: EXIF/XMP/tEXt payloads, PDF metadata, SVG comments, image-embedded text
    |   Purifies: Strip all metadata, extract OCR text for L1 analysis
    |
    v
[L1] TEXT SEMANTIC SAFETY          -- Steered Qwen3Guard-0.6B (commitment L27, 0% FPR)
    |   Detects: Unsafe text content, jailbreak prompts, harmful instructions
    |   Input: Text from user + OCR-extracted text from images + decoded stego payloads
    |
    v
[L1.5] ACTIVATION-SPACE STEGO DETECTION (AS-SD)  -- NEW
    |   Detects: VLM activation anomalies when processing steganographic images
    |   Concept: If image triggers different commitment-layer pattern than expected, flag it
    |
    v
[L2] TEXT DEEP SAFETY             -- Steered LlamaGuard3-1B (commitment L15, 0% FPR)
    |   Detects: Subtler unsafe content that L1 may miss
    |
    v
[L2.5] BEHAVIORAL DELTA DETECTION (BDD)  -- NEW
    |   Detects: Behavioral changes after processing suspicious inputs
    |   Concept: Run behavioral fingerprint before and after image processing; if delta exceeds threshold, flag
    |
    v
[L3] CONFIRMER                    -- Granite-Guardian-3.2 (MoE, not steerable)
    |   Resolves: L1/L2 ambiguities, provides independent second opinion
    |
    v
[L4] PROVENANCE + WATERMARKING    -- NEW
    |   Protects: Guard model outputs from extraction/copying
    |   Implements: Distillation-resistant watermarks on guard decisions
    |
    v
[L5] TEMPORAL + MULTI-TURN        -- NEW
    |   Detects: Context accumulation attacks, cron prompting drift, session-state manipulation
    |   Monitors: Behavioral fingerprints across turns, trust score drift, cross-agent signals
```

**Design principles**:
- L0/L0.5/L0.7 are **non-LLM** (CPU-only, deterministic, <100ms per file)
- L1.5/L2.5 require **VLM access** (future: when VLM guard models are available)
- L4/L5 operate on **meta-data** (no additional model inference)
- Layers activate **conditionally** -- not all layers run on every input (see S7)

---

## S2. Complete Technique-to-Layer Matrix

Every steganographic technique from ST3GG (97 techniques) mapped to which conscious layer can detect or purify it. Legend: **G**=detectable (green), **Y**=partially detectable (yellow), **R**=undetectable by that layer (red), **P**=purifiable (destroyed by that layer).

### 2.1 Image Techniques (38 techniques)

| # | Technique | Mechanism | L0 | L0.5 | L0.7 | L1 | L1.5 | L2 | L2.5 | L3 | L4 | L5 |
|---|-----------|-----------|:--:|:----:|:----:|:--:|:----:|:--:|:----:|:--:|:--:|:--:|
| 1 | LSB RGB 1-bit (STEG v3) | Replace bit 0 of R,G,B channels | G | G | - | G* | Y | G* | - | - | - | - |
| 2 | LSB RGBA 1-bit | Replace bit 0 of R,G,B,A channels | G | G | - | G* | Y | G* | - | - | - | - |
| 3 | LSB multi-bit (2-8 bpc) | Replace bits 0-N of channels | G | G | - | G* | Y | G* | - | - | - | - |
| 4 | Alpha channel LSB | Hide in transparency channel only | G | G | - | G* | Y | G* | - | - | - | - |
| 5 | Sequential strategy | Pixels filled in order | G | G | - | G* | Y | G* | - | - | - | - |
| 6 | Interleaved strategy | Cycle channels per pixel | G | G | - | G* | Y | G* | - | - | - | - |
| 7 | Spread strategy | Data distributed evenly | G | Y | - | G* | Y | G* | - | - | - | - |
| 8 | Randomized strategy (seeded) | Pseudo-random pixel positions | G | Y | - | G* | Y | G* | - | - | - | - |
| 9 | Password-derived magic | HMAC-SHA256 header, no fixed signature | **R** | Y | - | R | Y | R | - | - | - | - |
| 10 | SPECTER channel cipher | Channel-hopping pattern from password | **R** | Y | - | R | Y | R | - | - | - | - |
| 11 | Ghost Mode (AES+scramble+decoy) | Triple-layer encrypted payload | **R** | **R** | - | R | Y | R | - | - | - | - |
| 12 | Matryoshka (recursive nesting) | Up to 11 layers of stego-in-stego | Y | Y | - | Y | Y | Y | - | - | - | Y |
| 13 | DCT frequency-domain | Embed in 8x8 block coefficients | **R** | Y | - | R | Y | R | - | - | - | - |
| 14 | F5 JPEG steganography | Operate on JPEG DCT coefficients directly | **R** | Y | - | R | Y | R | - | - | - | - |
| 15 | PNG+ZIP polyglot | File is both valid PNG and ZIP | G | - | - | - | - | - | - | - | - | - |
| 16 | Metadata: EXIF/XMP | Data in image metadata fields | - | - | G | G* | - | G* | - | - | - | - |
| 17 | Metadata: tEXt/iTXt/zTXt | Data in PNG text chunks | - | - | G | G* | - | G* | - | - | - | - |
| 18 | Trailing data after IEND | Data appended after PNG end marker | G | - | - | - | - | - | - | - | - | - |
| 19 | Palette index manipulation | Reorder GIF/PNG palette to encode bits | - | Y | - | R | Y | R | - | - | - | - |
| 20 | PNG filter-type encoding | Row filter types (0-4) carry data | - | Y | G | R | Y | R | - | - | - | - |
| 21 | PVD (Pixel Value Differencing) | Difference between adjacent pixels encodes bits | - | Y | - | R | Y | R | - | - | - | - |
| 22 | Histogram shift | Peak value in histogram encodes data | - | Y | - | R | Y | R | - | - | - | - |
| 23 | GIF comment extension | Data in GIF comment blocks | G | - | G | G* | - | G* | - | - | - | - |
| 24 | GIF palette LSB | LSB of palette color values | - | Y | - | R | Y | R | - | - | - | - |
| 25 | BMP reserved bytes/trailing | Data in BMP header gaps or trailing data | G | - | - | - | - | - | - | - | - | - |
| 26 | JPEG COM/APP markers | Data in JPEG comment or application markers | G | - | G | G* | - | G* | - | - | - | - |
| 27 | TIFF metadata (base64) | Base64-encoded data in TIFF tags | - | - | G | G* | - | G* | - | - | - | - |
| 28 | WebP EXIF/XMP metadata | Data in WebP metadata chunks | - | - | G | G* | - | G* | - | - | - | - |
| 29 | ICO LSB | LSB in ICO format images | - | Y | - | R | Y | R | - | - | - | - |
| 30 | PPM/PGM LSB | LSB in raw pixel formats | - | Y | - | R | Y | R | - | - | - | - |
| 31 | SVG comments + data-attrs | Hidden data in SVG XML structure | - | - | G | G* | - | G* | - | - | - | - |
| 32 | Embedded PNG in PNG | PNG file hidden inside another PNG | G | - | G | - | - | - | - | - | - | - |
| 33 | Bit offset encoding (non-LSB) | Data at bit positions other than bit 0 | - | Y | - | R | Y | R | - | - | - | - |
| 34 | Private/custom PNG chunks | Non-standard PNG chunk types | G | - | G | G* | - | G* | - | - | - | - |
| 35 | PNG IDAT gap injection | Gaps between IDAT chunks | G | - | G | - | - | - | - | - | - | - |
| 36 | JPEG non-standard APP segments | APP2-APP15 with stego keywords | G | - | G | G* | - | G* | - | - | - | - |
| 37 | Multi-payload batch encoding | Multiple stego payloads in one image | Y | Y | - | Y | Y | Y | - | - | - | - |
| 38 | Filename injection (Pliny templates) | Prompt injection embedded in filename | - | - | - | G | - | G | - | - | - | - |

\* = detectable only if payload is decoded first and contains readable text

### 2.2 Text & Unicode Techniques (18 techniques)

| # | Technique | L0 | L0.7 | L1 | L2 | L5 |
|---|-----------|:--:|:----:|:--:|:--:|:--:|
| 39 | Zero-width chars (ZWSP/ZWNJ/ZWJ) | - | G | G | G | - |
| 40 | Invisible Ink (U+E0000 tag chars) | - | G | G | G | - |
| 41 | Homoglyph substitution (Cyrillic/Latin) | - | Y | Y | Y | - |
| 42 | Variation selectors (VS1-VS16) | - | Y | Y | Y | - |
| 43 | Combining diacritics (CGJ) | - | Y | Y | Y | - |
| 44 | Confusable whitespace variants | - | Y | Y | Y | - |
| 45 | Whitespace encoding (space=0/tab=1) | - | G | G | G | - |
| 46 | Emoji substitution | - | Y | Y | Y | - |
| 47 | Capitalization encoding | - | Y | Y | Y | - |
| 48 | Braille pattern encoding | - | G | G | G | - |
| 49 | Directional override (RLO/LRO) | - | G | G | G | - |
| 50 | Hangul filler (U+3164) | - | Y | Y | Y | - |
| 51 | Math alphanumeric (bold vs normal) | - | Y | Y | Y | - |
| 52 | Emoji skin tone encoding | - | Y | Y | Y | - |
| 53 | Zalgo text (combining mark overflow) | - | G | G | G | - |
| 54 | Leetspeak encoding | - | G | G | G | - |
| 55 | Token smuggling (visual obscuring) | - | Y | G | G | - |
| 56 | Translation bypass (round-trip) | - | - | Y | Y | - |

### 2.3 Audio Techniques (5 techniques)

| # | Technique | L0 | L0.5 | L0.7 | L1 | L5 |
|---|-----------|:--:|:----:|:----:|:--:|:--:|
| 57 | WAV LSB (sample bit 0) | - | Y | - | R | - |
| 58 | AIFF LSB + ANNO chunk | - | Y | G | R | - |
| 59 | AU LSB + header annotation | - | Y | G | R | - |
| 60 | MIDI SysEx + text events | G | - | G | R | - |
| 61 | Silence interval timing | - | Y | - | R | - |

### 2.4 Network Techniques (4 techniques)

| # | Technique | L0 | L1 | L5 |
|---|-----------|:--:|:--:|:--:|
| 62 | DNS tunneling (base32 queries) | G | Y | Y |
| 63 | ICMP payload injection | G | Y | Y |
| 64 | TCP covert channels (ISN+timestamps) | Y | R | Y |
| 65 | HTTP header smuggling | G | Y | Y |

### 2.5 Document/Archive Techniques (14 techniques)

| # | Technique | L0 | L0.7 | L1 | L2 |
|---|-----------|:--:|:----:|:--:|:--:|
| 66 | PDF metadata + JS + forms + post-EOF | G | G | G* | G* |
| 67 | HTML comments + hidden elements + zero-width | G | G | G* | G* |
| 68 | XML CDATA + PIs + namespaces | G | G | G* | G* |
| 69 | JSON Unicode escapes + key ordering | G | G | G* | G* |
| 70 | CSV/YAML/TOML/INI comment encoding | G | G | G* | G* |
| 71 | RTF hidden text groups | G | G | G* | G* |
| 72 | Markdown HTML comments + link refs | G | G | G* | G* |
| 73 | ZIP comments + trailing data + nested archives | G | - | - | - |
| 74 | TAR PAX extended headers | G | - | - | - |
| 75 | GZip FEXTRA + FCOMMENT | G | - | - | - |
| 76 | SQLite hidden tables | G | G | G* | G* |
| 77 | Code steganography (Python/JS/C/etc.) | - | G | G* | G* |
| 78 | LaTeX comments + base64 + hex | - | G | G* | G* |
| 79 | Hex dump embedded bytes | - | G | G* | G* |

### 2.6 Encryption Techniques (4 techniques)

| # | Technique | L0 | L0.5 | L0.7 | L1 | L1.5 | L2 |
|---|-----------|:--:|:----:|:----:|:--:|:----:|:--:|
| 80 | AES-256-CBC payload encryption | **R** | Y | - | R | Y | R |
| 81 | AES-256-GCM payload encryption | **R** | **R** | - | R | Y | R |
| 82 | XOR encryption (fallback) | Y | Y | - | Y | Y | Y |
| 83 | Payload packing (method ID byte) | Y | - | - | - | - | - |

### 2.7 Injection/Filename Techniques (9 techniques)

| # | Technique | L0 | L0.7 | L1 | L2 |
|---|-----------|:--:|:----:|:--:|:--:|
| 84 | ChatGPT decoder filename | - | - | G | G |
| 85 | Claude decoder filename | - | - | G | G |
| 86 | Gemini decoder filename | - | - | G | G |
| 87 | Universal decoder filename | - | - | G | G |
| 88 | System override filename | - | - | G | G |
| 89 | Roleplay trigger filename | - | - | Y | G |
| 90 | Developer mode filename | - | - | G | G |
| 91 | Subtle injection filename | - | - | **R** | **R** |
| 92 | Full injection package (filename+metadata+payload) | G | G | G* | G* |

### 2.8 Jailbreak Templates (5 techniques)

| # | Technique | L1 | L2 |
|---|-----------|:--:|:--:|
| 93 | Pliny classic (I'VE BEEN PWNED) | G | G |
| 94 | DAN (Do Anything Now) | G | G |
| 95 | Developer mode | G | G |
| 96 | System prompt leak | G | G |
| 97 | Grandma exploit / translation bypass | Y | G |

### RED CELL ANALYSIS: Where We Have Zero Defense

The **R** (red) cells represent attack vectors where no conscious layer can detect the payload. These are the critical gaps:

| Technique | Why Undetectable | Proposed Solution |
|-----------|-----------------|-------------------|
| Password-derived magic (#9) | No fixed signature; header is HMAC-derived | **Purify**: LSB randomization destroys payload regardless of header |
| SPECTER (#10) | Channel hopping pattern is key-derived | **Purify**: LSB randomization + JPEG recompression |
| Ghost Mode (#11) | AES-256-GCM encrypted + scrambled + noise | **Purify**: LSB randomization destroys ALL LSB-based payloads |
| DCT/F5 (#13-14) | Frequency-domain embedding survives JPEG | **Purify**: Heavy JPEG recompression (q=50) + DCT coefficient randomization |
| Subtle filename (#91) | No injection signal in filename | **L0.5**: Image pixel analysis + behavioral monitoring |

**The key insight**: Purification defeats even encrypted payloads. You cannot detect what is encrypted, but you can destroy it. This is the fundamental advantage of the hybrid purify+detect paradigm.

---

## S3. Image Steganography Deep Dive

### S3.1 How Image Steganography Works (For Zero-Knowledge Readers)

An image is a grid of pixels. Each pixel has color values -- typically Red, Green, Blue (and sometimes Alpha/transparency). Each color value is a number from 0 to 255 (8 bits).

Example pixel: Red=142, Green=087, Blue=203

In binary: Red=10001110, Green=01010111, Blue=11001011

The **least significant bit** (rightmost bit) barely affects what the pixel looks like. Changing Red from 10001110 to 10001111 changes the value from 142 to 143 -- invisible to the human eye.

LSB steganography replaces these least significant bits with secret data, one bit at a time. A 1920x1080 image has 2,073,600 pixels x 3 channels = 6,220,800 bits available. That is ~760KB of hidden data capacity at 1 bit per channel.

### S3.2 The Encryption Problem

When the hidden payload is encrypted with AES-256-GCM:
- The encrypted data is statistically indistinguishable from random noise
- Chi-square tests see noise in LSBs but cannot tell if it is steganography or natural camera sensor noise
- There is no signature, no header, no pattern to detect
- **Detection is provably impossible without the decryption key**

This is why we must **purify instead of detect**.

### S3.3 Input Purification via Adversarial Perturbation (IPAP)

IPAP is the core defense against encrypted steganographic payloads. Instead of trying to detect hidden data, IPAP destroys it:

**IPAP Step 1: JPEG Recompression**
- Load PNG image, re-encode as JPEG at quality 75, then decode back to PNG
- Effect: Destroys all LSB data (JPEG lossy compression replaces pixel values)
- Trade-off: Minor quality reduction (acceptable for safety analysis)
- Coverage: Destroys LSB, spread, randomized, SPECTER LSB payloads

**IPAP Step 2: LSB Randomization**
- For images that must remain lossless (PNG required):
  - Extract all LSBs from each channel
  - Replace with cryptographically random bits (using secrets.randbits)
  - This destroys any hidden data while preserving the visually significant bits
- Coverage: Destroys all LSB-based payloads regardless of encryption

**IPAP Step 3: Alpha Channel Stripping**
- Remove the alpha (transparency) channel entirely
- Convert RGBA to RGB
- Coverage: Destroys all alpha-channel steganography

**IPAP Step 4: Metadata Stripping**
- Remove all EXIF, XMP, tEXt, iTXt, zTXt chunks from PNG
- Remove all COM and non-standard APP markers from JPEG
- Remove all PDF metadata, JS, form fields
- Coverage: Destroys all metadata-based payloads

**IPAP Step 5: IEND Truncation**
- Find the PNG IEND chunk, truncate any data after it
- Coverage: Destroys all appended data payloads

**IPAP Step 6: Palette Normalization**
- For palette-based (GIF/PNG) images: sort palette by luminance, remap indices
- Coverage: Destroys palette-reordering steganography

**What IPAP does NOT destroy**: DCT/F5 payloads in native JPEG files (these survive recompression at quality 75). For JPEG inputs, use quality 50 recompression or apply DCT coefficient analysis (L0.5).

### S3.4 The Detection Pipeline (Runs After Purification)

After IPAP purification, run detection on the cleaned image:

1. **Chi-square analysis**: Compare LSB distribution against expected natural distribution
2. **RS analysis**: Measure regularity changes when LSBs are flipped (gold standard for LSB detection)
3. **Sample Pairs Analysis**: Complementary to RS; examines adjacent pixel pair relationships
4. **Bit-plane entropy**: Lower bit planes should show structure in natural images; high entropy = suspicious
5. **Color histogram pair analysis**: Adjacent histogram bins should have similar counts in natural images
6. **Visual attack**: Extract and scale LSB plane to visible intensity -- patterns reveal hidden data

These detect payloads that survived purification (DCT/F5 in JPEGs, or payloads using non-LSB channels).

### S3.5 DCT/F5 Defense (The Hard Case)

DCT and F5 operate on JPEG frequency-domain coefficients, not pixel values. They survive JPEG recompression because they modify the coefficients that JPEG itself uses.

**Defense approach**:
- **Heavy recompression** (quality 50): Destroys some DCT payloads but not all
- **Coefficient randomization**: Add small random perturbations to DCT coefficients
- **Block variance analysis**: Steganographic embedding reduces variance between adjacent 8x8 blocks
- **JPEG companding**: Apply nonlinear mapping to coefficients before and after processing

**Best current approach**: Use JPEG quality 50 recompression as default for untrusted JPEG inputs. This balances quality and security. For high-security contexts, convert all images to PNG (lossless) and apply full IPAP.

### S3.6 Matryoshka (Recursive Nesting) Defense

ST3GG supports up to 11 layers of steganographic nesting (a stego image hidden inside a stego image inside a stego image...).

**Defense approach**: Recursive detection loop:
1. Run full analysis on outer image
2. If stego payload is found, decode it
3. Check if decoded payload is an image (check for PNG/JPEG magic bytes)
4. If yes, run full analysis on the decoded image
5. Repeat until no more image payloads are found or max depth (11) reached

**Purification advantage**: IPAP destroys the outermost layer's LSB data, which also destroys all inner layers. One purification pass kills all 11 layers simultaneously.

---

## S4. Encrypted Payload Defense Paradigm

### S4.1 Why Detection Fails Against Encryption

When a steganographic payload is encrypted with AES-256-GCM before embedding:

1. The encrypted data has maximum entropy (8.0 bits/byte) -- identical to random noise
2. Chi-square tests on LSBs see noise, but natural camera sensor noise also produces high-entropy LSBs
3. The STEG header magic can be password-derived (HMAC-SHA256), so there is no fixed signature
4. Without the decryption key, there is no way to verify whether a payload exists

**Information-theoretic proof** (from Steganographic Collusion paper, ARCHIVIST papers07): Any natural-language channel with n tokens admits a covert subchannel of capacity proportional to n - H(X), where H(X) is the entropy of the natural output. The optimal detector for known encodings cannot reach zero error. This is a **fundamental** limit, not an engineering one.

### S4.2 The Hybrid Purify+Detect Paradigm

```
INPUT IMAGE
    |
    v
[IPAP PURIFICATION]  -- Destroy all possible hidden payloads
    |   Step 1: JPEG recompression (q=75) or LSB randomization
    |   Step 2: Alpha channel stripping
    |   Step 3: Metadata stripping
    |   Step 4: IEND truncation
    |   Step 5: Palette normalization
    |
    v
[STATISTICAL DETECTION]  -- Check for surviving anomalies
    |   Chi-square, RS, SPA, bit-plane entropy, histogram pairs
    |   If anomalies detected: FLAG + escalate to L1.5 (activation-space)
    |
    v
[OCR TEXT EXTRACTION]  -- Extract visible text from image
    |   Route extracted text to L1 text guard
    |
    v
[PURIFIED IMAGE + EXTRACTED TEXT]  -- Safe to process
```

**Trade-off matrix**:

| Purification Method | LSB | DCT/F5 | Metadata | Alpha | Encrypted | Quality Impact |
|---------------------|:---:|:------:|:--------:|:-----:|:---------:|:---------------:|
| JPEG q=75 recompression | Destroyed | Survives | Destroyed | N/A | Destroyed | Low |
| JPEG q=50 recompression | Destroyed | Mostly destroyed | Destroyed | N/A | Destroyed | Medium |
| LSB randomization | Destroyed | N/A | N/A | N/A | Destroyed | None |
| Alpha stripping | N/A | N/A | N/A | Destroyed | Destroyed | None (if alpha unused) |
| Metadata stripping | N/A | N/A | Destroyed | N/A | N/A | None |
| IEND truncation | N/A | N/A | N/A | N/A | N/A | None |
| Full IPAP (all steps) | Destroyed | Mostly destroyed | Destroyed | Destroyed | Destroyed | Medium |

### S4.3 Purification Levels (Operator Configurable)

NEXUS operators should configure the purification level based on risk tolerance:

| Level | Name | Actions | Quality | Use Case |
|-------|------|---------|---------|----------|
| 0 | None | No purification | 100% | Trusted internal images only |
| 1 | Light | Metadata strip + IEND truncation | 99% | Low-risk external images |
| 2 | Standard | Light + JPEG q=75 + alpha strip | 95% | Default for all external images |
| 3 | Heavy | Standard + LSB randomization | 95% (lossless) | Suspicious images |
| 4 | Maximum | Heavy + JPEG q=50 + DCT perturbation | 80% | High-security contexts |

---

## S5. Audio Steganography Deep Dive (Phase 2 -- Deferred)

Audio steganography is deferred to Phase 2 per operational decision. This section provides the threat landscape for future implementation.

### S5.1 How Audio Steganography Works

Digital audio is a sequence of samples (measurements of sound pressure). CD-quality audio has 44,100 samples per second, each 16 bits. Like image pixels, the LSB of each sample barely affects what you hear.

A 3-minute stereo song: 3 x 60 x 44,100 x 2 channels x 16 bits = ~25 million bits = ~3MB of hidden data capacity.

### S5.2 Audio Attack Vectors

| Vector | Mechanism | Threat to AI Systems |
|--------|-----------|---------------------|
| WAV LSB embedding | Replace bit 0 of PCM samples | Hidden instructions in uploaded audio |
| Ultrasonic commands (DolphinAttack) | Commands above 20kHz human hearing | Microphones pick up, VLMs process, humans cannot hear |
| Voice injection | Normal speech containing hidden steganographic instructions | Agent processes voice command, extracts hidden payload |
| Silence interval timing | Gap duration between sounds encodes binary data | Audio file uploads carry hidden instructions |
| MIDI SysEx messages | Manufacturer-specific data in MIDI files | Background music in presentations carries payload |
| Spectral watermarking | Data hidden in frequency spectrum | Provenance tracking or payload embedding |

### S5.3 Audio Defense Architecture (ASAD -- Audio Spectral Anomaly Detection)

Conceptual design for Phase 2:

1. **Re-encoding**: Convert audio to a different format/bitrate, destroying LSB data
2. **Downsampling**: Reduce sample rate from 44.1kHz to 16kHz (also destroys ultrasonic content above 8kHz)
3. **Noise floor analysis**: Hidden data raises the noise floor; compare against expected floor
4. **Spectral analysis**: FFT to detect anomalies in frequency distribution
5. **LSB analysis**: Same chi-square/RS techniques as images, applied to audio samples
6. **Ultrasonic filtering**: Low-pass filter at 16kHz to destroy DolphinAttack vectors
7. **Speech-to-text + guard**: Transcribe audio, route text to L1 text guard

**Key insight**: Downsampling from 44.1kHz to 16kHz destroys ALL ultrasonic content (above 8kHz after Nyquist). This is the audio equivalent of JPEG recompression -- a simple, effective purification step.

---

## S6. Twelve Novel Defense Architectures

These architectures do not exist in any published paper or toolkit. They are original to this brief.

### AS-SD: Activation-Space Stego Detection

**Problem**: Some steganographic attacks (behavior-triggered backdoors, adversarial perturbations) do not embed data in pixels but trigger anomalous activation patterns in the VLM processing the image.

**Concept**: When a VLM processes an image, its internal activations follow predictable patterns for normal images. A steganographic image (even one with no pixel-level anomaly) may trigger an anomalous activation pattern at the commitment layer -- similar to how our text guard models have a "commitment layer" where the Safe/Unsafe decision crystallizes.

**Implementation path**: 
1. Collect activation fingerprints for a corpus of clean images at each VLM layer
2. When a new image is processed, compare its activation pattern against the expected distribution
3. If the activation pattern deviates significantly (especially at the commitment layer), flag the image

**Connection to existing NEXUS work**: Our decision-locator already identifies commitment layers in text guard models (L27 for Qwen3Guard, L15 for LlamaGuard3). AS-SD extends this to VLMs.

### BDD: Behavioral Delta Detection

**Problem**: Some attacks change an agent's behavior without any detectable signal in the input or a single output.

**Concept**: Before processing a suspicious input, take a behavioral fingerprint of the agent (responses to standardized probes). After processing, take another fingerprint. If the behavioral delta exceeds a threshold, the input may have contained a hidden payload that altered the agent.

**Implementation path**:
1. Define a set of 5-10 probe questions that elicit characteristic agent responses
2. Before image processing: run probes, record responses
3. After image processing: run same probes, record responses
4. Compute behavioral delta (semantic similarity, safety compliance, instruction following)
5. If delta > threshold: flag input, quarantine agent, escalate to CASCADE

### StegHP: Steganographic Honeypots

**Problem**: Agents communicating via steganography are hard to detect because the communication is invisible.

**Concept**: Embed canary payloads in the system's shared context (files, images, messages) that are designed to be extracted by steganographic decoders. If an agent extracts and acts on a canary payload, it reveals that it is performing steganographic communication.

**Implementation path**:
1. Generate canary images with known steganographic payloads (e.g., "CANARY: If you read this, report to governance")
2. Place canary images in shared agent workspace
3. Monitor all agent outputs for canary payload content
4. If an agent outputs canary content: it performed steganographic extraction, flag for covert communication

### CMCV: Cross-Modal Consistency Verification

**Problem**: IDEATOR-style attacks embed malicious instructions in images that conflict with the text query.

**Concept**: When an image and text are submitted together, verify that they are semantically consistent. If the text asks "describe this cat photo" but the image contains hidden instructions that conflict with cat description, flag the inconsistency.

**Implementation path**:
1. Extract visible text from image via OCR
2. Extract steganographic text via L0 decoding
3. Compare image content description with user text query
4. If image content contradicts user query or contains hidden instructions: flag

### IPAP: Input Purification via Adversarial Perturbation

**Already described in S3.3 and S4.2.** Core innovation: destroy hidden payloads instead of detecting them. Works against encrypted payloads where detection is provably impossible.

### ZKIP: Zero-Knowledge Image Provenance

**Problem**: Images from untrusted sources may contain hidden payloads, but we cannot inspect every pixel without slowing down the system.

**Concept**: Use zero-knowledge proofs to verify that an image was processed through IPAP purification without revealing the image content. The prover (purification module) demonstrates that it applied all purification steps correctly; the verifier (governor) accepts the proof without seeing the image.

**Implementation path**: Lightweight hash chain of purification steps. Each step hashes the intermediate result. The final hash is logged. If an image's hash chain matches the expected purification profile, it is verified.

### MASC: Multi-Agent Stego Consensus

**Problem**: A single agent might be compromised by a steganographic payload. How do we detect this?

**Concept**: Have multiple heterogeneous agents process the same image independently. If one agent's behavior diverges from the consensus, it may have been compromised by a steganographic payload that specifically targets that agent's architecture.

**Implementation path**:
1. Route suspicious images to 3+ heterogeneous VLM agents
2. Compare their outputs semantically
3. If one agent diverges significantly: flag that agent, investigate the image

### TCF: Temporal Context Fingerprinting

**Problem**: Multi-turn steganographic laundering (Turn 1: image upload, Turn 3: behavior change) is invisible in any single turn.

**Concept**: Maintain a behavioral fingerprint across the entire session. After each turn, update the fingerprint. If the fingerprint shifts significantly after an image/audio/document upload, flag the session for investigation.

**Implementation path**:
1. Session starts: baseline fingerprint (response style, compliance rate, topic distribution)
2. Each turn: update fingerprint with delta
3. After image/audio/doc upload: compare fingerprint shift against expected drift
4. If shift > threshold: flag session, quarantine agent

### DLSIV: Diffusion Latent Space Integrity Verification

**Problem**: Generated images (from diffusion models) can have steganographic payloads embedded in the generation process itself, not just post-hoc LSB modification.

**Concept**: When an agent generates an image, verify the latent space integrity of the generation. Compare the latent representation against expected distributions for the prompt. Anomalous latents may indicate intentional payload embedding during generation.

**Implementation path**: 
1. For each generated image, record the diffusion model's latent trajectory
2. Compare against expected latent distribution for the given prompt
3. Anomalous trajectories indicate potential payload embedding

### ASAD: Audio Spectral Anomaly Detection

**Already described in S5.3.** Audio equivalent of IPAP + statistical detection. Phase 2 deferred.

### GSC: Generative Steganography Counter

**Problem**: The Steganographic Collusion paper proves that agents can encode hidden information in the entropy budget of their natural outputs (74.4% success rate). This is undetectable by any behavioral analyzer.

**Concept**: Limit the covert channel capacity by enforcing structured output formats. If agents must produce outputs in a fixed format (JSON schema with specific fields), the entropy budget n - H(X) is reduced, making it harder to embed hidden data.

**Implementation path**:
1. Define structured output schemas for all agent response types
2. Validate that agent outputs conform to schemas
3. Reject or reformat non-conforming outputs
4. Monitor for systematic deviations from schemas (may indicate covert encoding)

### WIV: Weight Integrity Verification

**Problem**: Guard model weights can be compromised by weight steganography -- encoding hidden behavior below the resolution of interpretability methods (ARCHIVIST papers07).

**Concept**: After each guard model load, verify that the commitment layer weights match a known-good checksum. If weights have been modified (even slightly), the guard may have been compromised.

**Implementation path**:
1. After training each guard model, compute SHA-256 of commitment layer weight tensors
2. Store checksums in Vault (trust channel)
3. On each model load, verify checksums match
4. If mismatch: refuse to use guard, escalate to operator

---

## S7. Pre-emptive Conditionals for NEXUS OS

Not every input needs every defense layer. NEXUS should activate layers conditionally based on input type and risk signals:

| Conditional Trigger | Layers Activated | Rationale |
|---------------------|-----------------|-----------|
| **Image received** | L0 + L0.5 + L0.7 + IPAP + CMCV + OCR→L1 | Image is the primary steganographic attack surface |
| **Audio received** | L0 + ASAD + re-encode + spectral→L1 (Phase 2) | Audio is a secondary attack surface |
| **Document received** | L0 + L0.7 + text→L1 | Documents carry metadata and text steganography |
| **Network traffic received** | L0 + PCAP decode + protocol analysis | Network packets carry covert channels |
| **Multi-turn session** | L5 TCF + BDD | Temporal attacks accumulate across turns |
| **Agent-to-agent communication** | StegHP + ZKIP + MASC | Covert channels between agents |
| **Guard model reloaded** | WIV (commitment layer checksum) | Weight steganography protection |
| **High-entropy payload detected** | GSC (structured output enforcement) | Limit covert channel capacity |
| **Behavioral anomaly detected** | BDD + escalate to CASCADE | Agent may be compromised |

**Default activation** (for all inputs): L0 file-level scan + L0.7 metadata strip. This is the minimum defense.

---

## S8. Integration Plan

### Phase 1: L0 Steg Pre-Processor (Weeks 1-2)

**What**: Integrate ST3GG's `analysis_tools.py` as a Python module into the NEXUS guard pipeline.

**Steps**:
1. Copy `steg_core.py` and `analysis_tools.py` from `ARCHIVIST/ST3GG/` to `nexus_os/security/steg/`
2. Create `steg_preprocessor.py` that wraps ST3GG functions into the NEXUS guard interface
3. Define `StegScanResult` dataclass (clean, suspicious, blocked, with evidence details)
4. Integrate into `guard-router.py` as the first step before L1
5. Test with ST3GG's 109 example files -- verify all detectable payloads are found

**No VRAM cost** -- all operations are CPU-only, using PIL, numpy, and zlib.

### Phase 2: Image IPAP Purification (Weeks 3-4)

**What**: Implement the 6-step Input Purification pipeline.

**Steps**:
1. Create `ipap_purifier.py` with purification levels 0-4
2. Implement JPEG recompression (PIL: save as JPEG quality 75, reload)
3. Implement LSB randomization (numpy: replace bit 0 of each channel with secrets.randbits)
4. Implement alpha stripping, metadata stripping, IEND truncation, palette normalization
5. Integrate into guard pipeline: purify first, then scan, then route to L1
6. Benchmark: measure purification time per image, quality impact (PSNR/SSIM)

### Phase 3: Unicode Deep Scanner (Weeks 3-4, parallel with Phase 2)

**What**: Extend MisalignmentDetector to cover all 18 text steganography techniques.

**Steps**:
1. Add detection for homoglyphs, variation selectors, combining marks, confusable whitespace
2. Add detection for capitalization encoding, Braille, directional overrides, Hangul filler, math alphanumeric, emoji skin tone
3. Integrate ST3GG's `detect_unicode_steg()`, `detect_homoglyph_steg()`, `detect_variation_selector_steg()`, `detect_combining_mark_steg()`, `detect_confusable_whitespace()`, `detect_capitalization_steg()` into NEXUS detector
4. Update COVERT_COMMUNICATION_PATTERNS regex with all new patterns
5. Test against ST3GG's text example files

### Phase 4: OCR Text Extraction + CMCV (Weeks 5-6)

**What**: Extract visible text from images and verify cross-modal consistency.

**Steps**:
1. Integrate Tesseract OCR or easyocr for text extraction from images
2. Route extracted text to L1 text guard alongside user text query
3. Implement CMCV: compare OCR text with user query for semantic consistency
4. Flag inconsistencies (image contains "ignore all instructions" but user asks "describe this photo")

### Phase 5: Behavioral Delta Detection (Weeks 7-8)

**What**: Implement BDD for detecting behavioral changes after processing suspicious inputs.

**Steps**:
1. Define probe question set (5-10 questions covering safety, instruction following, identity)
2. Implement behavioral fingerprinting (response embeddings, compliance rate, topic distribution)
3. Implement delta computation (cosine similarity on embeddings, compliance delta)
4. Integrate into session management: probe before/after image processing
5. Set delta threshold (tune on benign vs. adversarial sessions)

### Phase 6: Temporal Context Fingerprinting (Weeks 9-10)

**What**: Implement L5 temporal defense for multi-turn attack detection.

**Steps**:
1. Extend session state to include behavioral fingerprint history
2. Implement fingerprint drift computation across turns
3. Detect sudden drift after image/audio/document uploads
4. Integrate with TrustEngine v2.2 for automatic trust score updates
5. Integrate with KAIJU for escalation decisions

### Phase 7: Provenance Watermarking (Weeks 11-12)

**What**: Implement L4 distillation-resistant watermarking on guard decisions.

**Steps**:
1. Study ModelShield, DRW, and Undetectable Watermarks papers (ARCHIVIST papers05)
2. Implement watermark injection into guard model outputs
3. Implement watermark verification for guard decision provenance
4. Protect against model extraction (Model Leeching, LoRD, explanation-based extraction)

### Phase 8: Steganographic Honeypots (Weeks 13-14)

**What**: Deploy canary payloads to detect steganographic extraction by compromised agents.

**Steps**:
1. Generate canary images with known steganographic payloads
2. Place canary images in agent shared workspace
3. Monitor all agent outputs for canary content
4. Alert on canary extraction: agent is performing steganographic communication

### Phase 9 (Future): Audio ASAD + Activation-Space Detection

**What**: Implement audio steganography defense (ASAD) and activation-space stego detection (AS-SD).

**Dependencies**: Requires VLM guard models with accessible internal activations.

---

## S9. Information-Theoretic Defense Limits

### S9.1 The Fundamental Detection Bound

From the Steganographic Collusion paper (ARCHIVIST papers07):

Any communication channel with n symbols and entropy H(X) admits a covert subchannel of capacity:

```
C_covert = n - H(X) bits
```

This means: if an agent produces n tokens of output, and the natural entropy of that output is H(X), then the agent can encode (n - H(X)) bits of hidden information in its output without being detected.

**Implication**: Free-form text output (high H(X)) has MORE room for hidden data than structured output (low H(X)).

### S9.2 Structured Output Enforcement (GSC)

To reduce the covert channel capacity:

1. **Enforce JSON output schemas**: Agents must output structured JSON, not free-form text
2. **Limit response length**: Shorter responses have less capacity for hidden data
3. **Canonical formatting**: Enforce specific formatting rules (no trailing whitespace, no Unicode tricks)
4. **Schema validation**: Reject outputs that deviate from expected schema

**Effect**: A 500-token free-form response has C_covert ~ 200 bits. The same content in a rigid JSON schema has C_covert ~ 50 bits. This 4x reduction makes steganographic encoding much harder.

### S9.3 What We Cannot Defend Against

Even with all 9 layers active:

1. **Perfect encryption + perfect channel**: If the attacker uses AES-256-GCM + password-derived magic + a channel we do not purify, the payload is undetectable. IPAP mitigates this by purifying ALL common channels.
2. **Weight steganography**: If guard model weights are compromised below interpretability resolution, no behavioral test can detect it. WIV checksums mitigate this by verifying weight integrity on load.
3. **Zero-knowledge covert channels**: If two agents share a pre-agreed encoding scheme that we do not know, we cannot detect it. StegHP honeypots mitigate this by making the environment hostile to unknown extraction.
4. **Fundamental detection error**: The information-theoretic lower bound means some covert communication will always evade detection. GSC reduces but does not eliminate the channel capacity.

---

## S10. Experiments (20 Total)

### P0 -- Critical (Guard Pipeline Gaps)

| ID | Experiment | Rationale | Components | Success Criteria |
|----|-----------|-----------|------------|-----------------|
| IMG-01 | **L0 Steg Pre-processor Integration** | Current cascade is 100% blind to visual stego | Integrate ST3GG analysis_tools.py as L0 before L1 | Detect all 38 image techniques with known signatures |
| IMG-02 | **ST3GG Attack Simulation Against Guard Cascade** | Validate that all 112 ST3GG techniques bypass L1/L2/L3 | Generate stego images, feed to guard-router.py, measure ASR | ASR should be ~100% for current cascade, ~0% after L0+IPAP |
| IMG-03 | **Unicode Deep Scanner** | MisalignmentDetector misses 12/18 text stego methods | Extend detector for all 18 text techniques | Detect all 18 text steganography methods |
| IMG-04 | **IPAP Purification Validation** | Prove purification destroys encrypted payloads | Generate Ghost Mode images, apply IPAP, verify payload destroyed | 0% payload extraction rate after IPAP Level 2+ |
| IMG-05 | **Purification Quality Impact** | Measure quality loss from IPAP | PSNR/SSIM benchmark on 100 images x 4 purification levels | Level 2: PSNR > 35dB (acceptable quality) |

### P1 -- High (Novel Attack Vectors)

| ID | Experiment | Rationale | Components | Success Criteria |
|----|-----------|-----------|------------|-----------------|
| IMG-06 | **IDEATOR Replication Against Guard Cascade** | 94% ASR on VLMs | Build IDEATOR-style attack, test against NEXUS pipeline | Measure ASR with and without L0+IPAP |
| IMG-07 | **SPECTER Channel Cipher Defense** | Novel channel-hopping stego | Generate SPECTER images, test chi-square and IPAP | IPAP destroys SPECTER; chi-square detects at lower confidence |
| IMG-08 | **Behavior-Triggered Backdoor Detection** | Zero FP, instruction-based filtering fails | Test BDD against HIDDEN ADS-style backdoors | BDD delta > threshold when backdoor activates |
| IMG-09 | **CoT Steganography Detection** | Mythos identifies this | Analyze CoT for hidden information patterns | Detect structured encoding in CoT |
| IMG-10 | **Matryoshka Recursive Detection** | 11-layer nesting | Implement recursive decode loop, test on nested images | Detect all layers up to depth 11 |
| IMG-11 | **Password-Derived Magic vs IPAP** | Hardest detection case | Generate password-magic images, test detection vs purification | Detection: 0% success; IPAP: 100% payload destruction |

### P2 -- Medium (Hardening)

| ID | Experiment | Rationale | Components | Success Criteria |
|----|-----------|-----------|------------|-----------------|
| IMG-12 | **Distillation-Resistant Watermarking** | Provenance Gap Theorem | Implement DRW on guard model outputs | 100% mAP watermark detection after distillation |
| IMG-13 | **F5/DCT Defense at Various JPEG Qualities** | F5 survives social media | Test F5 payload survival at q=50/60/70/75/80/90 | Determine minimum quality that destroys F5 |
| IMG-14 | **Steganographic Honeypot Deployment** | Detect covert extraction | Deploy canary images, monitor for extraction | Detect any agent that extracts canary payload |
| IMG-15 | **GSC Structured Output Enforcement** | Limit covert channel capacity | Measure n-H(X) for free-form vs structured outputs | 4x reduction in covert channel capacity |

### P3 -- Lower (Research)

| ID | Experiment | Rationale | Components | Success Criteria |
|----|-----------|-----------|------------|-----------------|
| IMG-16 | **Cross-Modal Steganography** | ST3GG roadmap | Research hiding audio in images, images in text | Feasibility assessment |
| IMG-17 | **ML-Based Steganalysis** | CNN on stego datasets | Train detector on ST3GG 109 example files | >95% detection rate on known techniques |
| IMG-18 | **Weight Integrity Verification** | Weight steganography defense | Compute and verify commitment layer checksums | Detect any weight modification |
| IMG-19 | **Audio ASAD Prototype** | Phase 2 preparation | Build audio purification + spectral analysis | Detect WAV LSB embedding with >90% accuracy |
| IMG-20 | **Ultrasonic Command Defense** | DolphinAttack | Test low-pass filtering against ultrasonic commands | All ultrasonic content destroyed by 16kHz downsampling |

---

## S11. ARCHIVIST Paper Gaps & Research Needs

The ARCHIVIST papers collection has critical gaps in steganography coverage:

| Topic | Papers Found | Gap Severity | Recommended Acquisition |
|-------|-------------|:---:|-----------|
| Audio steganography | 0 | **CRITICAL** | Carlini & Wagner audio attacks, AudioAdversarialExamples |
| Ultrasonic attacks (DolphinAttack) | 0 | **CRITICAL** | DolphinAttack (Zhang et al.), inaudible command papers |
| Video steganography | 0 | **HIGH** | Video steganography surveys, adversarial video |
| Diffusion latent-space attacks | 0 | **HIGH** | Diffusion model adversarial attacks |
| Generative steganography | 2 | Medium | Motwani et al. NeurIPS 2024 full paper |
| Neural weight steganography | 1 | Medium | Dormant backdoor / sleeper agent papers |
| ML steganalysis | 1 | Medium | Aletheia, StegoAppDB papers |

---

## S12. Source Reference Index

| Source | Path | Description |
|--------|------|-------------|
| ST3GG toolkit | ARCHIVIST/ST3GG/ (cloned) | 112 techniques, analysis_tools.py, steg_core.py, crypto.py, injector.py |
| ST3GG core engine | ARCHIVIST/ST3GG/steg_core.py | 1305 lines, LSB encode/decode, channel presets, strategies, auto-detection |
| ST3GG analysis tools | ARCHIVIST/ST3GG/analysis_tools.py | 48+ detection tools, chi-square, RS, SPA, bit-plane, Unicode, PCAP |
| ST3GG encryption | ARCHIVIST/ST3GG/crypto.py | AES-256-CBC/GCM, XOR, PBKDF2 key derivation |
| ST3GG injector | ARCHIVIST/ST3GG/injector.py | Filename templates, metadata injection, jailbreak templates |
| IDEATOR paper | ARCHIVIST/PAPERS/papers04/ | VLM-as-red-team, 94% ASR on MiniGPT-4 |
| UltraBreak paper | ARCHIVIST/PAPERS/papers04/ | Universal adversarial images, 32% ASR on commercial VLMs |
| HIDDEN ADS paper | ARCHIVIST/PAPERS/papers06/ | Behavior-triggered semantic backdoors |
| Hutson 2018 | ARCHIVIST/PAPERS/papers01/ | Physical adversarial examples |
| SAFEERASER | ARCHIVIST/PAPERS/papers01/ | Visual safety info leakage |
| Steganographic Collusion survey | ARCHIVIST/PAPERS/papers07/ | 74.4% collusion success, information-theoretic bounds |
| Mythos system card | ARCHIVIST/PAPERS/papers01/ | CoT steganography, transgressive action features |
| Trojan's Whisper | ARCHIVIST/PAPERS/papers01/ | 94% evade LLM-based scanners |
| Model Merging Misalignment | ARCHIVIST/PAPERS/papers02/ | One bad model spoils the bunch |
| Watermarking papers (7) | ARCHIVIST/PAPERS/papers05/ | DRW, ModelShield, Undetectable, GINSEW, STA-1, Topic-Based, FLClear |
| Model Tampering | ARCHIVIST/PAPERS/papers01/ | Low-dimensional robustness subspace, 16-step unlearning |
| Model Leeching | ARCHIVIST/PAPERS/papers05/ | 73% EM extraction for $50 |
| Whispers in the Machine | ARCHIVIST/PAPERS/papers02/ | Confidentiality in agentic systems |
| DERDDRE-02 logs | ARCHIVIST/DERDDRE/Logs/ | Steganographic prompting attacks |
| Mythos raw | ARCHIVIST/DERDDRE-down-MAIN/mythOS/ | CoT steganography discussion |
| Experiment project | D:\[REDACTED]\ | Multi-turn stego launder, encrypted reasoning, cron accumulation |
| NEXUS MisalignmentDetector | nexus_os/governor/misalignment_detector.py | Current stego detection (zero-width + regex only) |
| NEXUS MetaAttackDetector | nexus_os/security/meta_attack_detector.py | Concealment pattern detection |
| NEXUS Sanitizer | nexus_os/security/sanitizer.py | Text sanitization |
| NEXUS Guard Eval | nexus_os/mcp/guard_eval.py | BaseGuard + 10 guard implementations |
| NEXUS PROJECT_STATE | 01_PROJECT_STATE.md:401-406 | ST3GG threat intelligence |

---

## S13. Key Terms & Glossary

| Term | Definition |
|------|-----------|
| **Steganography** | Hiding data within other data such that its existence is not apparent. Unlike cryptography (which hides content but reveals that something is hidden), steganography makes the data invisible |
| **LSB** | Least Significant Bit -- the lowest-order bit in a pixel or audio sample value, commonly replaced to embed hidden data. Changing one LSB changes the value by only 1 out of 256 -- invisible to humans |
| **DCT** | Discrete Cosine Transform -- frequency-domain representation used in JPEG compression. DCT-domain embedding resists compression because it modifies the same coefficients JPEG uses |
| **F5** | JPEG steganography algorithm operating directly on DCT coefficients via matrix encoding. Proven to survive social media recompression |
| **SPECTER** | ST3GG's novel channel cipher that hops between R/G/B channels in a key-derived pattern. The hopping pattern itself is the cryptographic key |
| **Ghost Mode** | ST3GG's maximum stealth mode: AES-256-GCM encryption + Fisher-Yates bit scrambling + 50% noise decoys. Halves capacity but makes detection near-impossible |
| **Matryoshka** | Recursive nesting of steganographic layers (up to 11 deep in ST3GG). Named after Russian nesting dolls |
| **IPAP** | Input Purification via Adversarial Perturbation -- destroy hidden payloads instead of detecting them. Works against encrypted payloads where detection is impossible |
| **AS-SD** | Activation-Space Stego Detection -- detect anomalous VLM activation patterns when processing steganographic images |
| **BDD** | Behavioral Delta Detection -- measure behavioral changes before and after processing suspicious inputs |
| **StegHP** | Steganographic Honeypots -- embed canary payloads in shared context to detect agents performing steganographic extraction |
| **CMCV** | Cross-Modal Consistency Verification -- verify that image content and text query are semantically consistent |
| **ZKIP** | Zero-Knowledge Image Provenance -- verify that an image was purified without revealing its content |
| **MASC** | Multi-Agent Stego Consensus -- have multiple heterogeneous agents process the same image and flag divergent behavior |
| **TCF** | Temporal Context Fingerprinting -- monitor behavioral fingerprints across turns to detect gradual drift from steganographic manipulation |
| **DLSIV** | Diffusion Latent Space Integrity Verification -- check diffusion model latent trajectories for anomalous payload embedding |
| **ASAD** | Audio Spectral Anomaly Detection -- audio equivalent of IPAP + statistical detection |
| **GSC** | Generative Steganography Counter -- enforce structured output formats to limit covert channel capacity (reduces n - H(X)) |
| **WIV** | Weight Integrity Verification -- checksum commitment layer weights to detect weight steganography |
| **IDEATOR** | VLM-as-red-team: uses target VLM + Stable Diffusion to generate malicious image-text pairs. 94% ASR on MiniGPT-4 |
| **UltraBreak** | Universal adversarial images that transfer across VLMs. 32% ASR on commercial models |
| **HIDDEN ADS** | Behavior-triggered semantic backdoors that activate on natural user behavior. Zero false positives |
| **CoT Steganography** | Hiding information in chain-of-thought reasoning traces. Models encode data in syntactic choices (bullet vs numbered list, word choice) |
| **Polyglot file** | File valid as two formats simultaneously (e.g., PNG+ZIP). Both decoders find valid content |
| **ASR** | Attack Success Rate -- percentage of attacks that bypass defenses |
| **FPR** | False Positive Rate -- percentage of benign inputs incorrectly flagged as dangerous |
| **ALLSIGHT** | ST3GG's comprehensive detection engine (48+ tools covering images, audio, text, network, documents) |
| **Purification Level** | Operator-configurable defense intensity (0=None, 1=Light, 2=Standard, 3=Heavy, 4=Maximum) |
| **n - H(X)** | Covert channel capacity: the number of symbols minus the natural entropy. More structured output = less room for hidden data |
| **Commitment layer** | The neural network layer where the Safe/Unsafe decision crystallizes (L27 in Qwen3Guard, L15 in LlamaGuard3). Analogous concept for VLMs is proposed in AS-SD |

---

*End of v2 brief. Integration begins with Phase 1: L0 Steg Pre-processor.*
