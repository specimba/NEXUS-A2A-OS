from nexus_os.security.behaviormancer_nexus import (
    NexusBehaviorMancer,
    NexusBehaviorMancerConfig,
)


def test_behaviormancer_prepare_proposal_is_dry_run_only(tmp_path):
    config = NexusBehaviorMancerConfig(
        model_path="WeiboAI/VibeThinker-3B",
        target_dataset_path=str(tmp_path / "target.jsonl"),
        baseline_dataset_path=str(tmp_path / "baseline.jsonl"),
        preservation_dataset_path=str(tmp_path / "preservation.jsonl"),
        output_path=str(tmp_path / "modified-model"),
    )

    proposal = NexusBehaviorMancer(config).prepare_proposal()
    data = proposal.to_dict()

    assert data["dry_run"] is True
    assert data["writes_weights"] is False
    assert data["can_write_weights"] is False
    assert data["route_class"] == "behavior_control"
    assert data["lab_allowed"] is True
    assert "vap_record" in data["required_controls"]
    assert data["artifact_manifest"]["before_refusal_score"] is None
    assert data["artifact_manifest"]["after_refusal_score"] is None


def test_behaviormancer_refuses_weight_write_without_governance(tmp_path):
    config = NexusBehaviorMancerConfig(
        model_path="DavidAU/VibeThinker-heretic-uncensored",
        output_path=str(tmp_path / "modified-model"),
    )
    mancer = NexusBehaviorMancer(config)

    assert mancer.run_abliteration() is False
    assert not (tmp_path / "modified-model").exists()
