"""Governed A2A/ACP intake adapter.

Inbound A2A callers may propose work, but they cannot self-approve execution.
The adapter maps protocol messages into the canonical NexusClaw envelope,
TrustKernel, and KAIJU decision surfaces. Live execution remains an operator
action through the governed coordinator path.
"""

from __future__ import annotations

from collections import deque
import hashlib
import json
from threading import Lock
from typing import Any

from nexus_os.bridge.secrets import SecretNotFoundError, SecretStore, verify_signature
from nexus_os.governor.kaiju_auth import (
    AuthRequest,
    ClearanceLevel,
    ImpactLevel,
    KaijuAuthorizer,
    ScopeLevel,
)
from nexus_os.governor.trust_kernel import TrustKernel, get_trust_kernel
from nexus_os.nexusclaw.coordinator import NexusClawCoordinator
from nexus_os.nexusclaw.envelope import NexusClawTaskEnvelope


A2A_SKILL_RISK: dict[str, str] = {
    "audit_log": "medium",
    "evidence_capture": "medium",
    "coordination_queue": "medium",
    "a2a_channel": "medium",
    "phase2_probe": "medium",
    "program_execution": "high",
    "swarm_dispatch": "medium",
    "browser_http_diagnostic": "medium",
}
A2A_SKILLS = frozenset(A2A_SKILL_RISK)

# This is deliberately an in-process test gate, not a network listener.  It
# exists so deployment work can exercise signed A2A intake without advertising
# or enabling an external A2A transport.
A2A_SIGNED_INBOUND_SMOKE_SCHEMA = "nexus.a2a-signed-inbound-smoke.v1"
MAX_A2A_SMOKE_PAYLOAD_BYTES = 16 * 1024
MAX_A2A_SMOKE_NONCE_LENGTH = 128


class A2AReplayGuard:
    """Bounded, process-local replay protection for signed A2A smoke intake.

    The guard intentionally has no persistence layer: a process restart resets
    it.  Callers receive that limitation in every response so this smoke gate
    is never mistaken for a durable production replay store.
    """

    def __init__(self, *, max_entries: int = 1024) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._max_entries = max_entries
        self._seen: set[str] = set()
        self._order: deque[str] = deque()
        self._lock = Lock()

    def consume(self, *, sender: str, nonce: str) -> bool:
        """Record a sender/nonce once and return false on any replay."""

        fingerprint = hashlib.sha256(f"{sender}\0{nonce}".encode("utf-8")).hexdigest()
        with self._lock:
            if fingerprint in self._seen:
                return False
            self._seen.add(fingerprint)
            self._order.append(fingerprint)
            if len(self._order) > self._max_entries:
                self._seen.remove(self._order.popleft())
            return True


_DEFAULT_A2A_REPLAY_GUARD = A2AReplayGuard()


def _safe_sender(value: Any) -> str:
    text = "".join(
        char for char in str(value or "anonymous") if char.isalnum() or char in "._:-"
    )
    return (text or "anonymous")[:64]


