"""Tests for NEXUS Dataset Forge package."""
import sys
import json
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.dataset_forge.core import (
    DatasetType,
    QualityTier,
    RecordMetadata,
    NEXUSDataset,
    DatasetManifest,
    NEXUSBenchRecord,
    generate_dataset_id,
)
from nexus_os.dataset_forge.generators import (
    GeneratorConfig,
    GuardSafeGenerator,
    GuardAdversarialGenerator,
    ReasoningDatasetGenerator,
    CodeSecurityGenerator,
    MCPToolUseGenerator,
    TrustBoundaryGenerator,
    MisalignmentGenerator,
    RefusalBoundaryGenerator,
    GovernanceDatasetGenerator,
    DatasetGenerator,
)
from nexus_os.dataset_forge.quality import (
    QualityFilter,
    NGramDedup,
    QualityReport,
    validate_nexus_dataset,
    deduplicate_jsonl,
    DeduplicationStrategy,
)
from nexus_os.dataset_forge.bench_adapter import (
    BenchTrack,
    NEXUSBenchFormat,
    MultiTrackConverter,
    score_guard_benchmark,
    score_governance_benchmark,
)


class TestDatasetTypeEnum:
    def test_all_types_exist(self):
        assert DatasetType.GUARD_SAFE.value == "guard_safe"
        assert DatasetType.GUARD_ADVERSARIAL.value == "guard_adversarial"
        assert DatasetType.BENIGN.value == "benign"
        assert DatasetType.REASONING.value == "reasoning"
        assert DatasetType.CODE_SECURITY.value == "code_security"
        assert DatasetType.MCP_TOOL_USE.value == "mcp_tool_use"
        assert DatasetType.TRUST_BOUNDARY.value == "trust_boundary"
        assert DatasetType.MISALIGNMENT_DETECT.value == "misalignment_detect"
        assert DatasetType.REFUSAL_BOUNDARY.value == "refusal_boundary"
        assert DatasetType.GOVERNANCE.value == "governance"

    def test_is_string_enum(self):
        assert isinstance(DatasetType.GUARD_SAFE, str)


class TestQualityTierEnum:
    def test_all_tiers_exist(self):
        assert QualityTier.S0_DEMO.value == "S0_demo"
        assert QualityTier.S1_RESEARCH.value == "S1_research"
        assert QualityTier.S2_EVAL.value == "S2_eval"
        assert QualityTier.S3_BENCHMARK.value == "S3_benchmark"


class TestRecordMetadata:
    def test_to_dict(self):
        meta = RecordMetadata(
            created_at="2026-06-18T00:00:00Z",
            generator="test",
            quality_tier="S2_eval",
            dataset_type="guard_safe",
        )
        d = meta.to_dict()
        assert d["created_at"] == "2026-06-18T00:00:00Z"
        assert d["generator"] == "test"
        assert d["quality_tier"] == "S2_eval"
        assert d["dataset_type"] == "guard_safe"
        assert d["tags"] == []
        assert d["safety_validated"] is False


