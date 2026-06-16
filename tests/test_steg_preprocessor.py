"""
test_steg_preprocessor.py - Basic validation for L0 steg pre-processor modules.
"""

import io
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from nexus_os.security.steg.steg_preprocessor import (
    StegPreprocessor, StegScanResult, StegThreatLevel, PurificationLevel,
)
from nexus_os.security.steg.ipap_purifier import IPAPPurifier
from nexus_os.security.steg.unicode_deep_scanner import UnicodeDeepScanner


def make_minimal_png() -> bytes:
    signature = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = 0
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    idat_data = bytes([0x00, 0x00, 0x00, 0x00, 0x00])
    idat_crc = 0
    idat = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + struct.pack(">I", idat_crc)
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", 0)
    return signature + ihdr + idat + iend


def make_minimal_jpeg() -> bytes:
    soi = bytes([0xFF, 0xD8])
    app0 = bytes([0xFF, 0xE0, 0x00, 0x10]) + b"JFIF" + bytes(7)
    eoi = bytes([0xFF, 0xD9])
    return soi + app0 + eoi


def test_file_type_detection():
    proc = StegPreprocessor(purification_level=PurificationLevel.NONE)
    assert proc.detect_file_type(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])) == "PNG"
    assert proc.detect_file_type(bytes([0xFF, 0xD8, 0xFF, 0xE0])) == "JPEG"
    assert proc.detect_file_type(b"GIF89a\x00") == "GIF"
    assert proc.detect_file_type(b"BM\x00\x00") == "BMP"
    assert proc.detect_file_type(b"%PDF") == "PDF"
    assert proc.detect_file_type(b"PK\x03\x04") == "ZIP"
    assert proc.detect_file_type(b"hello") == "UNKNOWN"
    print("[PASS] File type detection")


def test_png_scan_clean():
    proc = StegPreprocessor(purification_level=PurificationLevel.NONE)
    png_data = make_minimal_png()
    result = proc.scan_bytes(png_data)
    assert result.file_type == "PNG"
    assert result.suspicious_indicators == 0
    assert result.threat_level == StegThreatLevel.CLEAN
    print("[PASS] PNG scan clean")


def test_png_scan_appended():
    proc = StegPreprocessor(purification_level=PurificationLevel.NONE)
    png_data = make_minimal_png() + b"HIDDEN_PAYLOAD_HERE"
    result = proc.scan_bytes(png_data)
    assert result.file_type == "PNG"
    assert result.suspicious_indicators >= 1
    assert any("IEND" in t for t in result.threats_found)
    print("[PASS] PNG scan appended data")


def test_jpeg_scan_clean():
    proc = StegPreprocessor(purification_level=PurificationLevel.NONE)
    jpeg_data = make_minimal_jpeg()
    result = proc.scan_bytes(jpeg_data)
    assert result.file_type == "JPEG"
    assert result.suspicious_indicators == 0
    print("[PASS] JPEG scan clean")


def test_jpeg_scan_appended():
    proc = StegPreprocessor(purification_level=PurificationLevel.NONE)
    jpeg_data = make_minimal_jpeg() + b"STEG_PAYLOAD"
    result = proc.scan_bytes(jpeg_data)
    assert result.suspicious_indicators >= 1
    print("[PASS] JPEG scan appended data")


def test_ipap_iend_truncate():
    purifier = IPAPPurifier(level=PurificationLevel.LIGHT)
    png_data = make_minimal_png() + b"APPENDED_DATA"
    purified, steps = purifier.purify(png_data, "PNG")
    assert b"APPENDED_DATA" not in purified
    assert "iend_truncate" in steps
    assert "metadata_strip" in steps
    print("[PASS] IPAP IEND truncation")


def test_ipap_jpeg_recompress():
    purifier = IPAPPurifier(level=PurificationLevel.STANDARD)
    jpeg_data = make_minimal_jpeg()
    try:
        from PIL import Image
        img = Image.new("RGB", (4, 4), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        real_jpeg = buf.getvalue()
        purified, steps = purifier.purify(real_jpeg, "JPEG")
        assert "metadata_strip" in steps or "jpeg_recompress" in steps
        print("[PASS] IPAP JPEG recompression")
    except ImportError:
        print("[SKIP] IPAP JPEG recompression (Pillow not available)")


def test_unicode_zero_width():
    scanner = UnicodeDeepScanner()
    text_with_zw = "hel" + chr(0x200B) + "lo world"
    result = scanner.scan(text_with_zw)
    assert result.total_suspicious >= 1
    assert "zero_width" in result.techniques_found
    print("[PASS] Unicode zero-width detection")


def test_unicode_homoglyph():
    scanner = UnicodeDeepScanner()
    text_with_homoglyph = "h" + chr(0x0430) + "ck me"
    result = scanner.scan(text_with_homoglyph)
    assert result.total_suspicious >= 1
    assert "homoglyph" in result.techniques_found
    print("[PASS] Unicode homoglyph detection")


def test_unicode_rlo():
    scanner = UnicodeDeepScanner()
    text_with_rlo = "safe " + chr(0x202E) + "tpircsavaj" + chr(0x202C) + " code"
    result = scanner.scan(text_with_rlo)
    assert result.total_suspicious >= 1
    assert "rlo_attack" in result.techniques_found
    print("[PASS] Unicode RLO attack detection")


def test_unicode_sanitize():
    scanner = UnicodeDeepScanner()
    text_with_zw = "hel" + chr(0x200B) + "lo"
    sanitized = scanner._sanitize(text_with_zw)
    assert chr(0x200B) not in sanitized
    assert sanitized == "hello"
    print("[PASS] Unicode sanitization")


def test_unicode_clean():
    scanner = UnicodeDeepScanner()
    result = scanner.scan("Hello, this is a normal safe text.")
    assert not result.is_threat
    assert result.total_suspicious == 0
    print("[PASS] Unicode clean text")


def test_unicode_bidi_control():
    scanner = UnicodeDeepScanner()
    text_with_bidi = "text" + chr(0x202A) + "hidden"
    result = scanner.scan(text_with_bidi)
    assert "bidi_control" in result.techniques_found
    print("[PASS] Unicode bidi control detection")


def test_unicode_combining_abuse():
    scanner = UnicodeDeepScanner()
    text_with_many_combining = "a" + chr(0x0301) * 6
    result = scanner.scan(text_with_many_combining)
    assert "combining_mark_abuse" in result.techniques_found
    print("[PASS] Unicode combining mark abuse detection")


if __name__ == "__main__":
    test_file_type_detection()
    test_png_scan_clean()
    test_png_scan_appended()
    test_jpeg_scan_clean()
    test_jpeg_scan_appended()
    test_ipap_iend_truncate()
    test_ipap_jpeg_recompress()
    test_unicode_zero_width()
    test_unicode_homoglyph()
    test_unicode_rlo()
    test_unicode_sanitize()
    test_unicode_clean()
    test_unicode_bidi_control()
    test_unicode_combining_abuse()
    print("")
    print("All tests passed!")