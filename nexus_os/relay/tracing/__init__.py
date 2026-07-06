"""NEXUS-REASONS-DB tracing package.

Three-tier persistence (hot SQLite FTS, warm JSONL, cold ZSTD) wired through
`record.py`, with redaction baked in by `scrub.py` before any disk write.
"""
__version__ = "0.1.0"
