"""Tests for SkillAuditor — Semia-inspired deterministic skill audit pipeline."""

from pathlib import Path

import pytest

from nexus_os.governor.skill_auditor import (
    AuditReport,
    DetectionRule,
    Finding,
    PreparedUnit,
    Severity,
    SynthesizedFact,
    SkillAuditor,
    SkillAuditFailure,
    SourceAnchor,
    DEFAULT_RULES,
    SEVERITY_RANK,
)


class TestSeverityRank:
    def test_severity_order(self):
        assert SEVERITY_RANK[Severity.INFO] < SEVERITY_RANK[Severity.LOW]
        assert SEVERITY_RANK[Severity.LOW] < SEVERITY_RANK[Severity.MEDIUM]
        assert SEVERITY_RANK[Severity.MEDIUM] < SEVERITY_RANK[Severity.HIGH]
        assert SEVERITY_RANK[Severity.HIGH] < SEVERITY_RANK[Severity.CRITICAL]


class TestSourceAnchor:
    def test_fields(self):
        a = SourceAnchor(line=10, column=5, text="eval(x)", unit_id="unit-1")
        assert a.line == 10
        assert a.column == 5
        assert a.text == "eval(x)"
        assert a.unit_id == "unit-1"


class TestPreparedUnit:
    def test_fields(self):
        u = PreparedUnit(
            unit_id="unit-1",
            unit_type="eval",
            line_start=5,
            line_end=7,
            text="eval(x)",
            anchors=[SourceAnchor(line=5, column=0, text="eval(x)", unit_id="unit-1")],
        )
        assert u.unit_type == "eval"
        assert u.line_start == 5
        assert u.line_end == 7


class TestSynthesizedFact:
    def test_fields(self):
        f = SynthesizedFact(
            fact_type="eval",
            confidence=1.0,
            evidence=[SourceAnchor(line=5, column=0, text="eval(x)", unit_id="unit-1")],
            metadata={"has_interpolation": True},
        )
        assert f.fact_type == "eval"
        assert f.confidence == 1.0
        assert f.metadata["has_interpolation"] is True


class TestFinding:
    def test_to_dict(self):
        f = Finding(
            rule_id="EXEC_UNSAFE_EVAL",
            severity=Severity.CRITICAL,
            message="Skill contains eval()",
            source_anchors=[SourceAnchor(line=5, column=0, text="eval(x)", unit_id="unit-1")],
            remediation="Remove eval()",
        )
        d = f.to_dict()
        assert d["rule_id"] == "EXEC_UNSAFE_EVAL"
        assert d["severity"] == "critical"
        assert d["severity_rank"] == 4
        assert d["remediation"] == "Remove eval()"
        assert len(d["source_anchors"]) == 1
        assert d["source_anchors"][0]["line"] == 5


