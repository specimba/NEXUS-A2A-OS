"""
nexus_os/reasoning — FableReasoningEngine

CoT pattern extraction, vectorization, and template generation for
NEXUS agent reasoning guidance. Wires together:

  PatternExtractor -> ReasoningVectorizer -> ReasoningTemplateEngine
       |                                         |
  training_generator                        fable_engine (orchestrator)

Usage:
    from nexus_os.reasoning import FableReasoningEngine
    engine = FableReasoningEngine()
    engine.initialize()
    prompt = engine.generate_prompt(task_type="debug", complexity="L2")
"""

from nexus_os.reasoning.pattern_extractor import (
    PATTERN_CATEGORIES,
    PatternExtractor,
    ReasoningPattern,
)
from nexus_os.reasoning.reasoning_vectors import ReasoningVectorizer
from nexus_os.reasoning.reasoning_templates import (
    ReasoningStyle,
    ReasoningTemplateEngine,
)

try:
    from nexus_os.reasoning.fable_engine import (
        FableReasoningEngine,
        create_default_engine,
        run_cli,
    )
    _FABLE_ENGINE_AVAILABLE = True
except ImportError:
    _FABLE_ENGINE_AVAILABLE = False

try:
    from nexus_os.reasoning.training_generator import (
        CoTSynthesizer,
        DPOPairGenerator,
        DatasetFormatter,
        generate_training_data,
    )
    _TRAINING_AVAILABLE = True
except ImportError:
    _TRAINING_AVAILABLE = False

__all__ = [
    # Pattern extraction
    "PATTERN_CATEGORIES",
    "PatternExtractor",
    "ReasoningPattern",
    # Vectorization
    "ReasoningVectorizer",
    # Templates
    "ReasoningStyle",
    "ReasoningTemplateEngine",
    # Orchestrator (conditional)
    "FableReasoningEngine",
    "create_default_engine",
    "run_cli",
    # Training data (conditional)
    "CoTSynthesizer",
    "DPOPairGenerator",
    "DatasetFormatter",
    "generate_training_data",
    # Status flags
    "_FABLE_ENGINE_AVAILABLE",
    "_TRAINING_AVAILABLE",
]

__version__ = "0.1.0"
__description__ = "FableReasoningEngine -- CoT pattern extraction, vectorization, and template generation"
