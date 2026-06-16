"""Relay Mode — Strict (real) vs Frontier (mock) dual-mode enum."""

from __future__ import annotations
from enum import Enum


class RelayMode(Enum):
    STRICT = "strict"
    FRONTIER = "frontier"

    @property
    def is_strict(self) -> bool:
        return self == RelayMode.STRICT

    @property
    def is_frontier(self) -> bool:
        return self == RelayMode.FRONTIER
