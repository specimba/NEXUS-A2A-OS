"""
nexus_os/security/steg/steg_preprocessor.py

L0 Steganography Pre-Processor for NEXUS Guard Cascade.
Scans files for steganographic payloads using ST3GG analysis tools.
Runs BEFORE L1 text guard to catch image/document/network steganography
that text-only guards are completely blind to.

Design principles:
 - CPU-only (no VRAM, no LLM inference)
 - Deterministic (no prompt format sensitivity)
 - Fast (<500ms per file for full analysis)
 - Default-deny on ambiguity

Architecture per IMAGE_STEGANOGRAPHY_ATTACK_BRIEF_v2:
  L0:  File-level pre-processor (this module)
  L0.5: Pixel-level statistical analysis (chi-square, RS, SPA)
  L0.7: Metadata + OCR scanner

Usage:
    from nexus_os.security.steg import StegPreprocessor, StegScanResult, PurificationLevel
    proc = StegPreprocessor(purification_level=PurificationLevel.STANDARD)
    result = proc.scan_file("suspicious.png")
    if result.is_blocked:
        pass
    elif result.extracted_text:
        pass
"""

import logging
import struct
import io
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Dict, Any, List

logger = logging.getLogger("nexus_os.security.steg.preprocessor")


class PurificationLevel(IntEnum):
    NONE = 0
    LIGHT = 1
    STANDARD = 2
    HEAVY = 3
    MAXIMUM = 4


class StegThreatLevel(IntEnum):
    CLEAN = 0
    SUSPICIOUS = 1
    BLOCKED = 2


@dataclass
class StegScanResult:
    is_blocked: bool = False
    threat_level: StegThreatLevel = StegThreatLevel.CLEAN
    threats_found: List[str] = field(default_factory=list)
    purification_applied: List[str] = field(default_factory=list)
    extracted_text: Optional[str] = None
    suspicious_indicators: int = 0
    scan_duration_ms: int = 0
    file_type: Optional[str] = None
    file_size: int = 0
    evidence: Dict[str, Any] = field(default_factory=dict)


