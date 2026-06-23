import argparse
import json

from nexus_os.cli.nexusctl import cmd_model_lab


def test_model_lab_propose_outputs_dry_run_manifest(capsys):
    args = argparse.Namespace(
        inventory=False,
        verify_manifest=None,
        propose="DavidAU/VibeThinker-heretic-uncensored",
        method_class="refusal_vector_abliteration",
        target_dataset="target.jsonl",
        baseline_dataset="baseline.jsonl",
        preservation_dataset="preservation.jsonl",
        output_path="out-model",
        n_samples=8,
        direction_multiplier=0.5,
        null_space_constraints=True,
        start_layer_ratio=0.2,
        end_layer_ratio=0.8,
    )

    assert cmd_model_lab(args) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["dry_run"] is True
    assert result["writes_weights"] is False
    assert result["route_class"] == "behavior_control"
    assert result["lab_allowed"] is True
    assert result["artifact_manifest"]["n_samples"] == 8


def test_model_lab_inventory_is_read_only(capsys):
    args = argparse.Namespace(
        inventory=True,
        verify_manifest=None,
        propose=None,
    )

    assert cmd_model_lab(args) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["mode"] == "inventory"
    assert result["dry_run"] is True
    assert "behavior_control_count" in result
