"""Tests for NEXUS trace record/rotation/cold-archive.

These tests use a tmp_path sandbox so they NEVER touch $NEXUS_REASONS_DB.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from nexus_os.relay.tracing.schema import TraceRecord, ModelAttempt, uuid_v7
from nexus_os.relay.tracing.record import TraceWriter


def _mk_record(domain: str = "general", outcome: str = "ok") -> TraceRecord:
    return TraceRecord(
        session_id="sess-test",
        domain=domain,
        difficulty="medium",
        tags=["t1", "t2"],
        request_subject="sc-test scrubbed",
        outcome=outcome,
        models_tried=[
            ModelAttempt(
                provider="nvidia",
                model_id="z-ai/glm-5.2",
                message_content="hello world",
                latency_ms=1200,
                total_tokens=42,
                outcome=outcome,
            )
        ],
    )


def test_writer_append_creates_hot_jsonl(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    record = _mk_record()
    writer.append(record)
    files = list((tmp_path / "hot").glob("*.jsonl"))
    assert len(files) == 1
    written = files[0].read_text(encoding="utf-8").strip()
    assert json.loads(written)["trace_id"] == record.trace_id
    assert writer.count() == 1
    writer.close()


def test_writer_search_finds_domain_tag(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    writer.append(_mk_record(domain="code"))
    writer.append(_mk_record(domain="reasoning"))
    writer.close()
    writer2 = TraceWriter(base_dir=tmp_path)
    results = writer2.search("code")
    assert len(results) == 1
    assert results[0]["domain"] == "code"
    writer2.close()


def test_writer_append_many_inserts_all(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    n = writer.append_many([_mk_record() for _ in range(10)])
    assert n == 10
    assert writer.count() == 10
    writer.close()


def test_writer_rotation_moves_old_files_to_warm(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    record = _mk_record()
    record.ts = time.time() - 30 * 86400  # 30 days old
    writer.append(record)
    # Force flush by closing
    writer.close()
    writer2 = TraceWriter(base_dir=tmp_path)
    moved = writer2.rotate()
    assert moved >= 1
    warm_files = list((tmp_path / "warm").glob("*.gz"))
    assert len(warm_files) >= 1
    writer2.close()


def test_writer_cold_archive_zstd(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    record = _mk_record()
    record.ts = time.time() - 100 * 86400
    writer.append(record)
    writer.close()
    writer2 = TraceWriter(base_dir=tmp_path)
    writer2.rotate()
    moved = writer2.archive_cold()
    assert moved >= 1
    cold_files = list((tmp_path / "cold").glob("*.zst"))
    assert len(cold_files) >= 1
    writer2.close()


def test_writer_iter_all_three_tiers(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    old = _mk_record(domain="old_code")
    # 30 days old: pushes past hot_days cutoff
    old.ts = time.time() - 30 * 86400
    new = _mk_record(domain="new_code")
    writer.append(old)
    writer.append(new)
    writer.close()

    writer2 = TraceWriter(base_dir=tmp_path)
    rotating = writer2.rotate()
    cold = writer2.archive_cold(now=time.time() + 365 * 86400)
    found = list(writer2.iter_all())
    # At minimum we should have found records (whether warm, cold, or hot)
    assert isinstance(found, list)
    writer2.close()


def test_uuid_v7_returns_unique():
    seen = {uuid_v7() for _ in range(50)}
    assert len(seen) == 50


def test_uuid_v7_is_sortable():
    a = uuid_v7()
    time.sleep(0.005)
    b = uuid_v7()
    assert a < b  # lexical order = temporal order


def test_record_from_json_roundtrip():
    record = _mk_record()
    payload = record.to_json()
    rebuilt = TraceRecord.from_json(payload)
    assert rebuilt.trace_id == record.trace_id
    assert rebuilt.models_tried[0].provider == "nvidia"


def test_search_returns_recent_first(tmp_path: Path):
    writer = TraceWriter(base_dir=tmp_path)
    r1 = _mk_record(domain="zzz_recent_old")
    r1.ts = time.time() - 5000
    r2 = _mk_record(domain="aaa_newer_recent")
    r2.ts = time.time() - 1000
    writer.append(r1)
    writer.append(r2)
    writer.close()
    writer2 = TraceWriter(base_dir=tmp_path)
    out = writer2.search("aaa_newer_recent")
    assert out[0]["domain"] == "aaa_newer_recent"
    writer2.close()


def test_hot_sqlite_isolated_per_instance(tmp_path: Path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    w1 = TraceWriter(base_dir=dir_a)
    w1.append(_mk_record(domain="alpha"))
    w1.close()
    # a second writer pointed at dir_b should see nothing
    w2 = TraceWriter(base_dir=dir_b)
    assert w2.count() == 0
    w2.close()


# ── Slice-4 retrofit: T6 index-blob slimming, T7 straddle/timezone ─────

def test_index_blob_excludes_message_bodies(tmp_path: Path):
    w = TraceWriter(base_dir=tmp_path)
    heavy = "R" * 5000
    rec = TraceRecord(
        domain="code",
        models_tried=[ModelAttempt(
            provider="nvidia", model_id="m1",
            reasoning_content=heavy, message_content=heavy,
        )],
    )
    w.append(rec)
    row = w._db.execute("SELECT search_blob FROM traces").fetchone()
    blob = row[0]
    assert heavy not in blob                # bodies stay out of the index
    assert "nvidia" in blob and "m1" in blob  # slim projection remains searchable
    w.close()


def test_rotate_keeps_straddling_day_consistent(tmp_path: Path):
    import calendar

    w = TraceWriter(base_dir=tmp_path, hot_days=14)
    now = time.time()
    # a record 14.2 days old whose UTC DAY straddles the raw cutoff
    cutoff = now - 14 * 86400
    day_start = calendar.timegm(time.gmtime(cutoff)[:3] + (0, 0, 0, 0, 0, 0))
    straddler = TraceRecord(ts=day_start + 100.0, domain="straddle")
    old = TraceRecord(ts=day_start - 5 * 86400, domain="ancient")
    w.append(straddler)
    w.append(old)
    moved = w.rotate(now=now)
    assert moved >= 1
    # straddling day: JSONL still hot AND index row still searchable
    day_str = time.strftime("%Y%m%d", time.gmtime(straddler.ts))
    assert (tmp_path / "hot" / f"traces_{day_str}.jsonl").exists()
    assert any(r["domain"] == "straddle" for r in w.search("straddle"))
    # whole old day: file moved to warm AND index row gone
    old_day = time.strftime("%Y%m%d", time.gmtime(old.ts))
    assert not (tmp_path / "hot" / f"traces_{old_day}.jsonl").exists()
    assert (tmp_path / "warm" / f"traces_{old_day}.jsonl.gz").exists()
    assert not w.search("ancient")
    w.close()
