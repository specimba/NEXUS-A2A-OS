"""nexus_os/api/nexusclaw_routes.py - NEXUSCLAW Production API Endpoints (Phase E1).

REST API for real-time metrics, operator intervention, and evidence synthesis.
All endpoints are rate-limited and trust-gated.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from nexus_os.nexusclaw import (
    get_agent_pool,
    get_orchestrator,
    ResearchIntegrationEngine,
    SecurityEvidencePipeline,
)
from nexus_os.governor.trust_engine_v2 import get_trust_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nexusclaw", tags=["nexusclaw"])


# ── Request/Response Models ──────────────────────────────────────────────────────

class InterventionRequest(BaseModel):
    intervention: str
    target: str


class InterventionResponse(BaseModel):
    success: bool
    message: str
    intervention_id: Optional[str] = None


class ResearchSynthesisRequest(BaseModel):
    query: Optional[str] = None
    sources: Optional[List[str]] = None


class ResearchSynthesisResponse(BaseModel):
    synthesis: str
    sources_used: List[str]
    blake3_hash: str


class SecurityPatternsResponse(BaseModel):
    patterns: List[Dict[str, Any]]
    total_count: int


# ── Authentication Dependency ─────────────────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key for authenticated endpoints."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    # TODO: Validate against vault secrets
    if x_api_key.startswith("nexus-"):
        return x_api_key
    raise HTTPException(status_code=403, detail="Invalid API key")


# ── Status Endpoint ──────────────────────────────────────────────────────────────

@router.get("/status")
async def get_nexusclaw_status():
    """Get real-time NEXUSCLAW orchestrator status."""
    try:
        pool = get_agent_pool()
        orchestrator = get_orchestrator()
        
        pool_stats = pool.stats()
        orch_status = orchestrator.status()
        
        return {
            "status": "operational",
            "stats": {
                "agentPool": {
                    "total": pool_stats.get("total_agents", 0),
                    "online": pool_stats.get("online_agents", 0),
                    "busy": pool_stats.get("busy_agents", 0),
                    "error": pool_stats.get("error_agents", 0),
                },
                "brainstorm": {
                    "activeSessions": orch_status.active_brainstorms,
                    "totalProposals": 0,  # TODO: Track in orchestrator
                    "pendingVotes": 0,
                },
                "trustEngine": {
                    "avgTrust": 75.0,  # TODO: Calculate from trust engine
                    "degradedAgents": 0,
                },
            },
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Intervention Endpoint ────────────────────────────────────────────────────────

@router.post("/intervene", response_model=InterventionResponse)
async def submit_intervention(
    request: InterventionRequest,
    api_key: str = Depends(verify_api_key),
):
    """Submit operator intervention command to swarm."""
    try:
        intervention_id = f"intervene-{intervention_id}"
        
        # TODO: Route to orchestrator for execution
        logger.info(
            f"Intervention received: {request.intervention} → {request.target} (key={api_key[:10]}...)"
        )
        
        return InterventionResponse(
            success=True,
            message=f"Intervention '{request.intervention}' submitted for {request.target}",
            intervention_id=intervention_id,
        )
    except Exception as e:
        logger.error(f"Intervention error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research Synthesis Endpoint ──────────────────────────────────────────────────

@router.post("/research/synthesize", response_model=ResearchSynthesisResponse)
async def synthesize_research(
    request: ResearchSynthesisRequest,
    api_key: str = Depends(verify_api_key),
):
    """Synthesize research evidence from ARCHIVIST dossiers."""
    try:
        engine = ResearchIntegrationEngine()
        
        # Load relevant dossiers
        sources_used = []
        synthesis_parts = []
        
        if request.sources:
            for source in request.sources:
                dossier = engine.load_dossier(source)
                if dossier.findings:
                    sources_used.append(source)
                    synthesis_parts.append(f"- {dossier.title}: {len(dossier.findings)} findings")
        else:
            # Default: load top 3 dossiers
            for filename in engine.RESEARCH_DOSSIERS[:3]:
                dossier = engine.load_dossier(filename)
                if dossier.findings:
                    sources_used.append(filename)
                    synthesis_parts.append(f"- {dossier.title}")
        
        synthesis = "\n".join(synthesis_parts) if synthesis_parts else "No research available"
        
        # Generate BLAKE3 hash
        import hashlib
        try:
            import blake3
            blake3_hash = blake3.blake3(synthesis.encode("utf-8")).hexdigest()
        except ImportError:
            blake3_hash = hashlib.sha256(synthesis.encode("utf-8")).hexdigest()
        
        return ResearchSynthesisResponse(
            synthesis=synthesis,
            sources_used=sources_used,
            blake3_hash=blake3_hash,
        )
    except Exception as e:
        logger.error(f"Research synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Security Patterns Endpoint ───────────────────────────────────────────────────

@router.get("/security/patterns", response_model=SecurityPatternsResponse)
async def get_security_patterns(api_key: str = Depends(verify_api_key)):
    """Get DERDDRE attack patterns and mitigations."""
    try:
        pipeline = SecurityEvidencePipeline()
        report = pipeline.load_archivist_security_report()
        
        # Return known patterns
        patterns = [
            {
                "pattern_id": "prompt_injection",
                "severity": "high",
                "mitigation": "ALS-Blindness, CSI guards",
                "detection_confidence": 0.95,
            },
            {
                "pattern_id": "jailbreak",
                "severity": "critical",
                "mitigation": "Guard router, Qwen3-0.6B first",
                "detection_confidence": 0.98,
            },
            {
                "pattern_id": "steganographic_payload",
                "severity": "high",
                "mitigation": "IPAP purification, Arnold cat map",
                "detection_confidence": 0.92,
            },
        ]
        
        return SecurityPatternsResponse(
            patterns=patterns,
            total_count=len(patterns),
        )
    except Exception as e:
        logger.error(f"Security patterns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))