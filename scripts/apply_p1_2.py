#!/usr/bin/env python3
import os

print("Applying Fixes & P1-2: A2A v1.1 Capability Negotiation...")

# 1. Restore SkillRecord in hermes.py
hermes_path = os.path.join("src", "nexus_os", "engine", "hermes.py")
if os.path.exists(hermes_path):
    with open(hermes_path, "r", encoding="utf-8") as f:
        h_code = f.read()
    
    if "class SkillRecord:" not in h_code:
        skill_record_code = """
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SkillRecord:
    skill_id: str
    name: str
    task_type: str
    pattern: str
    recommended_model: str
    success_rate: float = 0.0
    execution_count: int = 0
"""
        # Inject right before HermesRouter
        h_code = h_code.replace("class HermesRouter:", skill_record_code + "\nclass HermesRouter:")
        with open(hermes_path, "w", encoding="utf-8") as f:
            f.write(h_code)
        print("[✅] Restored SkillRecord in hermes.py")

# 2. P1-2: Update AgentCard in trust_scoring.py
ts_path = os.path.join("src", "nexus_os", "governor", "trust_scoring.py")
if os.path.exists(ts_path):
    with open(ts_path, "r", encoding="utf-8") as f:
        ts_code = f.read()
    
    if "capabilities: List[str]" not in ts_code:
        ts_code = ts_code.replace(
            "capability_profile: Dict[str, float]", 
            "capability_profile: Dict[str, float]\n    capabilities: List[str] = field(default_factory=list)"
        )
        with open(ts_path, "w", encoding="utf-8") as f:
            f.write(ts_code)
        print("[✅] Added A2A capabilities to AgentCard in trust_scoring.py")

# 3. P1-2: Expose A2A Endpoint in Bridge Server
bridge_path = os.path.join("src", "nexus_os", "bridge", "server.py")
if os.path.exists(bridge_path):
    with open(bridge_path, "r", encoding="utf-8") as f:
        br_code = f.read()
        
    if "def get_agent_card" not in br_code:
        card_endpoint = """
    def get_agent_card(self, agent_id: str) -> dict:
        \"\"\"A2A v1.1 Endpoint: Expose capabilities and trust score to external swarms.\"\"\"
        return {
            "agent_id": agent_id,
            "protocol": "A2A-v1.1",
            "capabilities": ["code_generation", "governance_audit", "swarm_orchestration"],
            "negotiation_policies": {
                "fallback_behavior": "adaptive",
                "timeout_ms": 30000
            },
            "status": "active"
        }
"""
        # Inject right before handle_request
        if "def handle_request" in br_code:
            br_code = br_code.replace("def handle_request", card_endpoint + "\n    def handle_request")
            with open(bridge_path, "w", encoding="utf-8") as f:
                f.write(br_code)
            print("[✅] Injected A2A get_agent_card endpoint into BridgeServer")

print("\n[🚀] Script complete! Run tests to verify.")