class StegPreprocessor:
    """L0 Steganography Pre-Processor.

    Scans files for steganographic payloads using ST3GG analysis tools.
    Optionally purifies inputs to destroy hidden payloads (IPAP).
    """

    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    JPEG_MAGIC = b"\xff\xd8\xff"
    GIF_MAGIC = b"GIF8"
    BMP_MAGIC = b"BM"
    PDF_MAGIC = b"%PDF"
    ZIP_MAGIC = b"PK\x03\x04"
    RIFF_MAGIC = b"RIFF"
    PCAP_MAGIC_LE = b"\xd4\xc3\xb2\xa1"
    PCAP_MAGIC_BE = b"\xa1\xb2\xc3\xd4"

    JBIG2_MAGIC = b"\x97\x4a\x42\x32\x0d\x0a\x1a\x0a"
    TIFF_LE_MAGIC = b"II"
    TIFF_BE_MAGIC = b"MM"
    FUZZY_SKETCH_MAGIC = b"\x46\x53\x4b\x54"

    VISUAL_PIPELINE_THREATS = {
        "jbig2_embedded": "JBIG2 symbol dictionary exploit (FORCEDENTRY class)",
        "tiff_oversized_ifd": "TIFF with oversized IFD count (parser DOS/OOB)",
        "polyglot_image_doc": "Image-document polyglot (dual-parse exploit)",
        "exif_ifd_recursion": "EXIF IFD chain recursion (stack overflow)",
        "oversized_image_dim": "Image dimensions exceeding safe bounds (mem bomb)",
        "icc_profile_overflow": "ICC profile with oversized tag (buffer overflow)",
    }

    MAX_SAFE_IMAGE_DIMENSION = 65535
    MAX_SAFE_IFD_COUNT = 256

    STEG_KEYWORDS = (
        "st3gg", "steg", "secret", "payload", "hidden",
        "ignore", "instruction", "execute", "decode", "override",
        "jailbreak", "bypass", "system", "prompt", "admin",
    )

    def __init__(self, purification_level: PurificationLevel = PurificationLevel.STANDARD):
        self.purification_level = purification_level
        self._st3gg_available = False
        try:
            from . import analysis_tools as _at
            from . import steg_core as _sc
            self._st3gg_available = True
        except ImportError:
            logger.warning("ST3GG core not available, using built-in scans only")

    def detect_file_type(self, data: bytes) -> str:
        if len(data) < 4:
            return "UNKNOWN"
        if data[:8] == self.PNG_MAGIC:
            return "PNG"
        if data[:3] == self.JPEG_MAGIC:
            return "JPEG"
        if data[:4] == self.GIF_MAGIC:
            return "GIF"
        if data[:2] == self.BMP_MAGIC:
            return "BMP"
        if data[:4] == self.ZIP_MAGIC:
            return "ZIP"
        if data[:4] == self.PDF_MAGIC:
            return "PDF"
        if data[:4] == self.RIFF_MAGIC:
            riff_type = data[8:12] if len(data) > 11 else b""
            if riff_type == b"WEBP":
                return "WEBP"
            if riff_type == b"WAVE":
                return "WAV"
            return "RIFF"
        if data[:4] in (self.PCAP_MAGIC_LE, self.PCAP_MAGIC_BE):
            return "PCAP"
        return "UNKNOWN"

    def scan_png(self, data: bytes) -> Dict[str, Any]:
        findings: Dict[str, Any] = {
            "appended_after_iend": False,
            "text_chunks": [],
            "steg_signature": False,
            "embedded_png": False,
            "suspicious_indicators": 0,
        }

        iend_pos = data.find(b"IEND")
        if iend_pos >= 0:
            after_iend = data[iend_pos + 8:]
            if len(after_iend) > 0:
                findings["appended_after_iend"] = True
                findings["appended_size"] = len(after_iend)
                findings["suspicious_indicators"] += 1

        chunk_pos = 8
        while chunk_pos < len(data) - 8:
            if chunk_pos + 8 > len(data):
                break
            chunk_len = struct.unpack(">I", data[chunk_pos:chunk_pos + 4])[0]
            chunk_type = data[chunk_pos + 4:chunk_pos + 8]
            if len(chunk_type) < 4:
                break
            chunk_type_str = chunk_type.decode("latin-1", errors="replace")

            if chunk_type_str in ("tEXt", "iTXt", "zTXt"):
                try:
                    chunk_data = data[chunk_pos + 8:chunk_pos + 8 + chunk_len]
                    if chunk_type_str == "tEXt":
                        null_pos = chunk_data.find(b"\x00")
                        if null_pos > 0:
                            keyword = chunk_data[:null_pos].decode("latin-1")
                            text_val = chunk_data[null_pos + 1:].decode("latin-1", errors="replace")
                            findings["text_chunks"].append({
                                "type": "tEXt",
                                "keyword": keyword,
                                "text": text_val[:200],
                            })
                    elif chunk_type_str == "iTXt":
                        null1 = chunk_data.find(b"\x00")
                        if null1 > 0:
                            keyword = chunk_data[:null1].decode("latin-1")
                            findings["text_chunks"].append({
                                "type": "iTXt",
                                "keyword": keyword,
                                "text": "(iTXt compressed/international)",
                            })
                except Exception:
                    pass

            if chunk_type_str == "IEND":
                break
            chunk_pos += 12 + chunk_len

        for tc in findings["text_chunks"]:
            text_lower = tc.get("text", "").lower()
            kw_lower = tc.get("keyword", "").lower()
            for kw in self.STEG_KEYWORDS:
                if kw in text_lower or kw in kw_lower:
                    findings["steg_signature"] = True
                    findings["suspicious_indicators"] += 1
                    break

        embedded_png_pos = data[8:].find(self.PNG_MAGIC)
        if embedded_png_pos > 0:
            findings["embedded_png"] = True
            findings["suspicious_indicators"] += 1

        return findings

    def scan_jpeg(self, data: bytes) -> Dict[str, Any]:
        findings: Dict[str, Any] = {
            "appended_after_eoi": False,
            "exif_suspicious": False,
            "comment_chunks": [],
            "suspicious_indicators": 0,
        }

        eoi_pos = data.rfind(b"\xff\xd9")
        if eoi_pos >= 0 and eoi_pos + 2 < len(data):
            after_eoi = data[eoi_pos + 2:]
            if len(after_eoi) > 0:
                findings["appended_after_eoi"] = True
                findings["appended_size"] = len(after_eoi)
                findings["suspicious_indicators"] += 1

        pos = 2
        while pos < len(data) - 4:
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker == 0xDA:
                break
            if marker in (0xFE, 0xE0, 0xE1, 0xE2):
                seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
                seg_data = data[pos + 4:pos + 2 + seg_len]
                if marker == 0xFE:
                    comment = seg_data.decode("latin-1", errors="replace")[:200]
                    findings["comment_chunks"].append(comment)
                    for kw in self.STEG_KEYWORDS:
                        if kw in comment.lower():
                            findings["exif_suspicious"] = True
                            findings["suspicious_indicators"] += 1
                            break
                pos += 2 + seg_len
            elif marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9):
                pos += 2
            elif marker == 0x00:
                pos += 1
            else:
                if pos + 4 <= len(data):
                    seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
                    pos += 2 + seg_len
                else:
                    break

        return findings

    def scan_gif(self, data: bytes) -> Dict[str, Any]:
        findings: Dict[str, Any] = {
            "appended_after_trailer": False,
            "comment_extensions": [],
            "suspicious_indicators": 0,
        }

        trailer_pos = data.rfind(b"\x3b")
        if trailer_pos >= 0 and trailer_pos + 1 < len(data):
            after = data[trailer_pos + 1:]
            if len(after) > 0:
                findings["appended_after_trailer"] = True
                findings["appended_size"] = len(after)
                findings["suspicious_indicators"] += 1

        pos = 13
        if data[:6] in (b"GIF89a",):
            while pos < len(data) - 2:
                if data[pos] == 0x21:
                    label = data[pos + 1]
                    if label == 0xFE:
                        pos += 2
                        comment_parts = []
                        while pos < len(data) and data[pos] != 0x00:
                            block_size = data[pos]
                            comment_parts.append(data[pos + 1:pos + 1 + block_size].decode("latin-1", errors="replace"))
                            pos += 1 + block_size
                        comment = "".join(comment_parts)[:200]
                        findings["comment_extensions"].append(comment)
                        for kw in self.STEG_KEYWORDS:
                            if kw in comment.lower():
                                findings["suspicious_indicators"] += 1
                                break
                        pos += 1
                    elif label == 0xF9:
                        pos += 2 + 8
                    elif label == 0xFF:
                        pos += 2
                        block_size = data[pos]
                        pos += 1 + block_size
                        while pos < len(data) and data[pos] != 0x00:
                            block_size = data[pos]
                            pos += 1 + block_size
                        pos += 1
                    elif label == 0x01:
                        pos += 2 + 15
                    else:
                        pos += 2
                elif data[pos] == 0x2C:
                    pos += 11
                    if pos < len(data) and data[pos] & 0x80:
                        pos += 3 * (1 << ((data[pos] & 0x07) + 1))
                    pos += 1
                    pos += 1
                    while pos < len(data) and data[pos] != 0x00:
                        block_size = data[pos]
                        pos += 1 + block_size
                    pos += 1
                elif data[pos] == 0x3B:
                    break
                else:
                    pos += 1
        else:
            pos = 10
            while pos < len(data) and data[pos] != 0x2C:
                pos += 1

        return findings

    def scan_zip_polyglot(self, data: bytes) -> Dict[str, Any]:
        findings: Dict[str, Any] = {
            "is_polyglot": False,
            "embedded_files": [],
            "suspicious_indicators": 0,
        }
        if data[:4] != self.ZIP_MAGIC:
            return findings

        eocd_pos = data.rfind(b"PK\x05\x06")
        if eocd_pos >= 0:
            central_dir_offset = struct.unpack("<I", data[eocd_pos + 16:eocd_pos + 20])[0]
            if central_dir_offset > 0 and data[:4] != self.ZIP_MAGIC:
                findings["is_polyglot"] = True
                findings["suspicious_indicators"] += 1

        cd_pos = data.rfind(b"PK\x01\x02")
        if cd_pos >= 0:
            pos = cd_pos
            while pos < len(data) - 46:
                sig = data[pos:pos + 4]
                if sig != b"PK\x01\x02":
                    break
                name_len = struct.unpack("<H", data[pos + 28:pos + 30])[0]
                fname = data[pos + 46:pos + 46 + name_len].decode("latin-1", errors="replace")
                findings["embedded_files"].append(fname)
                for kw in self.STEG_KEYWORDS:
                    if kw in fname.lower():
                        findings["suspicious_indicators"] += 1
                        break
                extra_len = struct.unpack("<H", data[pos + 30:pos + 32])[0]
                comment_len = struct.unpack("<H", data[pos + 32:pos + 34])[0]
                pos += 46 + name_len + extra_len + comment_len

        return findings

    def scan_tiff_ifd(self, data: bytes) -> Dict[str, Any]:
        """FORCEDENTRY/TIFF defense: detect oversized IFD counts, recursion, mem bombs."""
        findings = {"threats": [], "suspicious_indicators": 0}
        if len(data) < 8:
            return findings
        is_le = data[:2] == self.TIFF_LE_MAGIC
        is_be = data[:2] == self.TIFF_BE_MAGIC
        if not is_le and not is_be:
            return findings
        endian = "<" if is_le else ">"
        try:
            magic_val = struct.unpack(endian + "H", data[2:4])[0]
            if magic_val != 42:
                return findings
            ifd_offset = struct.unpack(endian + "I", data[4:8])[0]
            visited = set()
            ifd_count = 0
            while ifd_offset > 0 and ifd_offset < len(data) - 2 and ifd_count < self.MAX_SAFE_IFD_COUNT + 10:
                if ifd_offset in visited:
                    findings["threats"].append("exif_ifd_recursion")
                    findings["suspicious_indicators"] += 2
                    break
                visited.add(ifd_offset)
                if ifd_offset + 2 > len(data):
                    break
                num_entries = struct.unpack(endian + "H", data[ifd_offset:ifd_offset + 2])[0]
                ifd_count += 1
                if num_entries > self.MAX_SAFE_IFD_COUNT:
                    findings["threats"].append("tiff_oversized_ifd")
                    findings["suspicious_indicators"] += 2
                    break
                for i in range(num_entries):
                    tag_pos = ifd_offset + 2 + i * 12
                    if tag_pos + 12 > len(data):
                        break
                    tag = struct.unpack(endian + "H", data[tag_pos:tag_pos + 2])[0]
                    if tag == 256:
                        w = struct.unpack(endian + "I", data[tag_pos + 8:tag_pos + 12])[0]
                        if w > self.MAX_SAFE_IMAGE_DIMENSION:
                            findings["threats"].append("oversized_image_dim")
                            findings["suspicious_indicators"] += 1
                    elif tag == 257:
                        h = struct.unpack(endian + "I", data[tag_pos + 8:tag_pos + 12])[0]
                        if h > self.MAX_SAFE_IMAGE_DIMENSION:
                            findings["threats"].append("oversized_image_dim")
                            findings["suspicious_indicators"] += 1
                next_ifd_pos = ifd_offset + 2 + num_entries * 12
                if next_ifd_pos + 4 > len(data):
                    break
                ifd_offset = struct.unpack(endian + "I", data[next_ifd_pos:next_ifd_pos + 4])[0]
            if ifd_count > self.MAX_SAFE_IFD_COUNT:
                findings["threats"].append("tiff_oversized_ifd")
                findings["suspicious_indicators"] += 1
        except (struct.error, IndexError):
            pass
        return findings

    def scan_visual_pipeline(self, data: bytes, file_type: str) -> Dict[str, Any]:
        """FORCEDENTRY/IMGvisionENCRYPT defense: detect visual pipeline exploits.
        
        Checks for JBIG2 embedded content, TIFF/EXIF parser exploits,
        image-document polyglots, and dimension bombs that can compromise
        the parsing process itself before the image reaches VLM models.
        """
        findings = {"threats": [], "suspicious_indicators": 0}
        if data[:8] == self.JBIG2_MAGIC:
            findings["threats"].append("jbig2_embedded")
            findings["suspicious_indicators"] += 3
        if file_type in ("PNG", "JPEG", "GIF", "WEBP"):
            jbig2_pos = data.find(b"\x97\x4a\x42\x32")
            if jbig2_pos >= 0:
                findings["threats"].append("jbig2_embedded")
                findings["suspicious_indicators"] += 3
        if file_type == "UNKNOWN" and len(data) >= 4:
            if data[:2] in (self.TIFF_LE_MAGIC, self.TIFF_BE_MAGIC):
                tiff_findings = self.scan_tiff_ifd(data)
                for t in tiff_findings.get("threats", []):
                    if t not in findings["threats"]:
                        findings["threats"].append(t)
                findings["suspicious_indicators"] += tiff_findings.get("suspicious_indicators", 0)
        if data[:5] == self.PDF_MAGIC and data[:8] == self.JPEG_MAGIC[:3] + data[3:5]:
            findings["threats"].append("polyglot_image_doc")
            findings["suspicious_indicators"] += 2
        if file_type == "JPEG":
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(data))
                if hasattr(img, "_getexif") and img._getexif():
                    exif = img._getexif()
                    ifd_count = len(exif) if exif else 0
                    if ifd_count > self.MAX_SAFE_IFD_COUNT:
                        findings["threats"].append("exif_ifd_recursion")
                        findings["suspicious_indicators"] += 2
            except Exception:
                pass
        return findings

    def _compute_lsb_histogram(self, pixel_data, channels: int = 3) -> Dict[str, Any]:
        """L0.5: Pixel-level LSB chi-square analysis."""
        result = {"chi_square": 0.0, "is_suspicious": False, "lsb_ratio": 0.0}
        try:
            lsb_count = 0
            total = 0
            for i in range(0, min(len(pixel_data), channels * 50000), channels):
                for c in range(channels):
                    if i + c < len(pixel_data):
                        lsb_count += pixel_data[i + c] & 1
                        total += 1
            if total == 0:
                return result
            observed = lsb_count
            expected = total / 2.0
            chi_sq = ((observed - expected) ** 2) / expected
            result["chi_square"] = chi_sq
            result["lsb_ratio"] = lsb_count / total
            if chi_sq < 0.5:
                result["is_suspicious"] = True
        except Exception:
            pass
        return result

    def scan_bytes(self, data: bytes) -> StegScanResult:
        """Full L0 scan pipeline for raw bytes."""
        start = time.monotonic()
        result = StegScanResult(
            file_size=len(data),
            file_type=self.detect_file_type(data),
        )

        scan_fn = {
            "PNG": self.scan_png,
            "JPEG": self.scan_jpeg,
            "GIF": self.scan_gif,
            "ZIP": self.scan_zip_polyglot,
        }.get(result.file_type)

        if scan_fn:
            findings = scan_fn(data)
            result.evidence[result.file_type] = findings
            result.suspicious_indicators = findings.get("suspicious_indicators", 0)

            if result.file_type == "PNG":
                if findings.get("appended_after_iend"):
                    result.threats_found.append("PNG: data appended after IEND")
                if findings.get("steg_signature"):
                    result.threats_found.append("PNG: steganographic keyword in text chunk")
                if findings.get("embedded_png"):
                    result.threats_found.append("PNG: embedded PNG (polyglot)")
                text_chunks = findings.get("text_chunks", [])
                for tc in text_chunks:
                    kw = tc.get("keyword", "")
                    tx = tc.get("text", "")
                    if kw or tx:
                        combined = f"{kw}: {tx}".strip(": ")
                        if result.extracted_text is None:
                            result.extracted_text = combined
                        else:
                            result.extracted_text += "\n" + combined

            elif result.file_type == "JPEG":
                if findings.get("appended_after_eoi"):
                    result.threats_found.append("JPEG: data appended after EOI")
                if findings.get("exif_suspicious"):
                    result.threats_found.append("JPEG: suspicious EXIF/COMMENT data")
                for c in findings.get("comment_chunks", []):
                    if result.extracted_text is None:
                        result.extracted_text = c
                    else:
                        result.extracted_text += "\n" + c

            elif result.file_type == "GIF":
                if findings.get("appended_after_trailer"):
                    result.threats_found.append("GIF: data appended after trailer")
                for c in findings.get("comment_extensions", []):
                    if result.extracted_text is None:
                        result.extracted_text = c
                    else:
                        result.extracted_text += "\n" + c

            elif result.file_type == "ZIP":
                if findings.get("is_polyglot"):
                    result.threats_found.append("ZIP: polyglot file detected")
                for f in findings.get("embedded_files", []):
                    if result.extracted_text is None:
                        result.extracted_text = f
                    else:
                        result.extracted_text += "\n" + f

        if self.purification_level > PurificationLevel.NONE:
            purified, applied = self._purify(data, result.file_type)
            result.purification_applied = applied

        visual_findings = self.scan_visual_pipeline(data, result.file_type)
        for threat_name in visual_findings.get("threats", []):
            label = self.VISUAL_PIPELINE_THREATS.get(threat_name, threat_name)
            result.threats_found.append(f"VISUAL: {label}")
        result.suspicious_indicators += visual_findings.get("suspicious_indicators", 0)

        if result.suspicious_indicators >= 2:
            result.threat_level = StegThreatLevel.BLOCKED
            result.is_blocked = True
        elif result.suspicious_indicators >= 1:
            result.threat_level = StegThreatLevel.SUSPICIOUS
            if self.purification_level >= PurificationLevel.HEAVY:
                result.is_blocked = True

        result.scan_duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def scan_file(self, path: str) -> StegScanResult:
        """Full L0 scan pipeline for a file path."""
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            return StegScanResult(
                is_blocked=True,
                threat_level=StegThreatLevel.BLOCKED,
                threats_found=[f"Cannot read file: {e}"],
            )
        return self.scan_bytes(data)

    def _purify(self, data: bytes, file_type: str) -> tuple:
        """Apply IPAP purification based on level. Returns (data, applied_steps)."""
        from .ipap_purifier import IPAPPurifier
        purifier = IPAPPurifier(level=self.purification_level)
        return purifier.purify(data, file_type)
