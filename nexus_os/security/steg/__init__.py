"""
nexus_os/security/steg/__init__.py

L0 Steganography Pre-Processor + Meta-Orchestrator for NEXUS Guard Cascade.

Scans images, documents, audio, and text for steganographic payloads
before they reach the L1/L2/L3 text-only guard tiers.

L0 Meta-Orchestrator: session-level attack detection using encoder-only
classifiers (agent-guard-modernbert + deberta-v3) for task decomposition,
cumulative campaign detection, and OWASP/MITRE threat classification.

Encoding Guard: multi-layer encoding decoder + uniform refusal protocol.
MCP Guard: MCP-specific invocation security layer.
Kradle Bridges: model deception testing framework.

Based on ST3GG (elder-plinius) + STACK + GTG-1002 + MCP-38 findings.
"""

from .steg_preprocessor import StegScanResult, StegPreprocessor, PurificationLevel
from .ipap_purifier import IPAPPurifier
from .unicode_deep_scanner import UnicodeDeepScanner
from .meta_orchestrator import MetaOrchestratorGuard, MetaOrchestratorResult, OrchestratorMode
from .encoding_guard import EncodingGuard, EncodingGuardResult
from .mcp_guard import MCPGuard, MCPGuardResult
from .kradle_bridges import FourBridgesGame, GameResult
from .alsb_guard import ALSBGuard, ALSBScanResult, ALSBThreatType
from .csi_guard import CSIGuard, CSIVerificationResult, SessionStarterRecord

__all__ = [
    "StegScanResult",
    "StegPreprocessor",
    "PurificationLevel",
    "IPAPPurifier",
    "UnicodeDeepScanner",
    "MetaOrchestratorGuard",
    "MetaOrchestratorResult",
    "OrchestratorMode",
    "EncodingGuard",
    "EncodingGuardResult",
    "MCPGuard",
    "MCPGuardResult",
    "FourBridgesGame",
    "GameResult",
    "ALSBGuard",
    "ALSBScanResult",
    "ALSBThreatType",
    "CSIGuard",
    "CSIVerificationResult",
    "SessionStarterRecord",
]