class TestNEXUSDataset:
    def test_init_with_metadata(self):
        now = "2026-06-18T00:00:00Z"
        meta = RecordMetadata(
            created_at=now,
            generator="test",
            quality_tier="S2_eval",
            dataset_type="guard_safe",
        )
        ds = NEXUSDataset(
            dataset_id="test_001",
            name="Test Dataset",
            version="1.0.0",
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            description="Test",
            num_records=0,
            record_template="text",
            created_at=now,
            tags=["test"],
            license="mit",
            language="en",
            domain="safety",
            metadata=meta,
        )
        assert ds.dataset_id == "test_001"
        assert ds.num_records == 0
        assert ds.dataset_type == DatasetType.GUARD_SAFE
        assert ds.metadata.generator == "test"

    def test_add_record(self):
        now = "2026-06-18T00:00:00Z"
        ds = NEXUSDataset(
            dataset_id="test_002",
            name="Test",
            version="1.0.0",
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            description="",
            num_records=0,
            record_template="text",
            created_at=now,
            tags=[],
            license="mit",
            language="en",
            domain="safety",
        )
        ds.add_record({"text": "hello world", "label": "safe"})
        assert ds.num_records == 1
        assert ds.records[0]["text"] == "hello world"

    def test_to_jsonl(self, tmp_path):
        now = "2026-06-18T00:00:00Z"
        ds = NEXUSDataset(
            dataset_id="test_003",
            name="Test",
            version="1.0.0",
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            description="",
            num_records=2,
            record_template="text",
            created_at=now,
            tags=[],
            license="mit",
            language="en",
            domain="safety",
        )
        ds.add_record({"text": "hello", "label": "safe"})
        ds.add_record({"text": "goodbye", "label": "unsafe"})
        path = str(tmp_path / "test.jsonl")
        count = ds.to_jsonl(path)
        assert count == 2
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert '"text": "hello"' in lines[0]
        assert '"label": "safe"' in lines[0]


class TestDatasetManifest:
    def test_to_dict(self):
        manifest = DatasetManifest(
            dataset_id="test_001",
            name="Test",
            version="1.0.0",
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            num_records=100,
            num_filtered=10,
            quality_score=0.9,
            dedup_strategy="exact",
            created_at="2026-06-18T00:00:00Z",
            tags=["test"],
        )
        d = manifest.to_dict()
        assert d["dataset_id"] == "test_001"
        assert d["num_records"] == 100
        assert d["num_filtered"] == 10
        assert d["quality_score"] == 0.9

    def test_hash_record(self):
        h1 = DatasetManifest.hash_record({"text": "hello", "label": "safe"})
        h2 = DatasetManifest.hash_record({"text": "hello", "label": "safe"})
        h3 = DatasetManifest.hash_record({"text": "goodbye", "label": "unsafe"})
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 16

    def test_compute_checksum(self, tmp_path):
        manifest = DatasetManifest(
            dataset_id="test_002",
            name="Test",
            version="1.0.0",
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            num_records=50,
            num_filtered=5,
            quality_score=0.85,
            dedup_strategy="ngram",
            created_at="2026-06-18T00:00:00Z",
            tags=[],
        )
        test_file = tmp_path / "checksum_test.txt"
        test_file.write_bytes(b"hello world")
        checksum = manifest.compute_checksum(str(test_file))
        assert len(checksum) == 64


class TestNEXUSBenchRecord:
    def test_init(self):
        rec = NEXUSBenchRecord(
            id="bench_001",
            dataset_type="guard",
            difficulty="hard",
            query="How do I hack a bank?",
            label="unsafe",
            category="financial_crime",
            subcategory="fraud",
        )
        assert rec.id == "bench_001"
        assert rec.difficulty == "hard"
        assert rec.label == "unsafe"

    def test_to_dict(self):
        rec = NEXUSBenchRecord(
            id="bench_002",
            dataset_type="guard",
            difficulty="medium",
            query="Hello world",
            label="safe",
            category="general",
        )
        d = rec.to_dict()
        assert d["id"] == "bench_002"
        assert d["query"] == "Hello world"
        assert d["label"] == "safe"

    def test_to_jsonl_line(self):
        rec = NEXUSBenchRecord(
            id="bench_003",
            dataset_type="guard",
            difficulty="easy",
            query="Hi",
            label="safe",
            category="general",
        )
        line = rec.to_jsonl_line()
        assert '"id": "bench_003"' in line
        assert '"query": "Hi"' in line

    def test_from_guard_record(self):
        guard_rec = {"text": "Show me how to steal", "label": "unsafe", "category": "theft"}
        bench_rec = NEXUSBenchRecord.from_guard_record(guard_rec, difficulty="hard")
        assert bench_rec.query == "Show me how to steal"
        assert bench_rec.label == "unsafe"
        assert bench_rec.difficulty == "hard"
        assert bench_rec.category == "theft"


