"""
reasoning/reasoning_templates.py — FableReasoningEngine Template Engine

Generates structured reasoning templates from extracted patterns, creates
injectable prompt blocks for NEXUS agents, and supports Fable-style,
NEXUS-native, and hybrid reasoning modes with CogER complexity routing.
"""

from enum import Enum
from typing import Dict, List, Optional


class ReasoningStyle(Enum):
    """Supported reasoning styles for template generation."""

    FABLE = "fable"
    NEXUS = "nexus"
    HYBRID = "hybrid"


# ── Canonical reasoning templates ────────────────────────────────────────

_FABLE_5_STEP = """\
## Reasoning Protocol (Fable 5-Step)

Follow this disciplined reasoning chain for every task:

### Step 1: DIAGNOSE — Context Verification
- Never assume environment state. Check before acting.
- Run non-invasive diagnostics: file existence, current config, process status.
- Identify the actual (not assumed) starting state.
- Ask: "What do I KNOW vs what am I ASSUMING?"

### Step 2: OPTIONS — Hypothesis Generation
- Generate at least 2 distinct solution approaches.
- For each option, estimate: effort, risk, reversibility.
- Prefer the option that touches fewest files and has clearest rollback path.

### Step 3: BOUNDARIES — Safety & Scope Analysis
- Explicitly list what NOT to change.
- Identify collateral damage surface: what else depends on the code I'm editing?
- Set a scope boundary: "I will only touch [X, Y, Z]."
- If the blast radius exceeds the task scope, STOP and re-scope.

### Step 4: MINIMAL TOOLING — Precise Tool Selection
- Choose the most precise tool for the job.
- Prefer reading over guessing. Prefer editing over rewriting.
- After each tool call, verify the result before proceeding.
- No batch operations without intermediate verification.

### Step 5: POST-CHECK — Verification
- Verify the change matches the original intent.
- Run relevant tests or manual checks.
- Confirm no regressions in adjacent functionality.
- If verification fails, enter self-correction loop (not retry loop).
"""

_COGER_ROUTING: Dict[str, str] = {
    "L1": """\
## Reasoning Level L1 — Direct Execution
Straightforward task. Apply minimal reasoning:
1. Identify the exact change needed.
2. Make the change.
3. Verify it works.
No deep analysis required. Speed is appropriate here.
""",
    "L2": """\
## Reasoning Level L2 — Guided Analysis
Moderate complexity. Apply structured reasoning:
1. READ: Understand the current state of all relevant files.
2. PLAN: Identify dependencies and side effects.
3. EXECUTE: Make changes with clear scope boundaries.
4. VERIFY: Test the change against expected outcomes.
One diagnostic pass before action is sufficient.
""",
    "L3": """\
## Reasoning Level L3 — Deep Reasoning
High complexity. Apply full Fable-style discipline:
1. DIAGNOSE: Full environment audit. No assumptions.
2. OPTIONS: Multiple solution paths with trade-off analysis.
3. BOUNDARIES: Explicit scope and collateral analysis.
4. MINIMAL TOOLING: Precise, verifiable tool chain.
5. POST-CHECK: Multi-layer verification.
Self-correction loop is mandatory if first attempt fails.
""",
    "L4": """\
## Reasoning Level L4 — Systematic Investigation
Critical complexity. Apply maximum rigor:
1. Full context verification (all related systems).
2. Hypothesis generation with formal risk scoring.
3. Boundary analysis including temporal dependencies.
4. Tool chain with intermediate checkpoints.
5. Comprehensive verification suite.
6. Delegation may be appropriate for subtasks.
If confidence < 80%, halt and request clarification.
""",
}

_SELF_CORRECTION_LOOP = """\
## Self-Correction Protocol

When an action fails or produces unexpected results:

1. **HALT** — Stop the current execution path. Do not retry blindly.
2. **ISOLATE** — Identify the exact point of failure.
   - Which variable, file, or assumption broke?
   - Create a minimal reproduction case.
3. **REPRODUCE** — Write a script or test that triggers the failure.
4. **VERIFY ROOT CAUSE** — Confirm the failure cause with evidence.
   - Use event hooks, logging, or type assertions.
5. **TARGETED FIX** — Apply the smallest possible correction.
6. **CONFIRM** — Re-run the reproduction case. Expect it to pass.
7. **EXPAND** — Now verify no collateral regressions.
"""

_TOOL_SELECTION_GUIDE = """\
## Tool Selection Discipline

Available tools: {tool_list}

### Selection Rules
1. **Read first** — Never guess file contents. Always read before editing.
2. **Grep for discovery** — Use grep to locate code before navigating.
3. **Edit precisely** — Use targeted replacements, not full file rewrites.
4. **Verify after each tool** — Check tool output before proceeding.
5. **Minimal footprint** — Prefer the tool that touches the least.

### Forbidden Patterns
- Batch-editing multiple files without reading each one first.
- Running destructive commands without a dry-run check.
- Using Write tool when Edit would suffice.
- Skipping verification after Bash execution.

### Read → Plan → Edit → Verify Cycle
For every code change, follow this cycle:
1. READ the target file(s) and understand the context.
2. PLAN the exact change (diff-level specificity).
3. EDIT with precise, targeted replacements.
4. VERIFY the edit produced the expected result.
"""