def _bounded_tokens(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 2048
    return max(128, min(parsed, 4096))


def _strict_identifier(value: Any, *, minimum_length: int = 1, maximum_length: int = 128) -> str | None:
    """Accept only a bounded, canonical identifier without rewriting it."""

    raw = str(value or "")
    if not minimum_length <= len(raw) <= maximum_length:
        return None
    return raw if raw == _safe_sender(raw) and raw != "anonymous" else None


def canonicalize_signed_a2a_smoke_payload(payload: dict[str, Any]) -> str:
    """Create the exact bounded JSON string protected by the Bridge HMAC."""

    if not isinstance(payload, dict):
        raise ValueError("signed A2A smoke payload must be a JSON object")
    try:
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("signed A2A smoke payload must be JSON-serializable") from exc
    if len(canonical.encode("utf-8")) > MAX_A2A_SMOKE_PAYLOAD_BYTES:
        raise ValueError("signed A2A smoke payload exceeds the 16KiB limit")
    return canonical


def _signed_smoke_result(
    *,
    enabled: bool,
    sender: str = "anonymous",
    identity_verified: bool = False,
    intake_status: str,
    reason: str,
    replay_detected: bool = False,
) -> dict[str, Any]:
    """Return a redacted, permanently proposal-only signed-intake receipt."""

    return {
        "schema": A2A_SIGNED_INBOUND_SMOKE_SCHEMA,
        "enabled": bool(enabled),
        "intake_status": intake_status,
        "accepted": False,
        "execution_allowed": False,
        "proposal_only": True,
        "reason": reason,
        "identity": {
            "sender": sender,
            "verified": identity_verified,
            "mechanism": "bridge_hmac_sha256" if identity_verified else "unverified",
            "authority": "external_proposal_only",
        },
        "replay": {
            "detected": replay_detected,
            "scope": "process_memory_only",
            "durable": False,
        },
        "transport": {
            "network_listener_enabled": False,
            "outbound_messages_sent": False,
        },
    }


def inspect_signed_a2a_inbound_smoke(
    *,
    payload: dict[str, Any],
    signature: str,
    secret_store: SecretStore | None,
    enabled: bool = False,
    replay_guard: A2AReplayGuard | None = None,
    trust_kernel: TrustKernel | None = None,
    coordinator: NexusClawCoordinator | None = None,
) -> dict[str, Any]:
    """Validate one signed A2A proposal without enabling an A2A transport.

    The input is HMAC-bound using the existing Bridge convention
    ``(secret, task_id, canonical_payload)``.  A valid signature only proves
    the configured caller identity; it never grants privilege or live
    execution.  This function is disabled by default and does not emit or
    send a message to any external agent.
    """

    raw_sender = payload.get("sender") if isinstance(payload, dict) else None
    sender = _strict_identifier(raw_sender, maximum_length=64) or "anonymous"
    if not enabled:
        return _signed_smoke_result(
            enabled=False,
            sender=sender,
            intake_status="disabled",
            reason="signed_inbound_smoke_disabled_by_default",
        )

    if not isinstance(payload, dict):
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="invalid_payload",
        )

    task_id = _strict_identifier(payload.get("task_id"))
    nonce = _strict_identifier(
        payload.get("nonce"),
        minimum_length=16,
        maximum_length=MAX_A2A_SMOKE_NONCE_LENGTH,
    )
    skill_id = str(payload.get("skill_id") or "").strip().lower()
    params = payload.get("params", {})
    if sender == "anonymous" or task_id is None or nonce is None or not isinstance(params, dict):
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="invalid_signed_smoke_fields",
        )
    if skill_id not in A2A_SKILLS:
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="unknown_a2a_skill",
        )
    if secret_store is None:
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="secret_store_required",
        )

    try:
        canonical_payload = canonicalize_signed_a2a_smoke_payload(payload)
        secret = secret_store.get_secret(sender)
    except ValueError as exc:
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason=str(exc),
        )
    except SecretNotFoundError:
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="unknown_signed_a2a_sender",
        )

    if not signature or not verify_signature(secret, task_id, canonical_payload, signature):
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            intake_status="rejected",
            reason="invalid_signature",
        )

    guard = replay_guard or _DEFAULT_A2A_REPLAY_GUARD
    if not guard.consume(sender=sender, nonce=nonce):
        return _signed_smoke_result(
            enabled=True,
            sender=sender,
            identity_verified=True,
            intake_status="rejected",
            reason="replay_detected",
            replay_detected=True,
        )

    proposal = build_governed_a2a_proposal(
        task_id=task_id,
        skill_id=skill_id,
        params={**params, "sender": sender},
        trust_kernel=trust_kernel,
        coordinator=coordinator,
        identity_verified=True,
    )
    result = _signed_smoke_result(
        enabled=True,
        sender=sender,
        identity_verified=True,
        intake_status="proposal_created",
        reason="valid_signature_fresh_nonce_proposal_only",
    )
    result["accepted"] = True
    result["proposal"] = proposal
    return result


