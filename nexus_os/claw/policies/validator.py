"""Policy schema validation for NEXUSCLAW network/filesystem policies.

Validates the structure of policy JSON files against the expected schema.
"""

from __future__ import annotations

from typing import Any

from nexus_os.claw.exceptions import PolicyError


class PolicyValidationError(PolicyError):
    """Raised when a policy document fails schema validation."""


_REQUIRED_NETWORK_FIELDS = {"name", "enforcement", "endpoints", "rules"}
_REQUIRED_ENDPOINT_FIELDS = {"host", "port", "protocol"}
_REQUIRED_RULE_FIELDS = {"method", "path", "description"}
_VALID_ENFORCEMENTS = {"allow", "deny"}
_VALID_PROTOCOLS = {"https", "tcp", "udp", "grpc"}
_VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "CONNECT", "OPTIONS", "TRACE"}
_VALID_TRUST_LEVELS = {"HARDWALL", "CAUTION", "RESTRICTED"}


def validate_policy(doc: dict[str, Any]) -> dict[str, Any]:
    """Validate a policy document.

    Returns the validated doc (possibly with defaults filled) or raises
    ``PolicyValidationError``.
    """
    errors: list[str] = []

    if not isinstance(doc, dict):
        raise PolicyValidationError("Policy must be a JSON object")

    version = doc.get("version")
    if version is None:
        errors.append("Missing 'version' field")
    elif not isinstance(version, int) or version < 1:
        errors.append(f"Invalid version: {version}")

    trust = doc.get("trust_level", "CAUTION")
    if trust not in _VALID_TRUST_LEVELS:
        errors.append(f"Invalid trust_level '{trust}'; must be one of {_VALID_TRUST_LEVELS}")

    fs = doc.get("filesystem_policy")
    if fs is not None:
        if not isinstance(fs, dict):
            errors.append("filesystem_policy must be an object")
        else:
            for key in ("read_allowed", "write_allowed", "exec_allowed"):
                if key in fs and not isinstance(fs[key], list):
                    errors.append(f"filesystem_policy.{key} must be a list of paths")

    net = doc.get("network_policies", [])
    if not isinstance(net, list):
        errors.append("network_policies must be a list")
    else:
        for i, np in enumerate(net):
            if not isinstance(np, dict):
                errors.append(f"network_policies[{i}] must be an object")
                continue
            missing = _REQUIRED_NETWORK_FIELDS - set(np)
            if missing:
                errors.append(f"network_policies[{i}] missing fields: {missing}")
                continue
            if np.get("enforcement") not in _VALID_ENFORCEMENTS:
                errors.append(f"network_policies[{i}] invalid enforcement: {np.get('enforcement')}")

            endpoints = np.get("endpoints", [])
            for j, ep in enumerate(endpoints):
                if not isinstance(ep, dict):
                    errors.append(f"network_policies[{i}].endpoints[{j}] must be an object")
                    continue
                ep_missing = _REQUIRED_ENDPOINT_FIELDS - set(ep)
                if ep_missing:
                    errors.append(f"network_policies[{i}].endpoints[{j}] missing: {ep_missing}")
                if ep.get("protocol") not in _VALID_PROTOCOLS:
                    errors.append(f"network_policies[{i}].endpoints[{j}] invalid protocol")

            rules = np.get("rules", [])
            for k, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    errors.append(f"network_policies[{i}].rules[{k}] must be an object")
                    continue
                rule_missing = _REQUIRED_RULE_FIELDS - set(rule)
                if rule_missing:
                    errors.append(f"network_policies[{i}].rules[{k}] missing: {rule_missing}")
                if rule.get("method") not in _VALID_METHODS and rule.get("method") != "*":
                    errors.append(f"network_policies[{i}].rules[{k}] invalid method: {rule.get('method')}")

    if errors:
        raise PolicyValidationError("; ".join(errors))

    return doc
