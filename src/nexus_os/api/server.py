"""FastAPI surface for the canonical Nexus Governor."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nexus_os.api.service import GovernanceAPIState


class SkillProposalRequest(BaseModel):
    """Incoming GSPP proposal request."""

    proposal_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    skill: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(..., min_length=1)
    timestamp: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Manual approval/rejection request for held proposals."""

    decision: str = Field(..., pattern="^(approve|reject|hold)$")
    reviewer: str = Field(default="speci")
    reason: str = Field(default="")


def create_app(db_path: Optional[str] = None) -> FastAPI:
    """Create the FastAPI governance app."""

    state = GovernanceAPIState(
        db_path=db_path or os.getenv("NEXUS_API_DB_PATH", "nexus_api.db")
    )

    api = FastAPI(title="Nexus OS Governance API", version="3.0.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "operational",
            "service": "nexus-governance-api",
            "proposals": len(state.proposals),
        }

    @api.post("/skills/propose")
    def propose_skill(request: SkillProposalRequest) -> Dict[str, Any]:
        try:
            return state.propose_skill(
                proposal_id=request.proposal_id,
                model_id=request.model_id,
                skill=request.skill,
                rationale=request.rationale,
                timestamp=request.timestamp,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/skills/status/{proposal_id}")
    def proposal_status(proposal_id: str) -> Dict[str, Any]:
        record = state.get_proposal(proposal_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return record

    @api.get("/governance/proposals")
    def list_proposals() -> Dict[str, Any]:
        return state.list_proposals()

    @api.post("/governance/approve/{proposal_id}")
    def approve_proposal(
        proposal_id: str, request: ApprovalRequest
    ) -> Dict[str, Any]:
        try:
            record = state.review_proposal(
                proposal_id=proposal_id,
                decision=request.decision,
                reviewer=request.reviewer,
                reason=request.reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return record

    @api.get("/dashboard/stats")
    def dashboard_stats() -> Dict[str, Any]:
        return state.dashboard_stats()

    @api.on_event("shutdown")
    def close_db() -> None:
        state.close()

    return api


app = create_app()
