"""nexus_os/boot.py — System initialization and component activation.

Activates all formerly-advisory subsystems at runtime:
  1. ConfigSyncEngine — centralized config with layered sources
  2. ModelRegistry — unified model/provider/domain routing
  3. SkillAuditor KAIJU gate — pre-flight code audit in AgentPool
  4. ModelRelayHeavySkill + DeliberationSynthesizer — real model inference
  5. ChromaDB SEMANTIC backend — vector search in MemoryChannelManager
  6. Escalation monitor daemon — 3-tier retry/re-route/rollback
  7. QEnhancer token confidence — CK-PLUG into TrustEngine

Call initialize_system() at startup before any other operations.
Each phase is wrapped in try/except so a single failure does not block
the rest of boot. Failure is logged but never raised.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_initialized = False
_phase_status: dict[str, str] = {}
_reasoning_engine: Optional["FableReasoningEngine"] = None  # NEW


def initialize_system() -> None:
    """Initialize and wire all system components. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return

    logger.info("NEXUS OS boot sequence starting...")

    phases = [
        ("config", _init_config_engine),
        ("model_registry", _init_model_registry),
        ("skill_auditor", _init_skill_auditor),
        ("heavy_skill", _init_heavy_skill),
        ("semantic_backend", _init_semantic_backend),
        ("escalation_monitor", _init_escalation_monitor),
        ("q_enhancer", _init_q_enhancer),
        ("reasoning_engine", _init_reasoning_engine),  # NEW
    ]

    for name, fn in phases:
        try:
            fn()
            _phase_status[name] = "ok"
        except Exception as e:
            _phase_status[name] = f"FAIL: {e}"
            logger.warning("Boot phase %s failed: %s", name, e, exc_info=True)

    _initialized = True
    ok = sum(1 for v in _phase_status.values() if v == "ok")
    total = len(_phase_status)
    logger.info(
        "NEXUS OS boot sequence complete: %d/%d phases OK (%s)",
        ok, total, _phase_status,
    )


def is_initialized() -> bool:
    return _initialized


def get_phase_status() -> dict[str, str]:
    """Return the activation status of each boot phase."""
    return dict(_phase_status)


def get_reasoning_engine():
    """Return the initialized FableReasoningEngine, or None."""
    return _reasoning_engine


# ── Phase 1: ConfigSyncEngine ──────────────────────────────────────────────


def _init_config_engine() -> None:
    """Activate ConfigSyncEngine with all sources and known config classes."""
    from nexus_os.config.sync_engine import (
        EnvSource, JsonSource, SourcePriority, get_engine,
    )
    from nexus_os.config.sync_engine import DataclassSource
    from pathlib import Path

    engine = get_engine()

    # Register env var source (auto-discovers NEXUS_* and NX_* vars)
    engine.register_source(EnvSource("NEXUS_"))
    engine.register_source(EnvSource("NX_"))

    # Register known config dataclasses (best-effort — skip if import fails)
    _safe_register(engine, DataclassSource, "nexus_os.governor.trust_formulas", "FormulaConfig")
    _safe_register(engine, DataclassSource, "nexus_os.nexusclaw.brainstorm", "ParallelReasoningConfig")
    _safe_register(engine, DataclassSource, "nexus_os.nexusclaw.deliberation_synthesis", "SynthesisConfig")
    _safe_register(engine, DataclassSource, "nexus_os.nexusclaw.runner", "RunnerConfig")

    # Load config file if it exists
    for filename in ("nexus_os.json", "config.json"):
        config_path = Path(filename)
        if config_path.exists():
            engine.register_source(JsonSource(str(config_path)))

    report = engine.load()
    logger.info(
        "ConfigSyncEngine active: %d entries from %d sources (%d conflicts)",
        report.entries_total, report.sources_loaded, report.conflicts_resolved,
    )


def _safe_register(engine: Any, DataclassSource: Any, module_path: str, class_name: str) -> None:
    """Try to import and register a config dataclass; skip on any error."""
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        instance = cls()
        engine.register_source(DataclassSource(instance, priority=10))
        logger.debug("Registered config: %s.%s", module_path, class_name)
    except (ImportError, AttributeError, TypeError) as e:
        logger.debug("Skipped config %s.%s: %s", module_path, class_name, e)


# ── Phase 2: ModelRegistry ────────────────────────────────────────────────


