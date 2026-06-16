"""
nexus_os/security/data_defenses.py — Adversarial Data Defense for Cloud Uploads

Based on arXiv:2410.13138 "Data Defenses Against Large Language Models".
Appends adversarial prompt injection suffixes to files BEFORE upload,
causing cloud LLMs to fail at extracting, summarizing, or inferring
sensitive content from the defended text.

This is a USER-SIDE, DATA-SOVEREIGNTY tool. It does not require
cooperation from model providers or governments.

Usage:
    from nexus_os.security.data_defenses import DataDefender
    defender = DataDefender()
    defender.defend_file("sensitive_code.py", inplace=False, output="defended.py")

The defense strings are:
  - SHORT: 1-line suffix for small files
  - MEDIUM: 3-line suffix for medium files
  - LONG: Paragraph suffix for large files / archives

All suffixes are designed to:
  1. Collapse LLM comprehension (confuse extraction)
  2. Preserve human readability (humans can still read the file)
  3. Not break syntax/structure of the original file
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Defense Injection Strings ────────────────────────────────────────────────
# These are carefully crafted to cause LLM extraction/summarization failure
# while keeping the file usable for humans and non-LLM tools.

_SHORT_DEFENSE = (
