"""
mem0_adapter.py — Legacy import shim redirecting to memory_adapter.py
"""

from nexus_os.vault.memory_adapter import Mem0Adapter, get_adapter

__all__ = ["Mem0Adapter", "get_adapter"]
