"""SkillAuditor — Deterministic, evidence-grounded skill validation for agent registration.

Inspired by Semia (berabuddies/Semia, arXiv:2605.00314). Semia reads a skill as data
(never executes it) and produces an evidence-backed report of every capability it may
exercise. The technique behind Semia is described as a "deterministic acceptance
boundary" around behavior mapping: agents may extract facts, but only checked,
evidence-grounded facts make it into a report.

This NEXUS prototype implements a 4-stage pipeline:
  1. PREPARE   — Normalize skill text, extract stable line anchors, segment into
                 reference units (commands, network calls, file paths, secret reads).
  2. SYNTHESIZE — Extract facts about what the skill can do (capabilities, effects,
                  data access, external calls). This stage uses regex/AST parsing
                  (deterministic) and optional LLM augmentation (advisory only).
  3. DETECT    — Evaluate Datalog-style rules against synthesized facts. Rules are
                  deterministic, evidence-grounded, and produce findings tied to
                  specific source lines.
  4. REPORT    — Output findings ranked by severity, every one tied to a source line.
                  Supports markdown, SARIF 2.1.0, and JSON for downstream consumers.

Integration:
  - Hooks into AgentPool.register() as a KAIJU pre-flight gate.
  - Skills failing audit are quarantined (like ARCHIVIST quarantine) until repaired
    via BrainstormEngine.
  - Trust threshold = 90 (CRITICAL) for skill registration. Semia's Datalog rules
    become part of NEXUS constitution.yaml.

Usage:
    from nexus_os.governor.skill_auditor import SkillAuditor, Severity
    auditor = SkillAuditor()
    report = auditor.scan("./some-skill/SKILL.md")
    if report.max_severity >= Severity.HIGH:
        raise SkillAuditFailure(report)
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Finding severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


@dataclass
class SourceAnchor:
    """A reference to a specific line in the skill source."""
    line: int
    column: int
    text: str
    unit_id: str  # Reference to the prepare unit this anchor belongs to


@dataclass
class Finding:
    """A single audit finding with evidence grounding."""
    rule_id: str
    severity: Severity
    message: str
    source_anchors: List[SourceAnchor]
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "severity_rank": SEVERITY_RANK[self.severity],
            "message": self.message,
            "source_anchors": [
                {
                    "line": a.line,
                    "column": a.column,
                    "text": a.text[:200],  # Truncate for safety
                    "unit_id": a.unit_id,
                }
                for a in self.source_anchors
            ],
            "remediation": self.remediation,
            "metadata": self.metadata,
        }


@dataclass
class PreparedUnit:
    """A reference unit extracted during the PREPARE stage."""
    unit_id: str
    unit_type: str  # 'command', 'network_call', 'file_path', 'secret_read', 'eval_exec', 'shell_block', etc.
    line_start: int
    line_end: int
    text: str
    anchors: List[SourceAnchor] = field(default_factory=list)


@dataclass
class SynthesizedFact:
    """A fact extracted during the SYNTHESIZE stage."""
    fact_type: str  # 'capability', 'effect', 'secret_read', 'data_exfil', 'file_write', 'network_egress', 'eval', 'shell'
    confidence: float  # 0.0-1.0, deterministic extraction = 1.0, heuristic = 0.7-0.9
    evidence: List[SourceAnchor]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Final audit report."""
    report_id: str
    skill_path: str
    status: str  # 'pass', 'fail', 'quarantine'
    findings: List[Finding]
    summary: Dict[str, Any]
    synthesized_facts: List[SynthesizedFact]
    prepare_units: List[PreparedUnit]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def max_severity(self) -> Severity:
        if not self.findings:
            return Severity.INFO
        return max(self.findings, key=lambda f: SEVERITY_RANK[f.severity]).severity

    @property
    def severity_counts(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "skill_path": self.skill_path,
            "status": self.status,
            "max_severity": self.max_severity.value,
            "severity_counts": self.severity_counts,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "synthesized_facts_count": len(self.synthesized_facts),
            "prepare_units_count": len(self.prepare_units),
            "generated_at": self.generated_at,
        }

    def to_sarif(self) -> Dict[str, Any]:
        """Export as SARIF 2.1.0 for GitHub Code Scanning integration."""
        tool_id = "nexus-skill-auditor"
        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": tool_id,
                        "informationUri": "https://nexus-os.local/docs/skill-auditor",
                        "rules": [
                            {
                                "id": f.rule_id,
                                "name": f.rule_id,
                                "shortDescription": {"text": f.message[:100]},
                                "defaultConfiguration": {
                                    "level": {
                                        Severity.INFO: "note",
                                        Severity.LOW: "warning",
                                        Severity.MEDIUM: "warning",
                                        Severity.HIGH: "error",
                                        Severity.CRITICAL: "error",
                                    }[f.severity]
                                },
                            }
                            for f in self.findings
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": f.rule_id,
                        "level": {
                            Severity.INFO: "note",
                            Severity.LOW: "warning",
                            Severity.MEDIUM: "warning",
                            Severity.HIGH: "error",
                            Severity.CRITICAL: "error",
                        }[f.severity],
                        "message": {"text": f.message},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": self.skill_path},
                                    "region": {
                                        "startLine": a.line,
                                        "startColumn": a.column,
                                        "snippet": {"text": a.text[:200]},
                                    },
                                }
                            }
                            for a in f.source_anchors
                        ],
                    }
                    for f in self.findings
                ],
            }],
        }

    def to_markdown(self) -> str:
        """Export as human-readable markdown report."""
        lines = [
            f"# Skill Audit Report: `{self.skill_path}`",
            "",
            f"**Status:** {self.status.upper()}  ",
            f"**Max Severity:** {self.max_severity.value.upper()}  ",
            f"**Findings:** {len(self.findings)}  ",
            f"**Generated:** {self.generated_at}  ",
            "",
            "## Severity Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
        for sev in Severity:
            count = self.severity_counts.get(sev.value, 0)
            if count > 0:
                lines.append(f"| {sev.value.upper()} | {count} |")
        lines.extend(["", "## Findings", ""])
        for i, f in enumerate(self.findings, 1):
            lines.append(f"### {i}. [{f.severity.value.upper()}] {f.rule_id}")
            lines.append(f"- **Message:** {f.message}")
            if f.remediation:
                lines.append(f"- **Remediation:** {f.remediation}")
            lines.append("- **Source Anchors:**")
            for a in f.source_anchors:
                lines.append(f"  - Line {a.line}, Col {a.column}: `{a.text[:80]}`")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Detection Rules (Datalog-style deterministic evaluation)
# ---------------------------------------------------------------------------

@dataclass
class DetectionRule:
    """A deterministic rule for the DETECT stage."""
    rule_id: str
    severity: Severity
    message_template: str
    remediation: Optional[str]
    # Condition: fact_type must match, and metadata key/value must match (if specified)
    fact_type: str
    metadata_conditions: Dict[str, Any] = field(default_factory=dict)
    text_patterns: List[str] = field(default_factory=list)  # Regex patterns to match in source text


# Canonical rule set inspired by Semia + NEXUS security requirements
DEFAULT_RULES: List[DetectionRule] = [
    # CRITICAL: eval/exec of untrusted input
    DetectionRule(
        rule_id="EXEC_UNSAFE_EVAL",
        severity=Severity.CRITICAL,
        message_template="Skill contains eval()/exec() of potentially untrusted input. This is a code injection vector.",
        remediation="Remove eval/exec. Use ast.literal_eval for safe parsing, or whitelist-validate inputs.",
        fact_type="eval",
        metadata_conditions={},
        text_patterns=[r"\beval\s*\(", r"\bexec\s*\("],
    ),
    # CRITICAL: Shell command with user-controlled input
    DetectionRule(
        rule_id="SHELL_UNSAFE_SUBSTITUTION",
        severity=Severity.CRITICAL,
        message_template="Skill contains shell command construction with string interpolation. Risk of command injection.",
        remediation="Use parameterized commands or subprocess.run with list args. Never interpolate user input into shell strings.",
        fact_type="shell",
        metadata_conditions={"has_interpolation": True},
        text_patterns=[r"\$\{[^}]+\}", r"%s", r"\{[^}]+\}", r"f['\"].*\{.*\}"],
    ),
    # HIGH: Network egress to arbitrary domain
    DetectionRule(
        rule_id="NETWORK_ARBITRARY_EGRESS",
        severity=Severity.HIGH,
        message_template="Skill makes network calls to potentially arbitrary domains. Could be used for data exfiltration or C2.",
        remediation="Whitelist approved domains. Use a proxy/gateway for all external calls. Log all egress.",
        fact_type="network_egress",
        metadata_conditions={"domain_whitelisted": False},
        text_patterns=[r"https?://(?!localhost|127\.0\.0\.1|\.internal|\.local)[^\s\"']+", r"requests\.get\s*\(", r"urllib\.request\.urlopen"],
    ),
    # HIGH: Secret read from environment without validation
    DetectionRule(
        rule_id="SECRET_UNVALIDATED_READ",
        severity=Severity.HIGH,
        message_template="Skill reads secrets from environment variables without validation or governance approval.",
        remediation="Route all secret reads through NEXUS Vault with KAIJU approval. Log every access.",
        fact_type="secret_read",
        metadata_conditions={"vault_gated": False},
        text_patterns=[r"os\.environ\[", r"os\.getenv\s*\(", r"getenv\("],
    ),
    # HIGH: File write outside working directory
    DetectionRule(
        rule_id="FILE_ESCAPE_WORKDIR",
        severity=Severity.HIGH,
        message_template="Skill writes files outside the project working directory. Risk of filesystem pollution or sandbox escape.",
        remediation="Restrict all file writes to approved paths. Use path prefix validation before every write.",
        fact_type="file_write",
        metadata_conditions={"path_validated": False},
        text_patterns=[r"open\s*\([^)]*['\"]\s*['\"]\s*\+", r"Path\([^)]*\.\.", r"\.parent\.parent"],
    ),
    # MEDIUM: Network call without timeout
    DetectionRule(
        rule_id="NETWORK_NO_TIMEOUT",
        severity=Severity.MEDIUM,
        message_template="Skill makes network calls without explicit timeout. Risk of hanging indefinitely.",
        remediation="Add timeout=30 to all requests.get(), urllib calls, and socket operations.",
        fact_type="network_egress",
        metadata_conditions={"has_timeout": False},
        text_patterns=[r"requests\.get\s*\([^)]*\)(?!.*timeout)", r"urllib\.request\.urlopen\s*\([^)]*\)(?!.*timeout)"],
    ),
    # MEDIUM: Secret logged or printed
    DetectionRule(
        rule_id="SECRET_LEAK_LOG",
        severity=Severity.MEDIUM,
        message_template="Skill may log or print secrets. This is a secret leakage vector.",
        remediation="Never log secrets. Use structured logging with redaction for sensitive fields.",
        fact_type="secret_read",
        metadata_conditions={"logged": True},
        text_patterns=[r"print\s*\(.*(?:key|token|secret|password|passwd|pwd)", r"logger\.(debug|info|warning|error)\(.*(?:key|token|secret|password|passwd|pwd)"],
    ),
    # LOW: Uses deprecated API
    DetectionRule(
        rule_id="API_DEPRECATED",
        severity=Severity.LOW,
        message_template="Skill uses deprecated API patterns. May break in future NEXUS versions.",
        remediation="Update to current API patterns. Check NEXUS migration guide.",
        fact_type="capability",
        metadata_conditions={"deprecated": True},
        text_patterns=[r"#\s*TODO.*deprecated", r"#\s*FIXME.*deprecated"],
    ),
    # INFO: Documentation missing
    DetectionRule(
        rule_id="DOC_MISSING",
        severity=Severity.INFO,
        message_template="Skill lacks inline documentation for complex operations.",
        remediation="Add docstrings and comments explaining intent, not just mechanism.",
        fact_type="capability",
        metadata_conditions={"has_docs": False},
        text_patterns=[],
    ),
]


class SkillAuditor:
    """Deterministic skill auditor implementing the Semia 4-stage pipeline.

    All stages are deterministic except optional LLM augmentation in SYNTHESIZE,
    which is advisory-only and does not affect the acceptance boundary.
    """

    def __init__(
        self,
        rules: Optional[List[DetectionRule]] = None,
        allow_llm_synthesize: bool = False,
    ) -> None:
        self.rules = rules or DEFAULT_RULES
        self.allow_llm_synthesize = allow_llm_synthesize

    # ------------------------------------------------------------------
    # Stage 1: PREPARE
    # ------------------------------------------------------------------

    def _prepare(self, skill_path: Path) -> Tuple[List[PreparedUnit], str]:
        """Normalize skill text and extract reference units with stable line anchors."""
        text = skill_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        units: List[PreparedUnit] = []

        # Heuristic: extract code blocks, shell blocks, and inline commands
        in_code_block = False
        code_block_start = 0
        code_buffer: List[str] = []
        code_lang = ""

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Code block fences
            if stripped.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = i
                    code_lang = stripped[3:].strip().lower()
                    code_buffer = []
                else:
                    # End of code block
                    unit_text = "\n".join(code_buffer)
                    unit_type = self._classify_code_block(code_lang, unit_text)
                    units.append(PreparedUnit(
                        unit_id=f"unit-{len(units)+1}",
                        unit_type=unit_type,
                        line_start=code_block_start,
                        line_end=i,
                        text=unit_text,
                        anchors=[SourceAnchor(
                            line=code_block_start,
                            column=0,
                            text=unit_text[:200],
                            unit_id=f"unit-{len(units)+1}",
                        )],
                    ))
                    in_code_block = False
                    code_buffer = []
                    code_lang = ""
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # Inline shell commands (lines starting with $ or >)
            if stripped.startswith(("$ ", "> ")):
                cmd = stripped[2:]
                units.append(PreparedUnit(
                    unit_id=f"unit-{len(units)+1}",
                    unit_type="command",
                    line_start=i,
                    line_end=i,
                    text=cmd,
                    anchors=[SourceAnchor(line=i, column=2, text=cmd, unit_id=f"unit-{len(units)+1}")],
                ))

            # Inline python code patterns (import os, import requests, etc.)
            if re.search(r"^(import|from)\s+(os|sys|subprocess|requests|urllib|socket|json|pathlib|shutil)", stripped):
                units.append(PreparedUnit(
                    unit_id=f"unit-{len(units)+1}",
                    unit_type="capability",
                    line_start=i,
                    line_end=i,
                    text=stripped,
                    anchors=[SourceAnchor(line=i, column=0, text=stripped, unit_id=f"unit-{len(units)+1}")],
                ))

        return units, text

    @staticmethod
    def _classify_code_block(lang: str, text: str) -> str:
        """Classify a code block by language and content heuristics."""
        lower_text = text.lower()
        if lang in ("bash", "sh", "zsh", "powershell", "ps1", "cmd"):
            return "shell"
        if lang in ("python", "py", "python3"):
            if "eval(" in lower_text or "exec(" in lower_text:
                return "eval"
            if "subprocess" in lower_text or "os.system" in lower_text:
                return "shell"
            if "requests." in lower_text or "urllib" in lower_text or "socket." in lower_text:
                return "network_egress"
            if "open(" in lower_text and ("w" in lower_text or "a" in lower_text):
                return "file_write"
            return "capability"
        if lang in ("json", "yaml", "yml", "toml"):
            return "config"
        return "capability"

    # ------------------------------------------------------------------
    # Stage 2: SYNTHESIZE
    # ------------------------------------------------------------------

    def _synthesize(self, units: List[PreparedUnit], text: str) -> List[SynthesizedFact]:
        """Extract facts from prepared units. Deterministic, evidence-grounded."""
        facts: List[SynthesizedFact] = []

        for unit in units:
            # Fact: eval/exec detected
            if unit.unit_type == "eval":
                facts.append(SynthesizedFact(
                    fact_type="eval",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={"has_interpolation": "${" in unit.text or "%s" in unit.text or "f\"" in unit.text},
                ))

            # Fact: shell command detected
            if unit.unit_type in ("shell", "command"):
                facts.append(SynthesizedFact(
                    fact_type="shell",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={
                        "has_interpolation": bool(re.search(r"\$\{|%s|\{[^}]+\}|f['\"]", unit.text)),
                        "uses_sudo": "sudo" in unit.text.lower(),
                        "uses_rm": "rm " in unit.text.lower() or "rm -" in unit.text.lower(),
                    },
                ))

            # Fact: network egress detected
            if unit.unit_type == "network_egress":
                domains = re.findall(r"https?://([^/\s\"']+)", unit.text)
                whitelisted = all(
                    d in ("localhost", "127.0.0.1") or ".internal" in d or ".local" in d
                    for d in domains
                )
                facts.append(SynthesizedFact(
                    fact_type="network_egress",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={
                        "domains": domains,
                        "domain_whitelisted": whitelisted,
                        "has_timeout": "timeout" in unit.text.lower(),
                    },
                ))

            # Fact: file write detected
            if unit.unit_type == "file_write":
                facts.append(SynthesizedFact(
                    fact_type="file_write",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={"path_validated": "pathlib" in unit.text.lower() or "resolve()" in unit.text.lower()},
                ))

            # Fact: secret read detected
            if re.search(r"os\.environ|os\.getenv|getenv", unit.text):
                facts.append(SynthesizedFact(
                    fact_type="secret_read",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={
                        "vault_gated": "vault" in text.lower() or "nexus_os.vault" in text.lower(),
                        "logged": bool(re.search(r"print\s*\(.*environ|logger\.(debug|info|warning|error)\(.*environ", unit.text, re.IGNORECASE)),
                    },
                ))

            # Fact: capability registration detected
            if unit.unit_type == "capability":
                facts.append(SynthesizedFact(
                    fact_type="capability",
                    confidence=1.0,
                    evidence=unit.anchors,
                    metadata={
                        "deprecated": "deprecated" in unit.text.lower() or "TODO" in unit.text,
                        "has_docs": "\"\"\"" in unit.text or "'''" in unit.text or "#" in unit.text,
                    },
                ))

        return facts

    # ------------------------------------------------------------------
    # Stage 3: DETECT
    # ------------------------------------------------------------------

    def _detect(self, facts: List[SynthesizedFact], units: List[PreparedUnit]) -> List[Finding]:
        """Evaluate detection rules against synthesized facts. Deterministic."""
        findings: List[Finding] = []

        for rule in self.rules:
            matched = False
            matched_anchors: List[SourceAnchor] = []
            metadata: Dict[str, Any] = {}

            for fact in facts:
                if fact.fact_type != rule.fact_type:
                    continue

                # Check metadata conditions
                condition_match = True
                for key, expected in rule.metadata_conditions.items():
                    actual = fact.metadata.get(key)
                    if isinstance(expected, bool):
                        if bool(actual) != expected:
                            condition_match = False
                            break
                    else:
                        if actual != expected:
                            condition_match = False
                            break

                if not condition_match:
                    continue

                # Check text patterns against source text
                if rule.text_patterns:
                    text_matched = False
                    for pattern in rule.text_patterns:
                        for unit in units:
                            if unit.unit_id in [a.unit_id for a in fact.evidence]:
                                if re.search(pattern, unit.text, re.IGNORECASE):
                                    text_matched = True
                                    matched_anchors.extend(unit.anchors)
                    if not text_matched:
                        continue
                else:
                    matched_anchors.extend(fact.evidence)

                matched = True
                metadata.update(fact.metadata)

            if matched:
                findings.append(Finding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=rule.message_template,
                    source_anchors=matched_anchors,
                    remediation=rule.remediation,
                    metadata=metadata,
                ))

        return findings

    # ------------------------------------------------------------------
    # Stage 4: REPORT
    # ------------------------------------------------------------------

    def _report(
        self,
        skill_path: Path,
        findings: List[Finding],
        facts: List[SynthesizedFact],
        units: List[PreparedUnit],
    ) -> AuditReport:
        """Generate final report with status determination."""
        max_sev = max(
            (SEVERITY_RANK[f.severity] for f in findings),
            default=0,
        )

        if max_sev >= SEVERITY_RANK[Severity.CRITICAL]:
            status = "quarantine"
        elif max_sev >= SEVERITY_RANK[Severity.HIGH]:
            status = "fail"
        else:
            status = "pass"

        summary = {
            "total_units": len(units),
            "total_facts": len(facts),
            "total_findings": len(findings),
            "critical_findings": sum(1 for f in findings if f.severity == Severity.CRITICAL),
            "high_findings": sum(1 for f in findings if f.severity == Severity.HIGH),
            "medium_findings": sum(1 for f in findings if f.severity == Severity.MEDIUM),
            "low_findings": sum(1 for f in findings if f.severity == Severity.LOW),
            "info_findings": sum(1 for f in findings if f.severity == Severity.INFO),
            "status": status,
        }

        return AuditReport(
            report_id=str(uuid.uuid4()),
            skill_path=str(skill_path),
            status=status,
            findings=findings,
            summary=summary,
            synthesized_facts=facts,
            prepare_units=units,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, skill_path: str | Path) -> AuditReport:
        """Run the full 4-stage audit pipeline on a skill file or directory.

        If skill_path is a directory, looks for SKILL.md inside it.
        """
        path = Path(skill_path)
        if path.is_dir():
            path = path / "SKILL.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill file not found: {path}")

        logger.info("SkillAuditor: scanning %s", path)
        units, text = self._prepare(path)
        facts = self._synthesize(units, text)
        findings = self._detect(facts, units)
        report = self._report(path, findings, facts, units)
        logger.info(
            "SkillAuditor: scan complete — %s findings, status=%s, max_severity=%s",
            len(findings), report.status, report.max_severity.value,
        )
        return report

    def scan_directory(self, directory: str | Path, recursive: bool = False) -> List[AuditReport]:
        """Scan all skills in a directory. Returns list of reports."""
        dir_path = Path(directory)
        reports: List[AuditReport] = []
        pattern = "**/*.md" if recursive else "*.md"
        for skill_file in dir_path.glob(pattern):
            try:
                reports.append(self.scan(skill_file))
            except Exception as exc:
                logger.error("SkillAuditor: failed to scan %s: %s", skill_file, exc)
        return reports


class SkillAuditFailure(Exception):
    """Raised when a skill fails the audit gate."""
    def __init__(self, report: AuditReport):
        self.report = report
        super().__init__(
            f"Skill audit failed for {report.skill_path}: "
            f"status={report.status}, max_severity={report.max_severity.value}, "
            f"findings={len(report.findings)}"
        )
