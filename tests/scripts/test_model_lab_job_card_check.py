from __future__ import annotations

import importlib.util
import json
from pathlib import Path


"""
CANARY_TOKEN: 319935963a161c7a9d91f1f6aa5f8bf8
"""
ROOT = Path(__file__).resolve().parents[2]


def load_validator():
    path = ROOT / "scripts" / "model_lab_job_card_check.py"
    spec = importlib.util.spec_from_file_location("model_lab_job_card_check", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_model_lab_job_card_passes() -> None:
    validator = load_validator()
    report = validator.validate_file(ROOT / "docs" / "handoff" / "model_lab_job_card.example.json")

    assert report["passed"] is True
    assert report["operation"] == "eval_only"
    assert report["errors"] == []


def test_training_job_requires_hard_safety_gates() -> None:
    validator = load_validator()
    card = {
        "schema_version": "nexus-model-lab-job-card-v1",
        "job_id": "MLAB-TEST-001",
        "created_at": "2026-05-26T00:00:00Z",
        "status": "proposal",
        "operation": "fine_tune",
        "objective": "Unsafe missing gates should fail.",
        "dataset": {
            "source_ref": "dataset.md",
            "hash_sha256": "a" * 64,
            "license": "internal",
            "contains_sensitive_data": False,
        },
        "recipe": {
            "config_ref": "recipe.md",
            "hash_sha256": "b" * 64,
            "base_model": "local/test",
            "method": "lora",
        },
        "resource_policy": {
            "allow_gpu": True,
            "max_runtime_minutes": 60,
            "protected_workloads_ack": False,
        },
        "safety_gates": {
            "leak_scan_required": True,
            "guard_eval_required": False,
            "rollback_required": False,
            "human_approval_required": False,
        },
        "outputs": {
            "target_dir": "out",
            "registry_action": "register_candidate",
        },
        "approvals": {
            "governor_proposal_id": None,
            "operator": "speci",
            "notes": "test",
        },
    }

    report = validator.validate_card(card)

    assert report["passed"] is False
    assert any("protected_workloads_ack" in error for error in report["errors"])
    assert any("guard_eval_required" in error for error in report["errors"])
    assert any("rollback_required" in error for error in report["errors"])
    assert any("human_approval_required" in error for error in report["errors"])


def test_job_card_rejects_secret_shaped_values(tmp_path: Path) -> None:
    validator = load_validator()
    card_path = tmp_path / "bad-card.json"
    card_path.write_text(
        json.dumps(
            {
                "schema_version": "nexus-model-lab-job-card-v1",
                "job_id": "MLAB-TEST-002",
                "created_at": "2026-05-26T00:00:00Z",
                "status": "proposal",
                "operation": "eval_only",
                "objective": "contains sk-or-1234567890abcdef token",
                "dataset": {
                    "source_ref": "dataset.md",
                    "hash_sha256": "a" * 64,
                    "license": "internal",
                    "contains_sensitive_data": False,
                },
                "recipe": {
                    "config_ref": "recipe.md",
                    "hash_sha256": "b" * 64,
                    "base_model": "local/test",
                    "method": "eval",
                },
                "resource_policy": {
                    "allow_gpu": False,
                    "max_runtime_minutes": 5,
                    "protected_workloads_ack": True,
                },
                "safety_gates": {
                    "leak_scan_required": True,
                    "guard_eval_required": True,
                    "rollback_required": True,
                    "human_approval_required": True,
                },
                "outputs": {
                    "target_dir": "out",
                    "registry_action": "evidence_only",
                },
                "approvals": {
                    "governor_proposal_id": None,
                    "operator": "speci",
                    "notes": "test",
                },
            }
        ),
        encoding="utf-8",
    )

    report = validator.validate_file(card_path)

    assert report["passed"] is False
    assert any("secret-shaped" in error for error in report["errors"])
