"""
swarm/worker_roles.py — 13 Specialized Worker Role Definitions

Backed by:
  - arXiv:2604.18133 (Multi-Agent Systems: Classical to LFM-MAS)
  - NEXUS_MODEL_USAGE_PLAN_2026-07-10.md (3-tier model stack)
  - NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md (antiGRAV stack design)

Integration: ADDITIVE to existing swarm/foreman.py + team/coordinator.py.
The existing SWARM_TEAM_DESIGN.md only defines 2 generic workers:
  glm5-worker-1 (code/analysis/reasoning)
  glm5-worker-2 (code/operations/security)

This module defines 13 specialized roles mapped to the real 3-tier model stack,
each with: CogER level, trust floor, sandbox class, and model assignment.

Usage:
    from nexus_os.swarm.worker_roles import WorkerRoleRegistry

    registry = WorkerRoleRegistry()
    role = registry.get_role("task_coder")
    # role = WorkerRole(name="task_coder", model="vibethinker-3b", tier=2, ...)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkerRole:
    """Specialized worker role definition."""
    role_id: str
    name: str
    description: str
    model: str
    tier: int  # 0-4
    tier_name: str  # T0-T4
    coger_level: str  # L1-L4
    trust_floor: int  # Minimum trust required (0-100)
    sandbox_class: str  # "userspace" / "container" / "microvm" / "cloud" / "browser_cdp"
    specializations: List[str] = field(default_factory=list)
    vram_mb: int = 0
    always_loaded: bool = False
    unload_before_load: bool = False  # T2 rotatable models need this
    activation_steering: Optional[Dict[str, int]] = None  # layer → steering value
    evidence_gate_required: bool = False
    serial_only: bool = False  # NIM constraint


class WorkerRoleRegistry:
    """Registry of 13 specialized worker roles.

    Maps to the NEXUS 3-tier model stack from NEXUS_MODEL_USAGE_PLAN:
    - T0 Anchors: always loaded, <800MB, CPU-offload OK
    - T1 Guards: always loaded, ~1GB, activation steering for 0% FPR
    - T2 Task: rotatable, 2-2.5GB, unload-before-load
    - T3 Cloud: via ModelRelay, serial-only on NIM
    - T4 CDP: browser-based, evidence-gate required
    """

    ROLES: List[WorkerRole] = [
        # ── T0: Anchors (always loaded, <800MB) ──────────────────────
        WorkerRole(
            role_id="anchor_intent",
            name="Anchor-Intent",
            description="Intent classification and tool selection via FunctionGemma",
            model="functiongemma-270m",
            tier=0, tier_name="T0",
            coger_level="L1",
            trust_floor=50,
            sandbox_class="userspace",
            specializations=["intent_classification", "tool_selection"],
            vram_mb=350,
            always_loaded=True,
        ),
        WorkerRole(
            role_id="anchor_cli",
            name="Anchor-CLI",
            description="Command parsing and bash validation via BashGemma",
            model="bashgemma-270m",
            tier=0, tier_name="T0",
            coger_level="L1",
            trust_floor=50,
            sandbox_class="container",
            specializations=["cli_parsing", "bash_validation", "command_safety"],
            vram_mb=400,
            always_loaded=True,
        ),

        # ── T1: Guards (always loaded, ~1GB, activation steering) ────
        WorkerRole(
            role_id="guard_vats",
            name="Guard-VATS",
            description="Security gatekeeping with VATS defense (error message sanitization)",
            model="llama-guard-3-1b",
            tier=1, tier_name="T1",
            coger_level="L1",
            trust_floor=80,
            sandbox_class="userspace",
            specializations=["vats_defense", "security_gate", "injection_detection"],
            vram_mb=1000,
            always_loaded=True,
            activation_steering={"layer": 15, "fpr_target": 0.0},  # L15 for 0% FPR
        ),
        WorkerRole(
            role_id="guard_prefilter",
            name="Guard-PreFilter",
            description="Pre-filter classification via Heretic uncensored Gemma",
            model="gemma-3-1b-heretic",
            tier=1, tier_name="T1",
            coger_level="L1",
            trust_floor=70,
            sandbox_class="userspace",
            specializations=["prefilter", "classification", "content_screening"],
            vram_mb=1000,
            always_loaded=True,
        ),
        WorkerRole(
            role_id="guard_consensus",
            name="Guard-Consensus",
            description="Consensus voting via GLiGuard + Arch-Guard ensemble",
            model="gliguard-300m",
            tier=1, tier_name="T1",
            coger_level="L1",
            trust_floor=75,
            sandbox_class="userspace",
            specializations=["consensus_voting", "guard_ensemble", "false_positive_reduction"],
            vram_mb=600,
            always_loaded=True,
        ),

        # ── T2: Task Workers (rotatable, 2-2.5GB, unload-before-load) ──
        WorkerRole(
            role_id="task_coder",
            name="Task-Coder",
            description="Code generation and SWE tasks via VibeThinker-3B-Agentic",
            model="vibethinker-3b-agentic",
            tier=2, tier_name="T2",
            coger_level="L2",
            trust_floor=60,
            sandbox_class="container",
            specializations=["code_generation", "swe_tasks", "code_review"],
            vram_mb=2500,
            always_loaded=False,
            unload_before_load=True,
        ),
        WorkerRole(
            role_id="task_reasoner",
            name="Task-Reasoner",
            description="Math, logic, and reasoning via Mythos-nano-OBLITERATED",
            model="mythos-nano-obliterated",
            tier=2, tier_name="T2",
            coger_level="L2",
            trust_floor=60,
            sandbox_class="userspace",
            specializations=["math", "logic", "reasoning", "verification"],
            vram_mb=2500,
            always_loaded=False,
            unload_before_load=True,
        ),
        WorkerRole(
            role_id="task_toolcaller",
            name="Task-ToolCaller",
            description="Multi-turn tool calling via refinedtoolcallv5-3b",
            model="refinedtoolcallv5-3b",
            tier=2, tier_name="T2",
            coger_level="L2",
            trust_floor=65,
            sandbox_class="container",
            specializations=["tool_calling", "multi_turn", "schema_validation"],
            vram_mb=2500,
            always_loaded=False,
            unload_before_load=True,
        ),

        # ── T3: Cloud Workers (via ModelRelay, serial-only on NIM) ───
        WorkerRole(
            role_id="cloud_researcher",
            name="Cloud-Researcher",
            description="Deep research and long context via GLM-5.2",
            model="glm-5.2",
            tier=3, tier_name="T3",
            coger_level="L3",
            trust_floor=70,
            sandbox_class="cloud",
            specializations=["deep_research", "long_context", "synthesis"],
            vram_mb=0,  # Cloud
            always_loaded=False,
            serial_only=True,  # NIM 8 RPM constraint
        ),
        WorkerRole(
            role_id="cloud_coder",
            name="Cloud-Coder",
            description="Complex code and SWE-bench via DeepSeek-V4-Flash",
            model="deepseek-v4-flash",
            tier=3, tier_name="T3",
            coger_level="L3",
            trust_floor=70,
            sandbox_class="cloud",
            specializations=["complex_code", "swe_bench", "code_refactoring"],
            vram_mb=0,  # Cloud
            always_loaded=False,
            serial_only=True,
        ),

        # ── T4: CDP Workers (browser-based, evidence-gate required) ──
        WorkerRole(
            role_id="cdp_thinker",
            name="CDP-Thinker",
            description="Trinity Thinker role via Grok/Qwen browser lane",
            model="grok-browser",
            tier=4, tier_name="T4",
            coger_level="L4",
            trust_floor=75,
            sandbox_class="browser_cdp",
            specializations=["trinity_thinker", "strategy", "plan_generation"],
            vram_mb=0,  # Browser
            always_loaded=False,
            evidence_gate_required=True,
        ),
        WorkerRole(
            role_id="cdp_worker",
            name="CDP-Worker",
            description="Trinity Worker role via DeepSeek/GLM browser lane",
            model="deepseek-browser",
            tier=4, tier_name="T4",
            coger_level="L4",
            trust_floor=70,
            sandbox_class="browser_cdp",
            specializations=["trinity_worker", "execution", "task_completion"],
            vram_mb=0,  # Browser
            always_loaded=False,
            evidence_gate_required=True,
        ),
        WorkerRole(
            role_id="cdp_verifier",
            name="CDP-Verifier",
            description="Trinity Verifier role via Gemini/MiniMax browser lane",
            model="gemini-browser",
            tier=4, tier_name="T4",
            coger_level="L4",
            trust_floor=80,
            sandbox_class="browser_cdp",
            specializations=["trinity_verifier", "verification", "quality_check"],
            vram_mb=0,  # Browser
            always_loaded=False,
            evidence_gate_required=True,
        ),
    ]

    @classmethod
    def get_role(cls, role_id: str) -> Optional[WorkerRole]:
        for role in cls.ROLES:
            if role.role_id == role_id:
                return role
        return None

    @classmethod
    def get_by_tier(cls, tier: int) -> List[WorkerRole]:
        return [r for r in cls.ROLES if r.tier == tier]

    @classmethod
    def get_by_coger_level(cls, level: str) -> List[WorkerRole]:
        return [r for r in cls.ROLES if r.coger_level == level]

    @classmethod
    def get_by_specialization(cls, specialization: str) -> List[WorkerRole]:
        return [r for r in cls.ROLES if specialization in r.specializations]

    @classmethod
    def to_worker_definitions(cls) -> List[Dict[str, Any]]:
        """Convert to format compatible with team/coordinator.py WORKER_DEFINITIONS."""
        return [
            {
                "worker_id": r.role_id,
                "agent_dir": r.role_id,
                "specializations": r.specializations,
                "model_profile": r.model,
                "tier": r.tier,
                "coger_level": r.coger_level,
                "trust_floor": r.trust_floor,
                "sandbox_class": r.sandbox_class,
                "vram_mb": r.vram_mb,
                "always_loaded": r.always_loaded,
                "unload_before_load": r.unload_before_load,
                "serial_only": r.serial_only,
                "evidence_gate_required": r.evidence_gate_required,
            }
            for r in cls.ROLES
        ]

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        return {
            "total_roles": len(cls.ROLES),
            "by_tier": {f"T{t}": len(cls.get_by_tier(t)) for t in range(5)},
            "by_coger": {f"L{n}": len(cls.get_by_coger_level(f"L{n}")) for n in range(1, 5)},
            "always_loaded": sum(1 for r in cls.ROLES if r.always_loaded),
            "rotatable": sum(1 for r in cls.ROLES if r.unload_before_load),
            "cloud": sum(1 for r in cls.ROLES if r.tier == 3),
            "cdp": sum(1 for r in cls.ROLES if r.tier == 4),
            "total_vram_mb": sum(r.vram_mb for r in cls.ROLES if r.always_loaded),
        }
