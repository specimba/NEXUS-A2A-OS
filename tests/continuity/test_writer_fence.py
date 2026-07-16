"""Writer-fence tests for the continuity ledger (schema v1, additive).

Fence contract:
- browser/MCP/lane-origin rows are capped at UNVERIFIED/E0 unless a proof
  artifact is attached (then eligible for E1); downgrades set fenced=True.
- read side re-applies the cap to rows lacking the fence marker, since the
  .mjs/.ps1/MCP writers append raw JSONL and bypass the Python API.
- governed core writers and legacy floor rows are unaffected.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from nexus_os.continuity.records import (
    ContinuityRunRecord,
    EVIDENCE_GRADE_E0,
    EVIDENCE_GRADE_E1,
    ORIGIN_BROWSER,
    ORIGIN_CORE,
    ORIGIN_MCP,
    ProgressClass,
    VERIFICATION_UNVERIFIED,
    VERIFICATION_VERIFIED,
    append_record,
    read_records,
)
from nexusctl.continuity_cli import run_continuity


def _record(**overrides):
    base = dict(run_id="run-fence", agent_id="agent-x", source_lane="lane-x")
    base.update(overrides)
    return ContinuityRunRecord(**base)


def _cli_args(command, **kwargs):
    base = {
        "continuity_command": command,
        "hours": 24.0,
        "run_id": "run-1",
        "agent_id": "codex-test",
        "source_lane": "grok-project-nexus",
        "input_fingerprint": None,
        "output_fingerprint": None,
        "artifact": [],
        "test": [],
        "provider_calls": 0,
        "quota_reserved": 0,
        "blocker": None,
        "next_action": None,
        "started_at": None,
        "implemented": False,
        "advisory_only": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_browser_row_verified_claim_without_proof_is_fenced(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    rec = _record(
        origin=ORIGIN_BROWSER,
        verification=VERIFICATION_VERIFIED,
        evidence_grade=EVIDENCE_GRADE_E1,
        progress_class=ProgressClass.VERIFIED_DELTA.value,
    )
    append_record(rec, ledger)

    raw = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert raw["verification"] == VERIFICATION_UNVERIFIED
    assert raw["evidence_grade"] == EVIDENCE_GRADE_E0
    assert raw["progress_class"] == ProgressClass.EVIDENCE_DELTA.value
    assert raw["fenced"] is True
    assert "without proof" in raw["fence_reason"]

    records, meta = read_records(ledger)
    assert meta["corrupt_tail"] is False
    (parsed,) = records
    assert parsed.verification == VERIFICATION_UNVERIFIED
    assert parsed.evidence_grade == EVIDENCE_GRADE_E0
    assert parsed.fenced is True


def test_mcp_writer_identity_is_classified_and_fenced(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    rec = _record(
        agent_id="grok_mcp_server_v2",
        verification=VERIFICATION_VERIFIED,
        progress_class=ProgressClass.VERIFIED_DELTA.value,
    )
    append_record(rec, ledger)  # no explicit origin: writer identity decides

    records, _ = read_records(ledger)
    (parsed,) = records
    assert parsed.origin == ORIGIN_MCP
    assert parsed.verification == VERIFICATION_UNVERIFIED
    assert parsed.evidence_grade == EVIDENCE_GRADE_E0
    assert parsed.fenced is True


def test_browser_row_with_proof_path_reaches_e1(tmp_path):
    proof = tmp_path / "proof.txt"
    proof.write_text("NEXUS_PROOF_OK lane evidence", encoding="utf-8")
    ledger = tmp_path / "runs.jsonl"
    rec = _record(
        origin=ORIGIN_BROWSER,
        verification=VERIFICATION_VERIFIED,
        progress_class=ProgressClass.VERIFIED_DELTA.value,
        proof_path=str(proof),
    )
    append_record(rec, ledger)

    records, _ = read_records(ledger)
    (parsed,) = records
    assert parsed.evidence_grade == EVIDENCE_GRADE_E1
    assert parsed.verification == VERIFICATION_VERIFIED
    assert parsed.progress_class == ProgressClass.VERIFIED_DELTA.value
    assert parsed.fenced is False


def test_browser_row_with_proof_token_payload_reaches_e1(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    rec = _record(
        origin=ORIGIN_BROWSER,
        verification=VERIFICATION_VERIFIED,
        proof={"tail_snippet": "NEXUS_PROOF_OK ping from lane"},
    )
    append_record(rec, ledger)

    records, _ = read_records(ledger)
    (parsed,) = records
    assert parsed.evidence_grade == EVIDENCE_GRADE_E1
    assert parsed.verification == VERIFICATION_VERIFIED
    assert parsed.fenced is False


def test_core_governed_writer_unaffected(monkeypatch, tmp_path):
    ledger = tmp_path / "runs.jsonl"
    monkeypatch.setenv("NEXUS_CONTINUITY_LEDGER", str(ledger))

    code, payload = run_continuity(
        _cli_args(
            "close",
            input_fingerprint="in-1",
            output_fingerprint="out-1",
            artifact=["docs/verified.md"],
            test=["python -m pytest tests/continuity/test_writer_fence.py -q"],
            provider_calls=1,
        )
    )
    assert code == 0
    row = payload["record"]
    assert row["origin"] == ORIGIN_CORE
    assert row["progress_class"] == ProgressClass.VERIFIED_DELTA.value
    assert row["verification"] == VERIFICATION_VERIFIED
    assert row["evidence_grade"] == EVIDENCE_GRADE_E1
    assert row["fenced"] is False

    records, meta = read_records(ledger)
    assert meta["corrupt_tail"] is False
    (parsed,) = records
    assert parsed.progress_class == ProgressClass.VERIFIED_DELTA.value
    assert parsed.verification == VERIFICATION_VERIFIED
    assert parsed.fenced is False


def test_read_side_caps_foreign_mjs_style_row(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    row = {
        "run_id": "lane-proof-1",
        "kind": "lane_send_proof",
        "agent": "send_grok_cdp",
        "proof_token": True,  # bare claim, not a proof payload
        "progress_class": "VERIFIED_DELTA",
        "verification": "VERIFIED",
        "evidence_grade": "E1",
    }
    ledger.write_text(json.dumps(row) + chr(10), encoding="utf-8")

    records, meta = read_records(ledger)
    assert meta["corrupt_tail"] is False
    (parsed,) = records
    assert parsed.origin == ORIGIN_BROWSER
    assert parsed.verification == VERIFICATION_UNVERIFIED
    assert parsed.evidence_grade == EVIDENCE_GRADE_E0
    assert parsed.progress_class == ProgressClass.EVIDENCE_DELTA.value
    assert parsed.fenced is True
    assert "without proof" in parsed.fence_reason


def test_read_side_caps_markerless_legacy_verified_claim(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    row = {
        "schema": "nexus.continuity.run.v1",
        "run_id": "old-1",
        "agent_id": "codex",
        "source_lane": "s",
        "progress_class": "VERIFIED_DELTA",
    }
    ledger.write_text(json.dumps(row) + chr(10), encoding="utf-8")

    records, _ = read_records(ledger)
    (parsed,) = records
    assert parsed.progress_class == ProgressClass.EVIDENCE_DELTA.value
    assert parsed.fenced is True
    assert "fence marker" in parsed.fence_reason


def test_legacy_and_corrupt_rows_stay_tolerated(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    lines = [
        '{"schema":"nexus.continuity.run.v1","run_id":"ok","agent_id":"a","source_lane":"s"}',
        '{"kind":"lane_stack_preflight","agent":"grok-build-0.1","status":"READY"}',
        '{bad-tail',
    ]
    original = chr(10).join(lines)
    ledger.write_text(original, encoding="utf-8")

    records, meta = read_records(ledger)
    assert len(records) == 2
    typed, foreign = records
    assert typed.origin == ORIGIN_CORE
    assert typed.fenced is False  # floor row: cap is identity, no flag
    assert typed.progress_class == ProgressClass.NOOP_RECAP.value
    assert foreign.run_id.startswith("legacy-sha256:")
    assert foreign.origin == ORIGIN_BROWSER
    assert foreign.source_lane == "lane_stack_preflight"
    assert meta["corrupt_tail"] is True
    assert len(meta["errors"]) == 1
    # read path never rewrites the ledger
    assert ledger.read_text(encoding="utf-8") == original


def test_concurrent_appends_remain_complete_jsonl(tmp_path):
    ledger = tmp_path / "runs.jsonl"

    def write(index):
        append_record(_record(run_id=f"run-{index}"), ledger)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(40)))

    rows, meta = read_records(ledger)
    assert meta["corrupt_tail"] is False
    assert len(rows) == 40
    assert {row.run_id for row in rows} == {f"run-{i}" for i in range(40)}
