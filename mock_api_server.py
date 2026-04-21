"""
Mock API Server for OS Integration Team
Simulates Nexus and TWAVE APIs for development without access to core systems

Usage:
  python mock_api_server.py --port 7352
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import time
import random
import json
from datetime import datetime

app = FastAPI(title="Nexus OS Mock API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data stores
mock_models = [
    {"id": "qwen2.5-0.5b", "name": "Qwen2.5 0.5B", "status": "ready", "vram_mb": 1200},
    {"id": "qwen2.5-1.5b", "name": "Qwen2.5 1.5B", "status": "ready", "vram_mb": 2800},
    {"id": "deepseek-v3", "name": "DeepSeek V3", "status": "warming", "vram_mb": 0},
    {"id": "glm-5.1", "name": "GLM 5.1", "status": "stopped", "vram_mb": 0},
]

mock_proposals = {}
mock_artifacts = {}
request_count = 0

class ExecuteRequest(BaseModel):
    model_id: str
    prompt: str
    chi: Optional[int] = 32
    max_modules: Optional[int] = 8
    timeout_seconds: Optional[int] = 120

class ProposalRequest(BaseModel):
    proposal_id: str
    model_id: str
    skill: dict
    rationale: str
    timestamp: str

# ==================== NEXUS API (Port 7352) ====================

@app.get("/models")
async def get_models():
    """Get available models - for GeniusTurtle model selector"""
    return {
        "models": mock_models,
        "total": len(mock_models),
        "healthy_count": len([m for m in mock_models if m["status"] == "ready"])
    }

@app.get("/status")
async def get_status():
    """Get system status - for GeniusTurtle status ribbon"""
    return {
        "status": "operational",
        "uptime_seconds": int(time.time() % 86400),
        "active_requests": random.randint(0, 3),
        "gpu_temp_c": random.randint(45, 65),
        "vram_used_mb": random.randint(2000, 4000),
        "vram_total_mb": 8192,
        "models_ready": 2,
        "models_total": 4
    }

@app.post("/execute")
async def execute_model(request: ExecuteRequest):
    """Execute a model - for GeniusTurtle Run page"""
    global request_count
    request_count += 1
    
    # Simulate processing time
    processing_time = random.uniform(1.5, 4.0)
    time.sleep(min(processing_time, 0.5))  # Short sleep for demo
    
    # Simulate token usage
    tokens_in = len(request.prompt) // 4
    tokens_out = random.randint(50, 200)
    
    return {
        "request_id": f"req_{request_count:04d}",
        "status": "completed",
        "model_id": request.model_id,
        "output_text": f"Mock response to: '{request.prompt[:50]}...'\n\nThis is a simulated response from {request.model_id}. In production, this would be the actual model output. Token usage and timing are simulated for development purposes.",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "execution_time_ms": int(processing_time * 1000),
        "finish_reason": "stop",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/logs")
async def get_logs(lines: int = 100):
    """Get system logs - for GeniusTurtle Console"""
    log_entries = []
    for i in range(min(lines, 50)):
        timestamp = datetime.now().isoformat()
        levels = ["INFO", "DEBUG", "WARN"]
        messages = [
            "Model qwen2.5-0.5b ready",
            "Health check passed",
            "Request processed successfully",
            "VRAM usage: 2.1GB",
            "Token budget remaining: 45000"
        ]
        log_entries.append(f"{timestamp} [{random.choice(levels)}] {random.choice(messages)}")
    
    return {
        "logs": log_entries,
        "total_lines": len(log_entries),
        "truncated": lines > 50
    }

@app.post("/skills/propose")
async def propose_skill(proposal: ProposalRequest):
    """Submit skill proposal - for GSPP integration"""
    proposal_id = proposal.proposal_id
    
    # Store mock proposal
    mock_proposals[proposal_id] = {
        "proposal_id": proposal_id,
        "model_id": proposal.model_id,
        "skill_name": proposal.skill.get("name", "unknown"),
        "status": "pending",
        "submitted_at": datetime.now().isoformat(),
        "estimated_tokens": proposal.skill.get("estimated_tokens", 0)
    }
    
    # Simulate governance delay
    time.sleep(0.2)
    
    # Auto-approve for mock (in real system, this would be pending)
    mock_proposals[proposal_id]["status"] = "approved"
    mock_proposals[proposal_id]["governance_ticket"] = f"gov-{proposal_id[:8]}"
    
    return {
        "proposal_id": proposal_id,
        "status": "received",
        "governance_ticket": mock_proposals[proposal_id]["governance_ticket"],
        "vap_l1_hash": f"0x{random.getrandbits(64):016x}",
        "message": "Mock approval - in production, this would be pending governance review"
    }

@app.get("/skills/status/{proposal_id}")
async def get_proposal_status(proposal_id: str):
    """Check proposal status"""
    if proposal_id not in mock_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = mock_proposals[proposal_id]
    return {
        "proposal_id": proposal_id,
        "status": proposal["status"],
        "decision": {
            "kaiju_verdict": "pass",
            "owasp_asi_checks": {
                "ASI-04_supply_chain": "pass",
                "ASI-07_excessive_agency": "pass"
            },
            "token_guard": {
                "budget_allocated": proposal["estimated_tokens"],
                "budget_remaining": 50000 - proposal["estimated_tokens"],
                "verdict": "pass"
            },
            "asbom": {
                "asbom_id": f"asbom-{proposal_id[:8]}",
                "sbom_uri": f"file:///vault/asbom/{proposal_id}.json",
                "vulnerabilities_found": 0,
                "verdict": "pass"
            },
            "trust_impact": {
                "proposer_trust_delta": 0.3,
                "new_trust_score": 67.4
            }
        },
        "vap_l2_proof": f"0x{random.getrandbits(64):016x}",
        "install_command": f"nexus skill install {proposal_id}"
    }

@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Dashboard stats - for existing control center"""
    return {
        "main_keys": [
            {"name": "opencode", "usage": 1247, "last_used": "2m ago", "status": "healthy"},
            {"name": "nvidia", "usage": 892, "last_used": "5m ago", "status": "healthy"},
            {"name": "kilocode", "usage": 445, "last_used": "1h ago", "status": "healthy"},
            {"name": "groq", "usage": 2103, "last_used": "30s ago", "status": "healthy"}
        ],
        "research_keys": [
            {"name": "openai", "usage": 56, "last_used": "3h ago"},
            {"name": "anthropic", "usage": 23, "last_used": "1d ago"},
            {"name": "deepseek", "usage": 178, "last_used": "15m ago"},
            {"name": "glm", "usage": 89, "last_used": "2h ago"}
        ],
        "healthy_models": [
            {"id": "minimax-m2.5", "status": "passing"},
            {"id": "trinity-large-preview", "status": "passing"},
            {"id": "kimi-k2.5", "status": "passing"},
            {"id": "step-3.5-flash", "status": "passing"}
        ],
        "rate_limits": {
            "hourly": {"used": 2, "limit": 5},
            "daily": {"used": 7, "limit": 20}
        },
        "total_requests": request_count,
        "success_rate": 0.931,
        "avg_latency_ms": 234
    }

