#!/usr/bin/env python3
"""P1-2: A2A v1.1 Capability Negotiation Builder"""
import os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Inject capabilities into AgentCard
trust_path = os.path.join(REPO, "src", "nexus_os", "governor", "trust_scoring.py")
with open(trust_path, "r", encoding="utf-8") as f:
    code = f.read()

if "capabilities:" not in code:
    # Find AgentCard dataclass and inject field after capability_profile
    pattern = r"(capability_profile:\s*(?:dict|Dict\[str,\s*Any\])\s*=\s*field\(default_factory=dict\))"
    match = re.search(pattern, code)
    if match:
        inject = f"{match.group(1)}\n    capabilities: List[str] = field(default_factory=list)  # A2A v1.1"
        code = code.replace(match.group(1), inject)
        with open(trust_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("[✅] Added capabilities: List[str] to AgentCard")
    else:
        print("[⚠️] Anchor not found in AgentCard. Manual inject required.")

# 2. Add get_agent_card method to BridgeServer
bridge_path = os.path.join(REPO, "src", "nexus_os", "bridge", "server.py")
with open(bridge_path, "r", encoding="utf-8") as f:
    code = f.read()

if "def get_agent_card" not in code:
    method = '''
    def get_agent_card(self, agent_id: str) -> Dict[str, Any]:
        """A2A v1.1: Expose agent capabilities for inter-agent negotiation."""
        # In production: pull from TrustScorer/AgentCard registry
        return {
            "agent_id": agent_id,
            "protocol": "A2A-v1.1",
            "capabilities": ["code_generation", "governance_audit", "swarm_orchestration"],
            "trust_band": "COMMUNITY_VERIFIED",
            "status": "active"
        }
'''
    # Insert before handle_request
    code = code.replace("def handle_request", method + "\n    def handle_request")
    with open(bridge_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[✅] Injected get_agent_card() into BridgeServer")

print("\n[🚀] P1-2: A2A v1.1 Integration applied.")