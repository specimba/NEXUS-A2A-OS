"""Brain API routes for native Sentinel."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from nexus_os.db.manager import DBConfig, DatabaseManager
from nexus_os.governor.base import NexusGovernor
from nexus_os.sentinel.models import (
    ApprovalRequest,
    CreateCaseRequest,
    DeliverableContract,
    EvaluateCaseRequest,
    ExecuteRequest,
    VerifyRequest,
)
from nexus_os.sentinel.policy import evaluate_deliverable_contract
from nexus_os.sentinel.repository import (
    CaseNotFound,
    IdempotencyConflict,
    SentinelRepository,
    VersionConflict,
)
from nexus_os.sentinel.service import BridgeExecutionError, SentinelService
from nexus_os.sentinel.state_machine import InvalidTransition
from nexus_os.vault.memory_channels import get_manager

logger = logging.getLogger("nexus.sentinel")


def _db_security_defaults() -> tuple[str, bool, bool]:
    """Resolve (passphrase, encrypted, allow_unencrypted) for the ledger.

    Audit fix (adoption review): the authoritative hash-chained case
    ledger defaulted to plaintext SQLite with allow_unencrypted=1 —
    silently. New posture: the passphrase defaults to the vault master
    key (same autogen key file the P2-5 channel encryption uses), and
    encryption turns ON automatically whenever pysqlcipher3 is
    installed. Without the cipher module the ledger still falls back to
    plaintext (hash chain keeps tamper-EVIDENCE), but loudly.
    """
    passphrase = os.getenv("NEXUS_SENTINEL_DB_PASSPHRASE", "")
    if not passphrase:
        try:
            from nexus_os.security.vault_encrypt import load_master_key
            key = load_master_key(generate=True)
            passphrase = key.hex() if key else ""
        except Exception:
            passphrase = ""
    try:
        import pysqlcipher3  # noqa: F401
        cipher_available = True
    except ImportError:
        cipher_available = False
    encrypted_default = "1" if (cipher_available and passphrase) else "0"
    encrypted = os.getenv("NEXUS_SENTINEL_DB_ENCRYPTED", encrypted_default) == "1"
    allow_unencrypted = os.getenv(
        "NEXUS_SENTINEL_ALLOW_UNENCRYPTED", "0" if cipher_available else "1"
    ) == "1"
    if not encrypted:
        logger.warning(
            "Sentinel case ledger is UNENCRYPTED at rest (pysqlcipher3 %s). "
            "Hash chain still provides tamper-evidence; install pysqlcipher3 "
            "for confidentiality.",
            "available but encryption disabled via env" if cipher_available else "not installed",
        )
    return passphrase, encrypted, allow_unencrypted

router = APIRouter(prefix="/api/sentinel", tags=["sentinel"])
_service: SentinelService | None = None


def get_sentinel_service() -> SentinelService:
    global _service
    if _service is None:
        default_root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NEXUS" / "sentinel"
        db_path = Path(os.getenv("NEXUS_SENTINEL_DB", str(default_root / "sentinel.db")))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        passphrase, encrypted, allow_unencrypted = _db_security_defaults()
        manager = DatabaseManager(
            DBConfig(
                db_path=str(db_path),
                passphrase=passphrase,
                encrypted=encrypted,
                allow_unencrypted=allow_unencrypted,
            )
        )
        manager.setup_schema()
        _service = SentinelService(
            repository=SentinelRepository(manager),
            governor=NexusGovernor(manager),
            memory_manager=get_manager(),
        )
    return _service


def set_sentinel_service(service: SentinelService | None) -> None:
    global _service
    _service = service


def _raise_api_error(exc: Exception) -> None:
    if isinstance(exc, CaseNotFound):
        raise HTTPException(404, "Sentinel case not found") from exc
    if isinstance(exc, (VersionConflict, IdempotencyConflict)):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(403, str(exc)) from exc
    if isinstance(exc, BridgeExecutionError):
        raise HTTPException(503, str(exc)) from exc
    if isinstance(exc, (InvalidTransition, ValueError)):
        raise HTTPException(422, str(exc)) from exc
    raise exc


@router.get("/cases")
def list_cases(limit: int = Query(100, ge=1, le=500)):
    repository = get_sentinel_service().repository
    cases = []
    for case in repository.list_cases(limit):
        item = case.model_dump(mode="json")
        item.update(repository.case_metrics(case.case_id))
        item["evidence_complete"] = "EVIDENCE_INCOMPLETE" not in case.reason_codes
        item["model_echo_mismatch"] = "MODEL_ECHO_MISMATCH" in case.reason_codes
        cases.append(item)
    return {"cases": cases}


@router.post("/cases", status_code=201)
def create_case(request: CreateCaseRequest):
    try:
        return get_sentinel_service().create_case(request)
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    try:
        return get_sentinel_service().repository.get_case(case_id)
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/cases/{case_id}/evaluate")
def evaluate_case(case_id: str, request: EvaluateCaseRequest):
    try:
        return get_sentinel_service().evaluate(case_id, request)
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/cases/{case_id}/approval")
def approve_case(case_id: str, request: ApprovalRequest):
    try:
        return get_sentinel_service().approve(case_id, request)
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/cases/{case_id}/execute")
def execute_case(case_id: str, request: ExecuteRequest):
    try:
        return get_sentinel_service().execute(case_id, request)
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/cases/{case_id}/verify")
def verify_case(case_id: str, request: VerifyRequest):
    try:
        return get_sentinel_service().verify(case_id, request)
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/cases/{case_id}/timeline")
def case_timeline(case_id: str):
    try:
        return {
            "case_id": case_id,
            "events": [
                event.model_dump(mode="json")
                for event in get_sentinel_service().repository.timeline(case_id)
            ],
        }
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/cases/{case_id}/replay")
def replay_case(case_id: str):
    try:
        return get_sentinel_service().replay(case_id)
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/claims/validate")
def validate_claim_contract(contract: DeliverableContract):
    return evaluate_deliverable_contract(contract)