# ==================== TWAVE API (Port 7353) ====================
# This would normally be separate service, but included here for simplicity

twave_app = FastAPI(title="TWAVE Mock API", version="1.0.0")
twave_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@twave_app.get("/twave/health")
async def twave_health():
    """TWAVE health check"""
    return {
        "status": "ready",
        "python_path": "C:\\Users\\speci.000\\.unsloth\\studio\\unsloth_studio\\Scripts\\python.exe",
        "models_available": ["Qwen2.5-0.5B", "Qwen2.5-1.5B"],
        "vram_total_mb": 8192,
        "vram_free_mb": random.randint(5000, 7000),
        "chi_baseline": 32,
        "last_verification": datetime.now().isoformat()
    }

@twave_app.post("/twave/execute")
async def twave_execute(request: ExecuteRequest):
    """TWAVE execution"""
    # Simulate TWAVE processing
    time.sleep(random.uniform(0.5, 2.0))
    
    artifact_id = f"twave_{int(time.time())}"
    mock_artifacts[artifact_id] = {
        "model_id": request.model_id,
        "chi": request.chi,
        "prompt": request.prompt[:100]
    }
    
    return {
        "status": "success",
        "output_text": f"TWAVE executed {request.model_id} with chi={request.chi}. Output would appear here in production.",
        "tokens_used": random.randint(100, 300),
        "vram_peak_mb": random.randint(1800, 2500),
        "execution_time_ms": random.randint(2000, 5000),
        "artifact_path": f"/artifacts/twave/{artifact_id}",
        "artifact_id": artifact_id
    }

@twave_app.get("/twave/artifacts")
async def list_artifacts():
    """List TWAVE artifacts"""
    return {
        "artifacts": [
            {
                "id": aid,
                "model_id": data["model_id"],
                "chi": data["chi"],
                "created": datetime.now().isoformat()
            }
            for aid, data in list(mock_artifacts.items())[-10:]
        ]
    }

@twave_app.get("/twave/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Get specific artifact"""
    if artifact_id not in mock_artifacts:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return {
        "artifact_id": artifact_id,
        "data": mock_artifacts[artifact_id],
        "files": ["output.json", "manifest.json", "metrics.json"]
    }

# ==================== Combined App ====================

from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware

# Mount TWAVE app under same server for simplicity
app.mount("/twave", twave_app)

@app.get("/")
async def root():
    return {
        "service": "Nexus OS Mock API",
        "version": "1.0.0",
        "endpoints": {
            "nexus": ["/models", "/status", "/execute", "/logs", "/skills/propose", "/dashboard/stats"],
            "twave": ["/twave/health", "/twave/execute", "/twave/artifacts"]
        },
        "note": "This is a mock server for development. All responses are simulated."
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Nexus OS Mock API Server")
    print("=" * 60)
    print("Nexus API: http://localhost:7352")
    print("TWAVE API: http://localhost:7352/twave")
    print("")
    print("Available endpoints:")
    print("  GET  /models              - List models")
    print("  GET  /status              - System status")
    print("  POST /execute             - Execute model")
    print("  GET  /logs                - Get logs")
    print("  POST /skills/propose      - Submit proposal")
    print("  GET  /dashboard/stats     - Dashboard data")
    print("  GET  /twave/health        - TWAVE health")
    print("  POST /twave/execute       - TWAVE execute")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=7352, log_level="info")