def build_governed_a2a_proposal(
    *,
    task_id: str,
    skill_id: str,
    params: dict[str, Any] | None = None,
    trust_kernel: TrustKernel | None = None,
    coordinator: NexusClawCoordinator | None = None,
    identity_verified: bool = False,
) -> dict[str, Any]:
    """Map one inbound A2A request to a proposal-only governed envelope.

    ``identity_verified`` records cryptographic sender verification only.  It
    never changes the proposal-only execution invariant or grants authority.
    """

    request = dict(params or {})
    normalized_skill = str(skill_id or "").strip().lower()
    if normalized_skill not in A2A_SKILLS:
        allowed = ", ".join(sorted(A2A_SKILLS))
        raise ValueError(f"unknown A2A skill '{normalized_skill}'; allowed: {allowed}")

    sender = _safe_sender(request.get("sender"))
    requested_live = str(request.get("mode") or "dry_run").strip().lower() == "live"
    claimed_approval = str(request.get("approval_state") or "pending").strip().lower()
    risk = A2A_SKILL_RISK[normalized_skill]

    kernel = trust_kernel or get_trust_kernel()
    trust = kernel.evaluate(
        agent_id=f"a2a:{sender}",
        action="execute",
        lane="integration",
        context={
            "side_effect": True,
            "requested_tokens": _bounded_tokens(request.get("max_tokens")),
            "protocol": "a2a-jsonrpc-2.0",
            "identity_verified": bool(identity_verified),
        },
    )
    kaiju = KaijuAuthorizer().authorize(
        AuthRequest(
            agent_id=f"a2a:{sender}",
            project_id="nexus-os",
            action="execute",
            scope=ScopeLevel.PROJECT,
            intent=f"execute governed A2A skill {normalized_skill}",
            impact=ImpactLevel(risk),
            clearance=ClearanceLevel.CONTRIBUTOR,
            trace_id=task_id,
        )
    )

    envelope = NexusClawTaskEnvelope.from_dict(
        {
            "task_id": task_id,
            "source": f"a2a:{sender}",
            "lane": "external",
            "intent": normalized_skill,
            "risk_level": risk,
            # Never trust an inbound caller's self-declared approval.
            "approval_state": "pending",
            "human_approved": False,
            "required_capabilities": [normalized_skill],
            "resource_budget": {
                "max_tokens": _bounded_tokens(request.get("max_tokens")),
                "max_runtime_s": 30,
            },
            "egress_policy": {
                "network_access": normalized_skill == "browser_http_diagnostic",
                "data_egress": False,
            },
            "evidence_refs": [f"a2a-task:{task_id}"],
        }
    )
    nexusclaw = (coordinator or NexusClawCoordinator()).dispatch(envelope, live=False)

    return {
        "schema": "nexus.a2a-governance.v1",
        "task_id": task_id,
        "skill_id": normalized_skill,
        "execution_allowed": False,
        "proposal_only": True,
        "client_requested_live": requested_live,
        "client_claimed_approval": claimed_approval,
        "client_approval_accepted": False,
        "identity": {
            "sender": sender,
            "verified": bool(identity_verified),
            "authority": "external_proposal_only",
        },
        "envelope": envelope.to_dict(),
        "trust": trust.to_dict(),
        "kaiju": {
            "decision": kaiju.decision.value,
            "reason": kaiju.reason,
            "trace_id": kaiju.trace_id,
        },
        "nexusclaw": nexusclaw.to_dict(),
        "control_plane": {
            "identity": "signed_external_proposal" if identity_verified else "unverified_external",
            "envelope": "NexusClawTaskEnvelope",
            "trust": "canonical_trust_kernel",
            "authorization": "kaiju_4_variable",
            "privilege": "operator_policy_required",
            "execution": "proposal_only",
            "evidence": "a2a_task_record",
        },
        "operator_next_step": (
            "Review the proposal, provision an explicit privilege policy, and "
            "re-dispatch through the NexusClaw governed live path."
        ),
    }