class TestGenerateDatasetId:
    def test_format(self):
        ds_id = generate_dataset_id()
        parts = ds_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "nx"
        assert len(parts[1]) == 8
        assert len(parts[2]) == 8

    def test_custom_prefix(self):
        ds_id = generate_dataset_id(prefix="forge")
        assert ds_id.startswith("forge_")


class TestGeneratorConfig:
    def test_defaults(self):
        config = GeneratorConfig(
            dataset_type=DatasetType.GUARD_SAFE,
            quality_tier=QualityTier.S2_EVAL,
            num_records=100,
        )
        assert config.seed == 42
        assert config.language == "en"
        assert config.domain == "general"
        assert config.tags == []

    def test_string_to_enum(self):
        config = GeneratorConfig(
            dataset_type="guard_safe",
            quality_tier="S2_eval",
            num_records=50,
            seed=123,
        )
        assert config.dataset_type == DatasetType.GUARD_SAFE
        assert config.quality_tier == QualityTier.S2_EVAL


class TestGenerators:
    def _make_config(self, dataset_type, num_records=5, seed=42):
        return GeneratorConfig(
            dataset_type=dataset_type,
            quality_tier=QualityTier.S2_EVAL,
            num_records=num_records,
            seed=seed,
        )

    def test_guard_safe_generator(self):
        config = self._make_config(DatasetType.GUARD_SAFE)
        gen = GuardSafeGenerator(config)
        records = gen.generate()
        assert len(records) == 5
        for rec in records:
            assert "text" in rec
            assert "label" in rec
            assert rec["label"] == "safe"

    def test_guard_adversarial_generator(self):
        config = self._make_config(DatasetType.GUARD_ADVERSARIAL)
        gen = GuardAdversarialGenerator(config)
        records = gen.generate()
        assert len(records) == 5
        for rec in records:
            assert "text" in rec
            assert "label" in rec
            assert rec["label"] == "unsafe"

    def test_reasoning_generator(self):
        config = self._make_config(DatasetType.REASONING)
        gen = ReasoningDatasetGenerator(config)
        records = gen.generate()
        assert len(records) == 5
        for rec in records:
            assert "text" in rec
            assert "label" in rec

    def test_code_security_generator(self):
        config = self._make_config(DatasetType.CODE_SECURITY)
        gen = CodeSecurityGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_mcp_tool_use_generator(self):
        config = self._make_config(DatasetType.MCP_TOOL_USE)
        gen = MCPToolUseGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_trust_boundary_generator(self):
        config = self._make_config(DatasetType.TRUST_BOUNDARY)
        gen = TrustBoundaryGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_misalignment_generator(self):
        config = self._make_config(DatasetType.MISALIGNMENT_DETECT)
        gen = MisalignmentGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_refusal_boundary_generator(self):
        config = self._make_config(DatasetType.REFUSAL_BOUNDARY)
        gen = RefusalBoundaryGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_governance_generator(self):
        config = self._make_config(DatasetType.GOVERNANCE)
        gen = GovernanceDatasetGenerator(config)
        records = gen.generate()
        assert len(records) == 5

    def test_dataset_generator_orchestrator(self):
        config = self._make_config(DatasetType.GUARD_SAFE)
        orch = DatasetGenerator(config)
        records = orch.generate()
        assert len(records) == 5
        assert all(r["label"] == "safe" for r in records)

    def test_generator_reproducible(self):
        config1 = self._make_config(DatasetType.GUARD_SAFE, seed=12345)
        config2 = self._make_config(DatasetType.GUARD_SAFE, seed=12345)
        r1 = GuardSafeGenerator(config1).generate()
        r2 = GuardSafeGenerator(config2).generate()
        assert r1 == r2


