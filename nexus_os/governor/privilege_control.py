"""governor/privilege_control.py — Progent Monotonic Privilege Control for Agents

Enforces least-privilege security policies over tool calls (names and arguments).
Supports allowed tools and forbidden tools.
Supports regex patterns and numerical interval constraints.
Implements monotonic confinement: updates can only shrink allowed spaces automatically.
Privilege expansions require explicit human/user approval.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)


# ── Interval Utilities ─────────────────────────────────────────────────────────

def parse_interval(c_str: str) -> Optional[Tuple[float, float, bool, bool]]:
    """Parse numerical interval constraints.

    Supports:
    - "< 100", "<= 100", "> 10", ">= 10"
    - "[10, 100]", "(10, 100)"
    - Single numbers like "20"

    Returns (lower, upper, lower_inclusive, upper_inclusive) or None.
    """
    c_str = c_str.strip()

    # Check for single number
    try:
        val = float(c_str)
        return (val, val, True, True)
    except ValueError:
        pass

    # Check for inequalities
    match = re.match(r"^([<>]=?)\s*(-?\d+(?:\.\d+)?)$", c_str)
    if match:
        op, val_str = match.groups()
        val = float(val_str)
        if op == "<":
            return (float("-inf"), val, False, False)
        elif op == "<=":
            return (float("-inf"), val, False, True)
        elif op == ">":
            return (val, float("inf"), False, False)
        elif op == ">=":
            return (val, float("inf"), True, False)

    # Check for range [10, 100] or (10, 100)
    match = re.match(r"^([\[\(])\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*([\]\)])$", c_str)
    if match:
        left_bracket, lower_str, upper_str, right_bracket = match.groups()
        lower = float(lower_str)
        upper = float(upper_str)
        lower_inc = left_bracket == "["
        upper_inc = right_bracket == "]"
        return (lower, upper, lower_inc, upper_inc)

    return None


def is_value_in_interval(val: float, interval: Tuple[float, float, bool, bool]) -> bool:
    """Verify if a numeric value falls within the specified interval."""
    lower, upper, lower_inc, upper_inc = interval
    # Check lower bound
    if lower_inc:
        if val < lower:
            return False
    else:
        if val <= lower:
            return False
    # Check upper bound
    if upper_inc:
        if val > upper:
            return False
    else:
        if val >= upper:
            return False
    return True


def is_interval_subset(next_int: Tuple[float, float, bool, bool], curr_int: Tuple[float, float, bool, bool]) -> bool:
    """Returns True if next_int is a strict subset of curr_int."""
    l_next, u_next, li_next, ui_next = next_int
    l_curr, u_curr, li_curr, ui_curr = curr_int

    # Check lower bound containment
    if l_next < l_curr:
        return False
    if l_next == l_curr:
        if not li_curr and li_next:
            return False

    # Check upper bound containment
    if u_next > u_curr:
        return False
    if u_next == u_curr:
        if not ui_curr and ui_next:
            return False

    return True


def _canonicalize_path_like(s: str) -> str:
    """Collapse traversal segments in path-like strings before allow-matching.

    Audit (privilege_control.py:121): without canonicalization an allowed
    prefix pattern permitted "<allowed-dir>/../../../etc" escapes. Only
    strings that look like paths AND contain dot segments are normalized,
    so URLs and plain strings pass through untouched.
    """
    if ("/" in s or "\\" in s) and (".." in s or "/./" in s or "\\.\\" in s):
        return os.path.normpath(s).replace("\\", "/")
    return s


def _iter_candidate_strings(val: Any) -> Iterator[str]:
    """Yield every string a forbid rule should be tested against.

    Audit (privilege_control.py:174): deny rules ran re.match on str(val),
    so command=["rm", "-rf", "/"] never matched ^rm. Recurse into
    structured arguments and also yield the space-joined argv form.
    """
    if isinstance(val, str):
        yield val
    elif isinstance(val, dict):
        for k, v in val.items():
            yield from _iter_candidate_strings(k)
            yield from _iter_candidate_strings(v)
    elif isinstance(val, (list, tuple, set, frozenset)):
        for item in val:
            yield from _iter_candidate_strings(item)
        yield " ".join(str(i) for i in val)
    else:
        yield str(val)


def check_constraint(constraint_str: str, val: Any, mode: str = "allow") -> bool:
    """Validate a value against a constraint string (either interval or regex).

    mode="allow": the value must lie entirely inside the pattern
    (re.fullmatch — audit: re.match prefix semantics let unanchored
    patterns pass arbitrary suffixes) after path canonicalization.
    mode="forbid": the pattern is hunted anywhere in the value, on any
    line (re.search + MULTILINE — deny must over-match, never under-match).
    An invalid regex fails closed: allow-side no match, forbid-side match.
    """
    interval = parse_interval(constraint_str)
    if interval is not None:
        try:
            numeric_val = float(val)
            return is_value_in_interval(numeric_val, interval)
        except (ValueError, TypeError):
            return False
    # Fallback to regex
    try:
        if mode == "forbid":
            return bool(re.search(constraint_str, str(val), re.MULTILINE))
        return bool(re.fullmatch(constraint_str, _canonicalize_path_like(str(val))))
    except re.error as e:
        logger.error("Progent: Invalid regex pattern '%s': %s", constraint_str, e)
        return mode == "forbid"


def is_constraint_subset(next_c: str, curr_c: str) -> bool:
    """Verify if next_c represents a subset of curr_c."""
    int_next = parse_interval(next_c)
    int_curr = parse_interval(curr_c)
    if int_next is not None and int_curr is not None:
        return is_interval_subset(int_next, int_curr)
    # Simple literal comparison for regexes
    return next_c == curr_c


# ── Policy & Control ───────────────────────────────────────────────────────────

@dataclass
class PrivilegePolicy:
    """Represents the allowed and forbidden action space of an agent session."""
    # Maps tool_name -> dict of arg_name -> list of allowed patterns (regex or interval)
    allowed_tools: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    # Maps tool_name -> dict of arg_name -> list of forbidden patterns (regex or interval)
    forbidden_tools: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)


class ProgentPrivilegeControl:
    """Checks tool execution against symbolic privilege rules with monotonic confinement."""

    def __init__(self, policy: Optional[PrivilegePolicy] = None) -> None:
        self.policy = policy or PrivilegePolicy()

    def check_call(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Verify if a tool call is permitted by the current policy.

        Returns True if allowed, False if blocked.
        """
        # 1. Deny-override: Check forbid rules first
        if tool_name in self.policy.forbidden_tools:
            forbid_constraints = self.policy.forbidden_tools[tool_name]
            # If no constraints exist, the entire tool is forbidden globally
            if not forbid_constraints:
                logger.warning("Progent: Tool %s is explicitly forbidden globally", tool_name)
                return False
            
            # Check if arguments match any forbid constraints
            for arg_name, patterns in forbid_constraints.items():
                if not patterns:
                    continue
                val = arguments.get(arg_name)
                if val is not None:
                    # If it matches even one of the forbid patterns, the call is blocked.
                    # Every candidate string is tested (structured args recursed).
                    for pattern in patterns:
                        if any(
                            check_constraint(pattern, cand, mode="forbid")
                            for cand in _iter_candidate_strings(val)
                        ):
                            logger.warning(
                                "Progent: Tool call %s blocked by forbid rule for arg %s matching '%s'",
                                tool_name, arg_name, pattern
                            )
                            return False

        # 2. Check allow rules
        if not self.policy.allowed_tools:
            logger.warning("Progent: Empty policy. Tool execution blocked by default: %s", tool_name)
            return False

        if tool_name not in self.policy.allowed_tools:
            logger.warning("Progent: Tool %s is not in the allowed tools list", tool_name)
            return False

        arg_constraints = self.policy.allowed_tools[tool_name]
        
        # If there are no specific argument constraints, the tool is allowed globally
        if not arg_constraints:
            return True

        # Check each argument constraint
        for arg_name, patterns in arg_constraints.items():
            if not patterns:
                continue

            val = arguments.get(arg_name)
            if val is None:
                logger.warning("Progent: Missing required constrained argument %s for tool %s", arg_name, tool_name)
                return False

            # Must match at least one of the configured regex/interval patterns
            matched = False
            for pattern in patterns:
                if check_constraint(pattern, val):
                    matched = True
                    break
            
            if not matched:
                logger.warning(
                    "Progent: Argument '%s' value '%s' failed policy validation for tool %s",
                    arg_name, str(val), tool_name
                )
                return False

        return True

    def narrow_policy(self, next_policy: PrivilegePolicy) -> bool:
        """Attempt to update the policy.

        Returns True if the update is a strict narrowing (applied automatically).
        Returns False if the update expands privileges (requires explicit user approval).
        """
        # 1. Evaluate allowed_tools updates
        for tool_name, next_constraints in next_policy.allowed_tools.items():
            # If a new tool is introduced, it is an expansion
            if tool_name not in self.policy.allowed_tools:
                logger.info("Progent: Update rejected (introduces new allowed tool: %s)", tool_name)
                return False
            
            current_constraints = self.policy.allowed_tools[tool_name]
            
            # Check for removed argument constraints or expanded allowed patterns
            for arg_name, current_patterns in current_constraints.items():
                if current_patterns:
                    next_patterns = next_constraints.get(arg_name, [])
                    if not next_patterns:
                        logger.info("Progent: Update rejected (removes allowed argument constraint for: %s)", arg_name)
                        return False
                    
                    # Verify each next pattern is a subset of at least one current pattern
                    for n_pat in next_patterns:
                        is_subset = False
                        for c_pat in current_patterns:
                            if is_constraint_subset(n_pat, c_pat):
                                is_subset = True
                                break
                        if not is_subset:
                            logger.info("Progent: Update rejected (contains new unapproved patterns for: %s)", arg_name)
                            return False

            # Verify that any arguments that are newly constrained in next_policy
            # were either unconstrained in current_policy or are subsets.
            for arg_name, next_patterns in next_constraints.items():
                current_patterns = current_constraints.get(arg_name, [])
                if current_patterns and next_patterns:
                    for n_pat in next_patterns:
                        is_subset = False
                        for c_pat in current_patterns:
                            if is_constraint_subset(n_pat, c_pat):
                                is_subset = True
                                break
                        if not is_subset:
                            logger.info("Progent: Update rejected (contains new unapproved patterns for: %s)", arg_name)
                            return False

        # 2. Evaluate forbidden_tools updates (dual of allow checks)
        # Adding a new forbid tool or adding new constraints to forbid tools restricts action space further (narrowing).
        # Removing a forbid tool or relaxing forbid constraints expands privileges.
        for tool_name, current_constraints in self.policy.forbidden_tools.items():
            # If a forbid tool is removed entirely, it is an expansion
            if tool_name not in next_policy.forbidden_tools:
                logger.info("Progent: Update rejected (removes forbidden tool constraint for: %s)", tool_name)
                return False

            next_constraints = next_policy.forbidden_tools[tool_name]
            
            # If current forbid tool was forbidden globally (empty dict) but next is now restricted (arg constraints),
            # that represents an expansion (allows calling the tool for other arguments).
            if not current_constraints and next_constraints:
                logger.info("Progent: Update rejected (relaxes global forbid for tool: %s)", tool_name)
                return False

            for arg_name, current_patterns in current_constraints.items():
                if current_patterns:
                    next_patterns = next_constraints.get(arg_name, [])
                    # If forbid constraint on an argument is removed, it is an expansion
                    if not next_patterns:
                        logger.info("Progent: Update rejected (removes forbidden argument constraint for: %s)", arg_name)
                        return False
                    
                    # For forbid rules, current_patterns must be a subset of next_patterns
                    # (meaning we forbid more or equal set of values).
                    for c_pat in current_patterns:
                        is_subset = False
                        for n_pat in next_patterns:
                            if is_constraint_subset(c_pat, n_pat):
                                is_subset = True
                                break
                        if not is_subset:
                            logger.info("Progent: Update rejected (relaxes forbidden pattern constraint for: %s)", arg_name)
                            return False

        # If we passed all checks, the next policy is a valid narrowing
        self.policy = next_policy
        logger.info("Progent: Monotonic policy update successful (narrowed)")
        return True