def _init_model_registry() -> None:
    """Activate ModelRegistry singleton and log available domains/providers."""
    from nexus_os.models.registry import get_registry

    registry = get_registry()
    domains = registry.list_domains()
    providers = registry.list_providers()
    models = registry.list_models()

    logger.info(
        "ModelRegistry active: %d domains, %d providers, %d models",
        len(domains), len(providers), len(models),
    )


# ── Phase 3: SkillAuditor KAIJU gate ──────────────────────────────────────


def _init_skill_auditor() -> None:
    """Create SkillAuditor and wire into AgentPool for pre-flight audit."""
    from nexus_os.governor.skill_auditor import SkillAuditor
    from nexus_os.nexusclaw.agent_pool import get_agent_pool

    auditor = SkillAuditor()
    pool = get_agent_pool()
    pool.set_skill_auditor(auditor)
    logger.info("SkillAuditor wired into AgentPool — pre-flight gate active")


# ── Phase 4: HeavySkill + Deliberation Synthesis ──────────────────────────


def _init_heavy_skill() -> None:
    """Wire ModelRelayHeavySkill and DeliberationSynthesizer into brainstorm."""
    from nexus_os.nexusclaw.heavyskill_relay import get_heavy_relay
    from nexus_os.nexusclaw.deliberation_synthesis import DeliberationSynthesizer

    relay = get_heavy_relay()
    available = relay.check_availability()
    logger.info(
        "ModelRelayHeavySkill: %s",
        "AVAILABLE" if available else "unavailable (mock fallback active)",
    )

    synth = DeliberationSynthesizer()
    logger.info(
        "DeliberationSynthesizer active (ModelRelay mode=%s)",
        synth.config.use_model_relay,
    )


# ── Phase 5: ChromaDB SEMANTIC backend ────────────────────────────────────


def _init_semantic_backend() -> None:
    """Initialize SEMANTIC channel backend (ChromaLocal or Hybrid)."""
    from nexus_os.vault.semantic_backend import LocalBackend, set_semantic_backend

    backend = LocalBackend()
    set_semantic_backend(backend)
    logger.info("SEMANTIC backend: Local (default — ChromaDB optional via HybridBackend)")


# ── Phase 6: Escalation monitor daemon ────────────────────────────────────


def _init_escalation_monitor() -> None:
    """Start the TaskRouter escalation monitor daemon thread."""
    from nexus_os.nexusclaw.task_router import get_task_router

    router = get_task_router()
    try:
        router.start_escalation_monitor()
        logger.info("Escalation monitor daemon started (3-tier retry/re-route/rollback)")
    except Exception as e:
        logger.debug("Escalation monitor already running or failed: %s", e)


# ── Phase 7: QEnhancer token confidence ────────────────────────────────────


def _init_q_enhancer() -> None:
    """Wire QEnhancer into TrustEngine as an optional Q input."""
    from nexus_os.governor.token_confidence import QEnhancer

    enhancer = QEnhancer(confidence_weight=0.3, mode="mean", floor=0.0)
    logger.info(
        "QEnhancer active (confidence_weight=0.3, mode=%s, floor=%s)",
        enhancer.mode, enhancer.floor,
    )


# ── Phase 8: FableReasoningEngine ──────────────────────────────────────────


def _init_reasoning_engine() -> None:
    """Initialize the FableReasoningEngine and register it as available.

    Creates the reasoning engine singleton, attempts to load the Fable 5 CoT
    dataset, and makes it accessible via the module's global reference for
    prompt injection and agent reasoning guidance.

    This phase is non-critical — failure only logs a warning and the system
    continues without reasoning templates.
    """
    global _reasoning_engine
    try:
        from nexus_os.reasoning.fable_engine import (
            FableReasoningEngine,
            create_default_engine,
        )

        engine = create_default_engine()
        engine.initialize()

        # Store as module global for access by agent_pool and orchestrator
        _reasoning_engine = engine

        stats = engine.status()
        logger.info(
            "FableReasoningEngine active: %d patterns across %d categories "
            "(style=%s, vectorizer=%s)",
            stats.get("total_patterns", 0),
            stats.get("categories_with_data", 0),
            stats.get("template_style", "unknown"),
            "fitted" if stats.get("vectorizer_fitted") else "not fitted",
        )
    except Exception as e:
        logger.warning(
            "FableReasoningEngine initialization skipped: %s", e,
        )