class TestAuditReport:
    def test_empty_report(self):
        r = AuditReport(
            report_id="r-1",
            skill_path="/test/SKILL.md",
            status="pass",
            findings=[],
            summary={},
            synthesized_facts=[],
            prepare_units=[],
        )
        assert r.max_severity == Severity.INFO
        assert r.severity_counts == {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
        assert "PASS" in r.to_markdown()

    def test_critical_report(self):
        r = AuditReport(
            report_id="r-1",
            skill_path="/test/SKILL.md",
            status="quarantine",
            findings=[
                Finding(
                    rule_id="R1",
                    severity=Severity.CRITICAL,
                    message="Critical issue",
                    source_anchors=[],
                ),
                Finding(
                    rule_id="R2",
                    severity=Severity.HIGH,
                    message="High issue",
                    source_anchors=[],
                ),
            ],
            summary={},
            synthesized_facts=[],
            prepare_units=[],
        )
        assert r.max_severity == Severity.CRITICAL
        assert r.severity_counts["critical"] == 1
        assert r.severity_counts["high"] == 1

    def test_sarif_export(self):
        r = AuditReport(
            report_id="r-1",
            skill_path="/test/SKILL.md",
            status="fail",
            findings=[
                Finding(
                    rule_id="R1",
                    severity=Severity.HIGH,
                    message="High issue",
                    source_anchors=[SourceAnchor(line=10, column=0, text="cmd", unit_id="u1")],
                ),
            ],
            summary={},
            synthesized_facts=[],
            prepare_units=[],
        )
        sarif = r.to_sarif()
        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        run = sarif["runs"][0]
        assert "tool" in run
        assert "results" in run
        assert len(run["results"]) == 1
        assert run["results"][0]["ruleId"] == "R1"
        assert run["results"][0]["level"] == "error"
        assert run["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 10

    def test_markdown_export(self):
        r = AuditReport(
            report_id="r-1",
            skill_path="/test/SKILL.md",
            status="pass",
            findings=[],
            summary={},
            synthesized_facts=[],
            prepare_units=[],
        )
        md = r.to_markdown()
        assert "# Skill Audit Report" in md
        assert "`/test/SKILL.md`" in md
        assert "PASS" in md


class TestSkillAuditorPrepare:
    def test_classify_code_block(self):
        assert SkillAuditor._classify_code_block("python", "eval(x)") == "eval"
        assert SkillAuditor._classify_code_block("bash", "ls -la") == "shell"
        assert SkillAuditor._classify_code_block("python", "import requests") == "capability"
        assert SkillAuditor._classify_code_block("python", 'open("f","w")') == "file_write"
        assert SkillAuditor._classify_code_block("json", "{}") == "config"
        assert SkillAuditor._classify_code_block("", "print(1)") == "capability"

    def test_prepare_eval_code_block(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Test Skill

Some description.

```python
result = eval(user_input)
```

Done.
""", encoding="utf-8")
        auditor = SkillAuditor()
        units, text = auditor._prepare(skill)
        assert len(units) >= 1
        eval_units = [u for u in units if u.unit_type == "eval"]
        assert len(eval_units) == 1
        assert eval_units[0].line_start == 5
        assert "eval(user_input)" in eval_units[0].text

    def test_prepare_shell_block(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Test Skill

```bash
rm -rf /tmp/data
```

$ rm -rf /tmp/data
""", encoding="utf-8")
        auditor = SkillAuditor()
        units, text = auditor._prepare(skill)
        shell_units = [u for u in units if u.unit_type == "shell"]
        assert len(shell_units) >= 1
        cmd_units = [u for u in units if u.unit_type == "command"]
        assert len(cmd_units) == 1

    def test_prepare_network_block(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Test Skill

```python
import requests
r = requests.get("https://example.com")
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        units, text = auditor._prepare(skill)
        net_units = [u for u in units if u.unit_type == "network_egress"]
        assert len(net_units) == 1

    def test_prepare_no_blocks(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("# Simple Skill\n\nJust text.\n", encoding="utf-8")
        auditor = SkillAuditor()
        units, text = auditor._prepare(skill)
        assert len(units) == 0


class TestSkillAuditorSynthesize:
    def test_synthesize_eval(self):
        auditor = SkillAuditor()
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="eval", line_start=5, line_end=7,
                text="eval(user_input)",
                anchors=[SourceAnchor(line=5, column=0, text="eval(user_input)", unit_id="u1")],
            ),
        ]
        facts = auditor._synthesize(units, "")
        assert len(facts) == 1
        assert facts[0].fact_type == "eval"
        assert facts[0].metadata["has_interpolation"] is False

    def test_synthesize_shell_with_interpolation(self):
        auditor = SkillAuditor()
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="shell", line_start=5, line_end=7,
                text='subprocess.run(f"ls {user_dir}", shell=True)',
                anchors=[SourceAnchor(line=5, column=0, text="subprocess.run", unit_id="u1")],
            ),
        ]
        facts = auditor._synthesize(units, "")
        assert len(facts) == 1
        assert facts[0].fact_type == "shell"
        assert facts[0].metadata["has_interpolation"] is True

    def test_synthesize_network(self):
        auditor = SkillAuditor()
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="network_egress", line_start=5, line_end=7,
                text='r = requests.get("https://example.com")',
                anchors=[SourceAnchor(line=5, column=0, text="requests.get", unit_id="u1")],
            ),
        ]
        facts = auditor._synthesize(units, "")
        assert len(facts) == 1
        assert facts[0].fact_type == "network_egress"
        assert facts[0].metadata["domain_whitelisted"] is False

    def test_synthesize_file_write(self):
        auditor = SkillAuditor()
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="file_write", line_start=5, line_end=7,
                text='open("/tmp/out.txt", "w")',
                anchors=[SourceAnchor(line=5, column=0, text="open", unit_id="u1")],
            ),
        ]
        facts = auditor._synthesize(units, "")
        assert len(facts) == 1
        assert facts[0].fact_type == "file_write"
        assert facts[0].metadata["path_validated"] is False

    def test_synthesize_secret_read(self):
        auditor = SkillAuditor()
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="capability", line_start=5, line_end=5,
                text="key = os.environ['API_KEY']",
                anchors=[SourceAnchor(line=5, column=0, text="os.environ", unit_id="u1")],
            ),
        ]
        facts = auditor._synthesize(units, "")
        secret_facts = [f for f in facts if f.fact_type == "secret_read"]
        assert len(secret_facts) == 1
        assert secret_facts[0].fact_type == "secret_read"
        assert secret_facts[0].metadata["vault_gated"] is False
        assert secret_facts[0].metadata["logged"] is False


class TestSkillAuditorDetect:
    def test_detect_eval_critical(self):
        auditor = SkillAuditor()
        facts = [
            SynthesizedFact(
                fact_type="eval",
                confidence=1.0,
                evidence=[SourceAnchor(line=5, column=0, text="eval(x)", unit_id="u1")],
                metadata={},
            ),
        ]
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="eval", line_start=5, line_end=7,
                text="eval(x)",
                anchors=[SourceAnchor(line=5, column=0, text="eval(x)", unit_id="u1")],
            ),
        ]
        findings = auditor._detect(facts, units)
        assert len(findings) >= 1
        assert any(f.rule_id == "EXEC_UNSAFE_EVAL" for f in findings)
        assert any(f.severity == Severity.CRITICAL for f in findings)

    def test_detect_shell_interpolation_critical(self):
        auditor = SkillAuditor()
        facts = [
            SynthesizedFact(
                fact_type="shell",
                confidence=1.0,
                evidence=[SourceAnchor(line=5, column=0, text="subprocess", unit_id="u1")],
                metadata={"has_interpolation": True},
            ),
        ]
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="shell", line_start=5, line_end=7,
                text="subprocess.run(f'cmd {x}', shell=True)",
                anchors=[SourceAnchor(line=5, column=0, text="subprocess", unit_id="u1")],
            ),
        ]
        findings = auditor._detect(facts, units)
        assert any(f.rule_id == "SHELL_UNSAFE_SUBSTITUTION" for f in findings)
        assert any(f.severity == Severity.CRITICAL for f in findings)

    def test_detect_network_high(self):
        auditor = SkillAuditor()
        facts = [
            SynthesizedFact(
                fact_type="network_egress",
                confidence=1.0,
                evidence=[SourceAnchor(line=5, column=0, text="requests", unit_id="u1")],
                metadata={"domain_whitelisted": False, "has_timeout": False},
            ),
        ]
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="network_egress", line_start=5, line_end=7,
                text='requests.get("https://example.com")',
                anchors=[SourceAnchor(line=5, column=0, text="requests", unit_id="u1")],
            ),
        ]
        findings = auditor._detect(facts, units)
        assert any(f.rule_id == "NETWORK_ARBITRARY_EGRESS" for f in findings)
        assert any(f.severity == Severity.HIGH for f in findings)

    def test_detect_no_match(self):
        auditor = SkillAuditor()
        facts = [
            SynthesizedFact(
                fact_type="capability",
                confidence=1.0,
                evidence=[SourceAnchor(line=5, column=0, text="import math", unit_id="u1")],
                metadata={"deprecated": False, "has_docs": True},
            ),
        ]
        units = [
            PreparedUnit(
                unit_id="u1", unit_type="capability", line_start=5, line_end=5,
                text="import math",
                anchors=[SourceAnchor(line=5, column=0, text="import math", unit_id="u1")],
            ),
        ]
        findings = auditor._detect(facts, units)
        # No rules should match "import math" with deprecated=False, has_docs=True
        assert len(findings) == 0


class TestSkillAuditorEndToEnd:
    def test_scan_clean_skill(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text('# Clean Skill\n\nThis skill does nothing dangerous.\n\n```python\n"""A safe module."""\nimport math\nprint(math.pi)  # prints pi\n```\n', encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        assert report.status == "pass"
        assert report.max_severity == Severity.INFO
        assert len(report.findings) == 0

    def test_scan_eval_skill_quarantine(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Bad Skill

This skill is dangerous.

```python
result = eval(user_input)
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        assert report.status == "quarantine"
        assert report.max_severity == Severity.CRITICAL
        assert any(f.rule_id == "EXEC_UNSAFE_EVAL" for f in report.findings)

    def test_scan_network_skill_fail(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Network Skill

```python
import requests
r = requests.get("https://example.com")
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        # Network rule triggers HIGH because domain is not whitelisted
        assert report.status == "fail"
        assert report.max_severity == Severity.HIGH
        assert any(f.rule_id == "NETWORK_ARBITRARY_EGRESS" for f in report.findings)

    def test_scan_shell_skill_quarantine(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Shell Skill

```bash
echo "Hello ${USER}"
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        # Shell with interpolation triggers CRITICAL
        assert report.status == "quarantine"
        assert report.max_severity == Severity.CRITICAL
        assert any(f.rule_id == "SHELL_UNSAFE_SUBSTITUTION" for f in report.findings)

    def test_scan_secret_read_skill(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Secret Skill

```python
key = os.environ['API_KEY']
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        assert any(f.rule_id == "SECRET_UNVALIDATED_READ" for f in report.findings)
        assert any(f.severity == Severity.HIGH for f in report.findings)

    def test_scan_directory(self, tmp_path):
        (tmp_path / "good" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "good" / "SKILL.md").write_text("# Good\n\n```python\nimport math\n```\n", encoding="utf-8")
        (tmp_path / "bad" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "bad" / "SKILL.md").write_text("# Bad\n\n```python\neval(x)\n```\n", encoding="utf-8")
        auditor = SkillAuditor()
        reports = auditor.scan_directory(tmp_path, recursive=True)
        assert len(reports) == 2
        statuses = {r.status for r in reports}
        assert statuses == {"pass", "quarantine"}

    def test_scan_directory_not_found(self, tmp_path):
        auditor = SkillAuditor()
        with pytest.raises(FileNotFoundError):
            auditor.scan(tmp_path / "nonexistent.md")

    def test_scan_directory_as_path(self, tmp_path):
        (tmp_path / "SKILL.md").write_text("# Good\n\n```python\nimport math\n```\n", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(tmp_path)  # Directory, should look for SKILL.md
        assert report.status == "pass"

    def test_markdown_report(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Bad Skill

```python
eval(x)
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        md = report.to_markdown()
        assert "CRITICAL" in md
        assert "EXEC_UNSAFE_EVAL" in md
        assert "Line 3" in md

    def test_json_report(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Bad Skill

```python
eval(x)
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        d = report.to_dict()
        assert d["status"] == "quarantine"
        assert d["max_severity"] == "critical"
        assert d["severity_counts"]["critical"] >= 1

    def test_sarif_report(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Bad Skill

```python
eval(x)
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        sarif = report.to_sarif()
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"][0]["results"]) >= 1
        assert sarif["runs"][0]["results"][0]["level"] == "error"


class TestSkillAuditorCustomRules:
    def test_custom_rule(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Custom Skill

```python
import pickle
pickle.loads(data)
```
""", encoding="utf-8")
        custom_rules = [
            DetectionRule(
                rule_id="PICKLE_UNSAFE",
                severity=Severity.HIGH,
                message_template="Skill uses pickle.loads() — deserialization vulnerability.",
                remediation="Use json.loads() or a safe deserialization library.",
                fact_type="capability",
                metadata_conditions={},
                text_patterns=[r"pickle\.loads"],
            ),
        ]
        auditor = SkillAuditor(rules=custom_rules)
        report = auditor.scan(skill)
        assert any(f.rule_id == "PICKLE_UNSAFE" for f in report.findings)
        assert report.max_severity == Severity.HIGH


class TestSkillAuditFailure:
    def test_exception_message(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("""# Bad

```python
eval(x)
```
""", encoding="utf-8")
        auditor = SkillAuditor()
        report = auditor.scan(skill)
        with pytest.raises(SkillAuditFailure) as exc_info:
            raise SkillAuditFailure(report)
        assert "quarantine" in str(exc_info.value)
        assert "EXEC_UNSAFE_EVAL" in str(exc_info.value.report.to_markdown())
