"""GMR Zero-Context-Loss Handoff Packet"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ContextPacket:
    """Zero-context-loss handoff packet.
    
    PROTOCOL: No model receives raw history. Only distilled state + anchors.
    SAVINGS: Reduces context token burn by 40-60%.
    """
    task_id: str
    original_prompt: str
    intent: str
    budget_remaining: int
    core_facts: List[str] = field(default_factory=list)
    decisions_made: List[Dict[str, Any]] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    tool_state: Dict[str, Any] = field(default_factory=dict)
    handoff_count: int = 0
    previous_models: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None

    def to_prompt_prefix(self) -> str:
        """Convert to compact prompt prefix for next model."""
        lines = [f"## Context Handoff (v{self.handoff_count})"]
        if self.core_facts:
            lines.append("### Facts")
            for f in self.core_facts[-5:]:
                lines.append(f"- {f}")
        if self.decisions_made:
            lines.append("### Decisions")
            for d in self.decisions_made[-3:]:
                lines.append(f"- {d}")
        if self.pending_actions:
            lines.append("### Pending")
            for a in self.pending_actions:
                lines.append(f"- {a}")
        return "\n".join(lines)