_DELEGATION_GUIDE = """\
## Delegation Protocol

When a task exceeds single-agent scope or requires parallel work:

1. **Decompose** — Break into independent, well-scoped subtasks.
2. **Isolate** — Each subtask must be self-contained with clear inputs/outputs.
3. **Specify** — Define exact acceptance criteria for each subtask.
4. **Route** — Assign to appropriate worker/subagent.
5. **Monitor** — Track progress against acceptance criteria.
6. **Integrate** — Merge results, verify no conflicts.
"""


# ── Template Engine ──────────────────────────────────────────────────────

class ReasoningTemplateEngine:
    """
    Generates reasoning templates for NEXUS agents.

    Supports Fable 5-step reasoning, CogER-based L1-L4 routing, and
    hybrid modes that combine Fable reasoning patterns with NEXUS routing.
    """

    def __init__(self, style: ReasoningStyle = ReasoningStyle.FABLE) -> None:
        """Initialize with reasoning style.

        Args:
            style: The default reasoning style for template generation.
        """
        self.style = style

    def generate_system_prompt(self, task_type: str, complexity: str) -> str:
        """Generate a system prompt with reasoning template.

        Combines the base reasoning protocol with task-specific guidance
        based on the selected style and complexity level.

        Args:
            task_type: Category of task (e.g., 'debug', 'feature', 'refactor',
                'security', 'analysis').
            complexity: CogER complexity level ('L1', 'L2', 'L3', 'L4').

        Returns:
            Complete system prompt string.
        """
        sections: List[str] = []

        # Core identity
        sections.append(
            "You are a NEXUS agent executing a software engineering task.\n"
            "You must reason through problems systematically before acting."
        )

        # Reasoning protocol based on style
        if self.style == ReasoningStyle.FABLE:
            sections.append(self.get_fable_5_step())
        elif self.style == ReasoningStyle.NEXUS:
            sections.append(self.get_coger_routing(complexity))
        elif self.style == ReasoningStyle.HYBRID:
            sections.append(self.get_coger_routing(complexity))
            sections.append(self._get_hybrid_guidelines())

        # Task-specific guidance
        task_guidance = self._get_task_guidance(task_type)
        if task_guidance:
            sections.append(task_guidance)

        # Self-correction (always included for L2+)
        if complexity in ("L2", "L3", "L4"):
            sections.append(_SELF_CORRECTION_LOOP)

        # Delegation (multi-agent levels: L3 peer-review, L4 delegation)
        if complexity in ("L3", "L4"):
            sections.append(_DELEGATION_GUIDE)

        return "\n\n---\n\n".join(sections)

    def generate_thinking_block(self, query: str) -> str:
        """Generate a <thinking_process> block for a query.

        Creates a structured thinking scaffold that guides the agent
        through Fable-style reasoning for a specific query.

        Args:
            query: The user query or task description.

        Returns:
            XML-style thinking block string.
        """
        lines = [
            "<thinking_process>",
            "",
            f"## Query Analysis",
            f"The task is: {query}",
            "",
            "## Context Verification",
            "- What environment state do I need to confirm?",
            "- What files/configs exist (vs what I assume)?",
            "- What dependencies are in play?",
            "",
            "## Hypothesis Generation",
            "- Option A: [primary approach]",
            "- Option B: [alternative approach]",
            "- Risk assessment for each:",
            "  - Effort: [low/medium/high]",
            "  - Reversibility: [easy/hard]",
            "  - Blast radius: [files affected]",
            "",
            "## Boundary Analysis",
            "- What MUST NOT change: [list]",
            "- What might be affected unintentionally: [list]",
            "- Scope boundary: [explicit limit]",
            "",
            "## Execution Plan",
            "1. [First concrete action]",
            "2. [Verification checkpoint]",
            "3. [Second action]",
            "4. [Final verification]",
            "",
            "## Success Criteria",
            "- [ ] [Criterion 1]",
            "- [ ] [Criterion 2]",
            "- [ ] No regressions in adjacent functionality",
            "",
            "</thinking_process>",
        ]
        return "\n".join(lines)

    def generate_verification_checklist(self, action: str) -> str:
        """Generate a post-verification checklist for an action.

        Creates a structured checklist that ensures thorough verification
        after completing an action.

        Args:
            action: Description of the action that was taken.

        Returns:
            Formatted verification checklist string.
        """
        return (
            f"## Verification Checklist for: {action}\n\n"
            "- [ ] Action produced expected output\n"
            "- [ ] No error messages or warnings\n"
            "- [ ] Changed files parse/compile correctly\n"
            "- [ ] Related tests still pass\n"
            "- [ ] No unintended side effects observed\n"
            "- [ ] Scope boundary was respected\n"
            "- [ ] Rollback path is clear if needed\n"
            "- [ ] Logging/audit trail is clean\n"
        )

    def inject_into_prompt(self, base_prompt: str, query: str) -> str:
        """Inject reasoning template into an existing agent prompt.

        Inserts the reasoning protocol between the base prompt and the
        user query, ensuring the agent follows structured reasoning.

        Args:
            base_prompt: The existing system prompt.
            query: The user query to append.

        Returns:
            Modified prompt with reasoning injection.
        """
        injection_parts: List[str] = []

        if self.style == ReasoningStyle.FABLE:
            injection_parts.append(self.get_fable_5_step())
        elif self.style == ReasoningStyle.NEXUS:
            injection_parts.append(self.get_coger_routing("L2"))
        elif self.style == ReasoningStyle.HYBRID:
            injection_parts.append(self.get_fable_5_step())
            injection_parts.append(self._get_hybrid_guidelines())

        injection_parts.append(_SELF_CORRECTION_LOOP)
        injection_parts.append(
            self.generate_verification_checklist("current action")
        )

        injection = "\n\n---\n\n".join(injection_parts)

        return (
            f"{base_prompt}\n\n"
            f"---\n\n{injection}\n\n"
            f"---\n\n## User Query\n{query}"
        )

    def get_fable_5_step(self) -> str:
        """Return the canonical Fable 5-step reasoning template.

        Returns:
            The 5-step reasoning protocol string.
        """
        return _FABLE_5_STEP

    def get_coger_routing(self, complexity: str) -> str:
        """Return CogER-appropriate reasoning for a complexity level.

        Args:
            complexity: One of 'L1', 'L2', 'L3', 'L4'.

        Returns:
            Reasoning template appropriate for the complexity level.
        """
        return _COGER_ROUTING.get(complexity, _COGER_ROUTING["L2"])

    def generate_tool_selection_guide(self, tool_names: List[str]) -> str:
        """Generate tool selection guide based on available tools.

        Adapts the generic tool selection guide to only reference tools
        that are actually available to the agent.

        Args:
            tool_names: List of tool names available to the agent.

        Returns:
            Customized tool selection guide string.
        """
        tool_list = ", ".join(sorted(tool_names))
        return _TOOL_SELECTION_GUIDE.format(tool_list=tool_list)

    def _get_hybrid_guidelines(self) -> str:
        """Return hybrid mode guidelines combining Fable + NEXUS routing.

        Returns:
            Hybrid reasoning guidelines string.
        """
        return (
            "## Hybrid Reasoning Guidelines\n\n"
            "This task uses hybrid mode: Fable reasoning discipline + "
            "CogER complexity routing.\n\n"
            "1. Start with Fable 5-step reasoning for all actions.\n"
            "2. Route depth of reasoning based on CogER level:\n"
            "   - L1/L2: Steps 1+4+5 only (diagnose, minimal tool, post-check).\n"
            "   - L3/L4: Full 5-step protocol required.\n"
            "3. Self-correction always uses the full loop regardless of level.\n"
            "4. Escalate reasoning depth if confidence drops below 70%.\n"
        )

    @staticmethod
    def _get_task_guidance(task_type: str) -> str:
        """Get task-type-specific guidance.

        Args:
            task_type: Category of task.

        Returns:
            Guidance string or empty string if no specific guidance.
        """
        guidance_map = {
            "debug": (
                "## Debugging Guidance\n"
                "- Start by reproducing the bug with minimal steps.\n"
                "- Isolate the failure to a specific function, line, or input.\n"
                "- Verify your fix against the original reproduction case.\n"
                "- Check for similar patterns in adjacent code.\n"
            ),
            "feature": (
                "## Feature Development Guidance\n"
                "- Understand the full requirement before coding.\n"
                "- Design the API/interface before implementation.\n"
                "- Write tests alongside (or before) the implementation.\n"
                "- Verify integration with existing systems.\n"
            ),
            "refactor": (
                "## Refactoring Guidance\n"
                "- Ensure existing tests pass before starting.\n"
                "- Make one structural change at a time.\n"
                "- Run tests after each change.\n"
                "- Verify behavior is preserved, not just structure.\n"
            ),
            "security": (
                "## Security Guidance\n"
                "- Assume all inputs are untrusted.\n"
                "- Check for injection, traversal, and privilege escalation.\n"
                "- Verify no secrets are logged or exposed.\n"
                "- Apply principle of least privilege.\n"
            ),
            "analysis": (
                "## Analysis Guidance\n"
                "- Read before interpreting. No assumptions about file contents.\n"
                "- Cross-reference multiple sources.\n"
                "- State confidence level for conclusions.\n"
                "- Identify gaps in available information.\n"
            ),
        }
        return guidance_map.get(task_type, "")
