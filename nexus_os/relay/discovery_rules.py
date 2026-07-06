"""Pure classification rules for new-model discovery (FI-D1).

Shared by provider_refresher (registry-backed discovery) and
tools/frontier_scanner (external catalog polling). No I/O, no state —
every function is a pure computation over the registry dict and model
id strings, so both consumers apply identical noise/priority rules.

Rules encoded here:
- unknown-vendor-prefix: a listed model id whose org prefix (the part
  before "/") matches no registered model is flagged HIGH priority —
  the "Owl Alpha" rule (Meituan's LongCat-2.0 ran 9 weeks on OpenRouter
  under an unrecognized alias before anyone noticed).
- alias suppression: an id that is really an alias of a registered
  model is never a candidate, and a "removed" id that survives as an
  alias is not dead.
- metadata-diff suppression: candidate identity is the model id alone;
  price/context/metadata changes on a known id never re-emit.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Set, Tuple

PRIORITY_HIGH = "high"
PRIORITY_NORMAL = "normal"

REASON_UNKNOWN_PREFIX = "unknown-vendor-prefix"
REASON_NEW_MODEL = "new-model"


def _org_prefix(model_id: str) -> str:
    """Org portion of a namespaced model id, lowercased ('' if bare)."""
    if "/" in model_id:
        return model_id.split("/", 1)[0].strip().lower()
    return ""


def _family_stem(model_id: str) -> str:
    """Family stem of a bare model id: leading alpha run, lowercased.

    'glm-5.2' -> 'glm', 'qwen3-coder-next' -> 'qwen', 'kimi-k2.7' -> 'kimi'.
    """
    bare = model_id.split("/")[-1].strip().lower()
    stem = []
    for ch in bare:
        if ch.isalpha():
            stem.append(ch)
        else:
            break
    return "".join(stem)


def registered_ids(registry: Dict[str, Any], provider: str | None = None) -> Set[str]:
    """All registry model ids + aliases (any status), optionally per provider."""
    known: Set[str] = set()
    for m in registry.get("models", []):
        if provider is not None and m.get("provider") != provider:
            continue
        mid = m.get("id")
        if mid:
            known.add(mid)
        for alias in m.get("aliases") or []:
            known.add(alias)
    return known


def known_vendor_prefixes(registry: Dict[str, Any]) -> Set[str]:
    """Org prefixes + family stems of every registered id and alias."""
    prefixes: Set[str] = set()
    for mid in registered_ids(registry):
        org = _org_prefix(mid)
        if org:
            prefixes.add(org)
        stem = _family_stem(mid)
        if len(stem) >= 3:  # 1-2 letter stems ('m3') are noise, not vendors
            prefixes.add(stem)
    prefixes.discard("")
    return prefixes


def classify_candidate(model_id: str, known_prefixes: Set[str]) -> Tuple[str, str]:
    """(priority, reason) for a listed-but-unregistered model id."""
    org = _org_prefix(model_id)
    stem = _family_stem(model_id)
    if org and org in known_prefixes:
        return PRIORITY_NORMAL, REASON_NEW_MODEL
    if stem and stem in known_prefixes:
        return PRIORITY_NORMAL, REASON_NEW_MODEL
    return PRIORITY_HIGH, REASON_UNKNOWN_PREFIX


def new_candidates(
    listed: Iterable[str], registry: Dict[str, Any], provider: str
) -> Dict[str, Tuple[str, str]]:
    """Listed ids that are neither registered nor aliases, classified.

    Returns {model_id: (priority, reason)}. Comparison is provider-scoped
    for identity but prefix knowledge is registry-wide (a Qwen model
    appearing on a new provider is 'new-model', not 'unknown vendor').
    """
    known = registered_ids(registry, provider=provider)
    prefixes = known_vendor_prefixes(registry)
    out: Dict[str, Tuple[str, str]] = {}
    for mid in listed:
        if not mid or mid in known:
            continue
        out[mid] = classify_candidate(mid, prefixes)
    return out


def resolve_removal(model_id: str, registry: Dict[str, Any], listed: Set[str]) -> bool:
    """True if a registered id missing from the listing is alias-covered.

    A provider that renames a model keeps serving it under the alias —
    that is a rename, not a removal, and must not trip suspension.
    """
    for m in registry.get("models", []):
        if m.get("id") != model_id:
            continue
        for alias in m.get("aliases") or []:
            if alias in listed:
                return True
    return False
