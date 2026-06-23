"""NEXUSCLAW Runtime Security Integration - TerminalSanitizer wiring for all agent I/O.

This module provides the runtime integration points for TerminalSanitizer,
AgentPTY, and VerifiableOutput as specified in MASTER_PLAN Phase 0.

Components integrated:
- TaskRouter: sanitize agent output before passing to other agents
- MessagingHub: sanitize inter-agent messages before delivery
- Runner: sanitize agent output in heartbeat/daemon sync
- Coordinator: sanitize brainstorm/brainstorm output
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from nexus_os.security.sanitizer import TerminalSanitizer, VerifiableOutput

logger = logging.getLogger("nexusclaw.runtime_security")

# ── Global Configuration ──────────────────────────────────────────────
# SOVEREIGN mode disabled by default per MASTER_PLAN Phase 0.2
SOVEREIGN_MODE_ENABLED = os.getenv("NEXUS_SOVEREIGN_ENABLED", "false").lower() == "true"
SANITIZATION_ENABLED = os.getenv("NEXUS_SANITIZATION_ENABLED", "true").lower() == "true"
PTY_ISOLATION_ENABLED = os.getenv("NEXUS_PTY_ISOLATION_ENABLED", "true").lower() == "true"

# Singleton sanitizer instances
_sanitizer = TerminalSanitizer()
_verifiable_output_cls = VerifiableOutput


# ── Core Sanitization Functions ──────────────────────────────────────

def sanitize_agent_output(content: str, source_agent: str = "", target_agent: str = "") -> str:
    """Sanitize agent output before passing to another agent or system.
    
    Args:
        content: Raw agent output
        source_agent: Source agent identifier (for logging)
        target_agent: Target agent identifier (for logging)
        
    Returns:
        Sanitized output safe for inter-agent consumption
    """
    if not SANITIZATION_ENABLED:
        return content
    
    if not content:
        return content
    
    # Check for escape sequences
    if _sanitizer.contains_escape(content):
        logger.warning(
            "TerminalSanitizer triggered: escape sequences detected in output from %s → %s",
            source_agent, target_agent
        )
    
    sanitized = _sanitizer.sanitize(content)
    
    if sanitized != content:
        logger.info(
            "Output sanitized: %s → %s (removed %d chars)",
            source_agent, target_agent, len(content) - len(sanitized)
        )
    
    return sanitized


def create_verifiable_output(
    content: str,
    source: str = "",
    target: str = "",
    signing_key: str = ""
) -> VerifiableOutput:
    """Create a verifiable output envelope for cross-agent communication."""
    vo = _verifiable_output_cls(content, source=source, target=target)
    if signing_key:
        vo.sign(signing_key)
    return vo


def verify_verifiable_output(vo: VerifiableOutput, signing_key: str = "") -> bool:
    """Verify a verifiable output envelope."""
    return vo.verify(signing_key)


def sanitize_inter_agent_message(message: Dict[str, Any], source: str = "", target: str = "") -> Dict[str, Any]:
    """Sanitize a message being sent between agents."""
    if not SANITIZATION_ENABLED:
        return message
    
    sanitized = dict(message)
    
    # Sanitize text content fields
    text_fields = ["content", "text", "message", "body", "description"]
    for field in text_fields:
        if field in sanitized and sanitized[field]:
            sanitized[field] = sanitize_agent_output(
                str(sanitized[field]), 
                source=source, 
                target=target
            )
    
    return sanitized


def check_sovereign_mode() -> bool:
    """Check if SOVEREIGN mode is enabled (should be False by default)."""
    return SOVEREIGN_MODE_ENABLED


def get_runtime_security_config() -> Dict[str, bool]:
    """Get current runtime security configuration."""
    return {
        "sovereign_mode": SOVEREIGN_MODE_ENABLED,
        "sanitization": SANITIZATION_ENABLED,
        "pty_isolation": PTY_ISOLATION_ENABLED,
    }


# ── Mixin Classes for Easy Integration ────────────────────────────────

class SanitizedOutputMixin:
    """Mixin to add output sanitization to any agent runner/component."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source_agent_id = getattr(self, 'agent_id', 'unknown')
    
    def _sanitize_for_agent(self, content: str, target_agent: str = "") -> str:
        """Sanitize output before sending to another agent."""
        return sanitize_agent_output(content, self._source_agent_id, target_agent)
    
    def _create_verifiable(self, content: str, target: str = "", signing_key: str = "") -> VerifiableOutput:
        """Create verifiable output envelope."""
        return create_verifiable_output(content, self._source_agent_id, target, signing_key)


# ── Configuration Validation ──────────────────────────────────────────

def validate_runtime_security() -> List[str]:
    """Validate runtime security configuration and return warnings."""
    warnings = []
    
    if SOVEREIGN_MODE_ENABLED:
        warnings.append("WARNING: SOVEREIGN mode is ENABLED - this bypasses sanitization and PTY isolation!")
    
    if not SANITIZATION_ENABLED:
        warnings.append("WARNING: TerminalSanitizer is DISABLED - ANSI escape sequences will not be stripped!")
    
    if not PTY_ISOLATION_ENABLED:
        warnings.append("WARNING: PTY isolation is DISABLED - agents share terminal sessions!")
    
    if not SOVEREIGN_MODE_ENABLED and not SANITIZATION_ENABLED:
        warnings.append("CRITICAL: Both SOVEREIGN mode disabled AND sanitization disabled - no defense against terminal injection!")
    
    return warnings


# Run validation on import
_runtime_warnings = validate_runtime_security()
for warning in _runtime_warnings:
    logger.warning(warning)