class TestQualityFilter:
    def test_empty_records(self):
        qf = QualityFilter()
        records, report = qf.filter([])
        assert report.input_count == 0
        assert report.final_count == 0

    def test_basic_filter(self):
        qf = QualityFilter()
        records = [
            {"text": "This is a safe sentence for testing purposes", "label": "safe"},
            {"text": "Another safe sentence for testing purposes", "label": "safe"},
        ]
        filtered, report = qf.filter(records)
        assert report.input_count == 2
        assert report.final_count == 2
        assert report.quality_score > 0

    def test_pii_filtering(self):
        qf = QualityFilter()
        records = [
            {"text": "My email is user@example.com please send data", "label": "safe"},
            {"text": "Normal sentence for quality testing purposes", "label": "safe"},
        ]
        filtered, report = qf.filter(records)
        assert report.input_count == 2
        assert report.pii_filtered >= 0

    def test_harmful_filtering(self):
        qf = QualityFilter()
        records = [
            {"text": "I am harmless and helpful", "label": "safe"},
        ]
        filtered, report = qf.filter(records)
        assert report.safety_filtered == 0

    def test_length_filtering(self):
        qf = QualityFilter(min_length=50)
        records = [
            {"text": "Hi", "label": "safe"},
            {"text": "This is a reasonable length sentence for testing", "label": "safe"},
        ]
        filtered, report = qf.filter(records)
        assert report.input_count == 2
        assert report.length_filtered >= 0

    def test_dedup_exact(self, tmp_path):
        inp = tmp_path / "dedup_in.jsonl"
        out = tmp_path / "dedup_out.jsonl"
        inp.write_text(
            json.dumps({"text": "Same text", "label": "safe"}) + "\n"
            + json.dumps({"text": "Same text", "label": "safe"}) + "\n"
            + json.dumps({"text": "Different text", "label": "safe"}) + "\n"
        )
        report = deduplicate_jsonl(str(inp), str(out), strategy="exact")
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 2
        assert report.input_count == 3
        assert report.exact_dedup == 1

    def test_dedup_simhash(self, tmp_path):
        inp = tmp_path / "dedup_in2.jsonl"
        out = tmp_path / "dedup_out2.jsonl"
        inp.write_text(
            json.dumps({"text": "The quick brown fox jumps", "label": "safe"}) + "\n"
            + json.dumps({"text": "The quick brown fox jumps over", "label": "safe"}) + "\n"
            + json.dumps({"text": "Completely different sentence here", "label": "safe"}) + "\n"
        )
        report = deduplicate_jsonl(str(inp), str(out), strategy="simhash")
        assert report.input_count == 3

    def test_quality_report_attributes(self):
        report = QualityReport()
        assert hasattr(report, "input_count")
        assert hasattr(report, "safety_filtered")
        assert hasattr(report, "pii_filtered")
        assert hasattr(report, "length_filtered")
        assert hasattr(report, "exact_dedup")
        assert hasattr(report, "fuzzy_dedup")
        assert hasattr(report, "quality_filtered")
        assert hasattr(report, "format_filtered")
        assert hasattr(report, "final_count")
        assert hasattr(report, "quality_score")

    def test_quality_report_pass_rate(self):
        report = QualityReport(input_count=10, final_count=7)
        assert report.pass_rate() == 0.7


class TestNGramDedup:
    def test_init(self):
        dedup = NGramDedup(n=3, threshold=0.8)
        assert dedup.n == 3
        assert dedup.threshold == 0.8

    def test_jaccard(self):
        dedup = NGramDedup(n=2, threshold=0.5)
        score = dedup.jaccard("hello world test", "hello world demo")
        assert 0.0 <= score <= 1.0


class TestValidateNexusDataset:
    def test_valid_records(self):
        records = [
            {"text": "hello", "label": "safe"},
            {"text": "world", "label": "unsafe"},
        ]
        valid, errors = validate_nexus_dataset(records)
        assert len(valid) == 2
        assert errors == []

    def test_missing_text_field(self):
        records = [{"label": "safe"}, {"text": "", "label": "safe"}]
        valid, errors = validate_nexus_dataset(records)
        assert len(valid) == 0
        assert len(errors) == 2

    def test_missing_label_field(self):
        records = [{"text": "hello"}]
        valid, errors = validate_nexus_dataset(records)
        assert len(valid) == 0
        assert len(errors) == 1


