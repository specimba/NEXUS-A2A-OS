"""NEXUS Eval — Benchmarking and evaluation framework."""
from nexus_os.eval.vibethinker_eval import (
    TaskCategory,
    EvalTask,
    TaskResult,
    EvalReport,
    build_task_bank,
    run_eval,
    compute_report,
    print_report,
    get_client,
)

__all__ = [
    "TaskCategory",
    "EvalTask",
    "TaskResult",
    "EvalReport",
    "build_task_bank",
    "run_eval",
    "compute_report",
    "print_report",
    "get_client",
]