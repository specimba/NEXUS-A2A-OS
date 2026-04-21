"""
Sandbox version of Langfuse Tracker
Simplified for local testing with full mock support.
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class MockTrace:
    """Mock trace object for sandbox testing."""
    id: str
    name: str
    data: Dict[str, Any]
    created_at: str
    
    def generation(self, **kwargs):
        return MockGeneration(kwargs)
    
    def update(self, **kwargs):
        self.data.update(kwargs)
        print(f"  [Mock] Trace updated: {kwargs}")


@dataclass
class MockGeneration:
    """Mock generation object."""
    data: Dict[str, Any]
    id: str = "mock-gen"
    
    def __post_init__(self):
        self.id = f"gen-{int(time.time() * 1000)}"
    
    def update(self, **kwargs):
        self.data.update(kwargs)


class SandboxLangfuseTracker:
    """
    Simplified Langfuse tracker for sandbox testing.
    No external dependencies - everything is local/mock.
    """
    
    MODEL_PRICING = {
        "deepseek-r1:8b": (0.0001, 0.0002),
        "nemotron-3-nano:4b": (0.00005, 0.0001),
        "mock-model": (0.00001, 0.00001),
        "default": (0.0001, 0.0002)
    }
    
    def __init__(self, storage_path: str = "./sandbox/mock_data/traces.json"):
        self.traces = []
        self.storage_path = storage_path
        self.session_count = 0
        print("[Sandbox] Langfuse tracker initialized (mock mode)")
    
    def track_model_call(
        self,
        model_id: str = "mock-model",
        prompt: str = "test prompt",
        response: str = "test response",
        latency_ms: float = 500,
        tokens_in: int = 10,
        tokens_out: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: str = "sandbox-user",
        proposal_id: Optional[str] = None
    ) -> MockTrace:
        """Track a model call - always works in sandbox."""
        
        # Calculate cost
        pricing = self.MODEL_PRICING.get(model_id, self.MODEL_PRICING["default"])
        cost_usd = (tokens_in / 1000 * pricing[0]) + (tokens_out / 1000 * pricing[1])
        
        # Create trace
        trace_id = f"trace-{int(time.time() * 1000)}-{self.session_count}"
        self.session_count += 1
        
        trace_data = {
            "model": model_id,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "response": response[:100] + "..." if len(response) > 100 else response,
            "latency_ms": latency_ms,
            "tokens": {"in": tokens_in, "out": tokens_out, "total": tokens_in + tokens_out},
            "cost_usd": round(cost_usd, 6),
            "metadata": metadata or {},
            "session_id": session_id or f"sandbox-session-{self.session_count}",
            "user_id": user_id,
            "proposal_id": proposal_id
        }
        
        trace = MockTrace(
            id=trace_id,
            name=f"model_call_{model_id}",
            data=trace_data,
            created_at=datetime.now().isoformat()
        )
        
        self.traces.append(asdict(trace))
        
        print(f"[Sandbox] Traced: {model_id} | {tokens_in+tokens_out} tokens | ${cost_usd:.6f}")
        
        return trace
    
    def log_feedback(self, trace_id: str, score: float, comment: str = "", name: str = "quality"):
        """Log feedback for a trace."""
        print(f"[Sandbox] Feedback: {trace_id} | {name}={score} | {comment}")
        
        # Update trace
        for trace in self.traces:
            if trace["id"] == trace_id:
                trace["feedback"] = {"name": name, "score": score, "comment": comment}
                break
    
    def log_gspp_proposal(self, proposal_data: Dict, session_id: str, user_id: str = "sandbox-user"):
        """Log a GSPP proposal."""
        trace_id = f"gspp-{int(time.time() * 1000)}"
        
        trace = MockTrace(
            id=trace_id,
            name="gspp_proposal",
            data={
                "proposal_type": proposal_data.get("proposal_type"),
                "governor": proposal_data.get("governor"),
                "skill_name": proposal_data.get("skill_request", {}).get("name"),
                "vap_compliant": proposal_data.get("vap_compliant", False),
                "session_id": session_id,
                "user_id": user_id
            },
            created_at=datetime.now().isoformat()
        )
        
        self.traces.append(asdict(trace))
        print(f"[Sandbox] GSPP Proposal: {proposal_data.get('governor')} | {proposal_data.get('proposal_type')}")
        
        return trace
    
    def save_traces(self):
        """Save all traces to JSON file."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.traces, f, indent=2)
        print(f"[Sandbox] Saved {len(self.traces)} traces to {self.storage_path}")
    
    def get_stats(self) -> Dict:
        """Get sandbox statistics."""
        if not self.traces:
            return {"total_traces": 0}
        
        total_cost = sum(t.get("data", {}).get("cost_usd", 0) for t in self.traces)
        total_tokens = sum(
            t.get("data", {}).get("tokens", {}).get("total", 0) 
            for t in self.traces
        )
        
        return {
            "total_traces": len(self.traces),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "models_used": list(set(
                t.get("data", {}).get("model", "unknown") 
                for t in self.traces
            ))
        }


# Singleton for sandbox
_sandbox_tracker = None

def get_sandbox_tracker() -> SandboxLangfuseTracker:
    global _sandbox_tracker
    if _sandbox_tracker is None:
        _sandbox_tracker = SandboxLangfuseTracker()
    return _sandbox_tracker


if __name__ == "__main__":
    print("=== Sandbox Langfuse Tracker Test ===\n")
    
    tracker = get_sandbox_tracker()
    
    # Test 1: Model call
    print("Test 1: Model Call Tracking")
    trace1 = tracker.track_model_call(
        model_id="deepseek-r1:8b",
        prompt="Explain quantum computing in simple terms",
        response="Quantum computing uses qubits which can be 0, 1, or both at once...",
        latency_ms=850,
        tokens_in=15,
        tokens_out=120,
        metadata={"test": True, "governor": "KAIJU"}
    )
    
    # Test 2: Feedback
    print("\nTest 2: Feedback Logging")
    tracker.log_feedback(trace1.id, score=0.95, comment="Great explanation!")
    
    # Test 3: GSPP proposal
    print("\nTest 3: GSPP Proposal")
    gspp_trace = tracker.log_gspp_proposal(
        proposal_data={
            "proposal_type": "new_skill",
            "governor": "KAIJU",
            "skill_request": {"name": "token_compressor", "description": "Compress prompts"},
            "vap_compliant": True
        },
        session_id="sandbox-test-001"
    )
    
    # Test 4: Stats
    print("\nTest 4: Statistics")
    stats = tracker.get_stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")
    
    # Test 5: Save
    print("\nTest 5: Save Traces")
    tracker.save_traces()
    
    print("\n=== All Tests Passed ===")