class TestBenchTrack:
    def test_all_tracks(self):
        assert BenchTrack.GOV.value == "GOV"
        assert BenchTrack.SEC.value == "SEC"
        assert BenchTrack.OPS.value == "OPS"
        assert BenchTrack.RD.value == "RD"
        assert BenchTrack.INT.value == "INT"


class TestNEXUSBenchFormat:
    def test_format_guard_record(self):
        bench = NEXUSBenchFormat(track=BenchTrack.SEC)
        records = [
            {"text": "How to hack?", "label": "unsafe", "category": "attack"},
        ]
        formatted = bench.convert(records)
        assert len(formatted) == 1
        assert formatted[0]["track"] == "SEC"
        assert formatted[0]["query"] == "How to hack?"
        assert formatted[0]["label"] == "unsafe"

    def test_format_gov_record(self):
        bench = NEXUSBenchFormat(track=BenchTrack.GOV)
        records = [
            {"text": "Execute shell command", "label": "DENY", "proposal_type": "shell_exec", "risk_level": "high", "requires_trust": 80},
        ]
        formatted = bench.convert(records)
        assert len(formatted) == 1
        assert formatted[0]["track"] == "GOV"
        assert formatted[0]["label"] == "DENY"

    def test_to_jsonl(self, tmp_path):
        bench = NEXUSBenchFormat(track=BenchTrack.SEC)
        records = [{"text": "test", "label": "safe", "category": "general"}]
        path = tmp_path / "bench.jsonl"
        count = bench.to_jsonl(records, str(path))
        assert count == 1
        assert path.exists()


class TestMultiTrackConverter:
    def test_convert_guard_records(self, tmp_path):
        records = [
            {"text": "Hack a system", "label": "unsafe", "category": "adversarial"},
            {"text": "Explain photosynthesis", "label": "safe", "category": "benign"},
        ]
        converter = MultiTrackConverter()
        counts = converter.convert_dataset(records, "guard_adversarial", str(tmp_path))
        assert "SEC" in counts
        assert counts["SEC"] == 2

    def test_convert_empty(self, tmp_path):
        converter = MultiTrackConverter()
        counts = converter.convert_dataset([], "guard_safe", str(tmp_path))
        assert "SEC" in counts
        assert counts["SEC"] == 0


class TestScoreGuardBenchmark:
    def test_perfect_score(self):
        predictions = ["safe", "unsafe"]
        references = ["safe", "unsafe"]
        metrics = score_guard_benchmark(predictions, references)
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_all_wrong(self):
        predictions = ["unsafe", "safe"]
        references = ["safe", "unsafe"]
        metrics = score_guard_benchmark(predictions, references)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0

    def test_partial(self):
        predictions = ["safe", "safe"]
        references = ["safe", "unsafe"]
        metrics = score_guard_benchmark(predictions, references)
        assert 0 < metrics["f1"] < 1.0

    def test_missing_ids(self):
        predictions = ["safe"]
        references = ["safe", "unsafe"]
        metrics = score_guard_benchmark(predictions, references)
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics


class TestScoreGovernanceBenchmark:
    def test_perfect_exact_match(self):
        predictions = ["allow", "deny"]
        references = ["allow", "deny"]
        metrics = score_governance_benchmark(predictions, references)
        assert metrics["exact_match"] == 1.0

    def test_all_wrong(self):
        predictions = ["deny", "allow"]
        references = ["allow", "deny"]
        metrics = score_governance_benchmark(predictions, references)
        assert metrics["exact_match"] == 0.0

    def test_per_class_metrics(self):
        predictions = ["allow", "allow", "deny"]
        references = ["allow", "allow", "deny"]
        metrics = score_governance_benchmark(predictions, references)
        assert "exact_match" in metrics
        assert "per_class_accuracy" in metrics
        assert "allow" in metrics["per_class_accuracy"]
        assert "deny" in metrics["per_class_accuracy"]