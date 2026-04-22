#!/usr/bin/env python3
"""Compatibility wrapper for the canonical GMR test builder."""

from __future__ import annotations

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("build_gmr_tests.py")),
        run_name="__main__",
    )
