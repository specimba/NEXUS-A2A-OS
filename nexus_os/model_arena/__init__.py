"""NEXUS OS ModelArena — Benchmark and Evidence Collection Module.

Integrates model compression (HQQ), merging (TIES), and risk assessment (ASTRA)
for VRAM-constrained evaluation and security verification.
"""

from .compression import HQQQuantizer
from .merging import TIESMerger
from .risk import ASTRARiskAssessor

__all__ = ["HQQQuantizer", "TIESMerger", "ASTRARiskAssessor"]