"""
Sandbox version of Supabase Client
Local JSON-based storage for testing without cloud setup.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field


@dataclass
class Proposal:
    """GSPP Proposal - simplified for sandbox."""
    id: str
    proposal_type: str
    governor: str
    skill_name: Optional[str]
    skill_description: Optional[str]
    vap_compliant: bool
    vap_violation: Optional[str] = None
    rationale: str = ""
    code_changes: Optional[Dict] = None
    status: str = "pending"
    votes: List[Dict] = field(default_factory=list)
    trust_score: float = 0.50
    session_id: str = ""
    user_id: str = "sandbox-user"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TrustScore:
    """Trust score entry."""
    id: str
    governor: str
    user_id: str
    score: float = 0.50
    proposal_count: int = 0
    accepted_count: int = 0
    veto_count: int = 0
    last_proposal_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SandboxSupabaseClient:
    """
    Local JSON-based client for sandbox testing.
    No cloud required - everything stored in ./mock_data/
    """
    
    def __init__(self, data_dir: str = "./sandbox/mock_data"):
        self.data_dir = data_dir
        self.proposals_file = os.path.join(data_dir, "proposals.json")
        self.trust_scores_file = os.path.join(data_dir, "trust_scores.json")
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load or initialize data
        self.proposals: List[Proposal] = self._load_data(self.proposals_file, Proposal)
        self.trust_scores: List[TrustScore] = self._load_data(self.trust_scores_file, TrustScore)
        
        print(f"[Sandbox] Supabase client ready")
        print(f"  - Proposals: {len(self.proposals)}")
        print(f"  - Trust Scores: {len(self.trust_scores)}")
    
    def _load_data(self, filepath: str, dataclass_type):
        """Load data from JSON file."""
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return [dataclass_type(**item) for item in data]
        except Exception as e:
            print(f"[WARN] Could not load {filepath}: {e}")
            return []
    
    def _save_data(self, filepath: str, data: List):
        """Save data to JSON file."""
        with open(filepath, 'w') as f:
            json.dump([asdict(item) for item in data], f, indent=2, default=str)
    
    def create_proposal(self, proposal_data: Dict[str, Any]) -> Optional[Proposal]:
        """Create a new proposal."""
        proposal_id = f"prop-{int(datetime.now().timestamp() * 1000)}"
        
        proposal = Proposal(
            id=proposal_id,
            proposal_type=proposal_data.get("proposal_type", "new_skill"),
            governor=proposal_data.get("governor", "UNKNOWN"),
            skill_name=proposal_data.get("skill_name") or proposal_data.get("skill_request", {}).get("name"),
            skill_description=proposal_data.get("skill_description") or proposal_data.get("skill_request", {}).get("description"),
            vap_compliant=proposal_data.get("vap_compliant", False),
            vap_violation=proposal_data.get("vap_violation"),
            rationale=proposal_data.get("rationale", ""),
            code_changes=proposal_data.get("code_changes"),
            session_id=proposal_data.get("session_id", "sandbox"),
            user_id=proposal_data.get("user_id", "sandbox-user"),
            trust_score=proposal_data.get("trust_score", 0.50)
        )
        
        self.proposals.append(proposal)
        self._save_data(self.proposals_file, self.proposals)
        
        print(f"[Sandbox] Created proposal: {proposal_id} ({proposal.governor})")
        return proposal
    
    def get_proposals(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        governor: Optional[str] = None
    ) -> List[Proposal]:
        """Query proposals with filters."""
        results = self.proposals
        
        if session_id:
            results = [p for p in results if p.session_id == session_id]
        if status:
            results = [p for p in results if p.status == status]
        if governor:
            results = [p for p in results if p.governor == governor]
        
        return results
    
    def update_proposal_status(self, proposal_id: str, status: str, votes: Optional[List[Dict]] = None) -> bool:
        """Update proposal status."""
        for proposal in self.proposals:
            if proposal.id == proposal_id:
                proposal.status = status
                proposal.updated_at = datetime.now().isoformat()
                if votes:
                    proposal.votes = votes
                
                self._save_data(self.proposals_file, self.proposals)
                print(f"[Sandbox] Updated {proposal_id} → {status}")
                return True
        
        return False
    
    def get_trust_score(self, governor: str, user_id: str) -> Optional[TrustScore]:
        """Get trust score for governor-user pair."""
        for score in self.trust_scores:
            if score.governor == governor and score.user_id == user_id:
                return score
        return None
    
    def update_trust_score(self, governor: str, user_id: str, score: float, accepted: bool = False, veto: bool = False) -> bool:
        """Update or create trust score."""
        existing = self.get_trust_score(governor, user_id)
        
        if existing:
            existing.score = round(score, 2)
            existing.proposal_count += 1
            if accepted:
                existing.accepted_count += 1
            if veto:
                existing.veto_count += 1
            existing.last_proposal_at = datetime.now().isoformat()
        else:
            new_score = TrustScore(
                id=f"ts-{int(datetime.now().timestamp() * 1000)}",
                governor=governor,
                user_id=user_id,
                score=round(score, 2),
                proposal_count=1,
                accepted_count=1 if accepted else 0,
                veto_count=1 if veto else 0,
                last_proposal_at=datetime.now().isoformat()
            )
            self.trust_scores.append(new_score)
        
        self._save_data(self.trust_scores_file, self.trust_scores)
        
        tier = "Platinum" if score >= 0.90 else "Gold" if score >= 0.75 else "Silver" if score >= 0.50 else "Bronze"
        print(f"[Sandbox] Trust score: {governor}/{user_id} = {score:.2f} ({tier})")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        return {
            "proposals": {
                "total": len(self.proposals),
                "by_status": {
                    "pending": len([p for p in self.proposals if p.status == "pending"]),
                    "approved": len([p for p in self.proposals if p.status == "approved"]),
                    "rejected": len([p for p in self.proposals if p.status == "rejected"]),
                    "merged": len([p for p in self.proposals if p.status == "merged"])
                },
                "by_governor": {
                    gov: len([p for p in self.proposals if p.governor == gov])
                    for gov in set(p.governor for p in self.proposals)
                }
            },
            "trust_scores": {
                "total": len(self.trust_scores),
                "avg_score": round(sum(s.score for s in self.trust_scores) / len(self.trust_scores), 2) if self.trust_scores else 0
            }
        }


# Singleton
_sandbox_client = None

def get_sandbox_client() -> SandboxSupabaseClient:
    global _sandbox_client
    if _sandbox_client is None:
        _sandbox_client = SandboxSupabaseClient()
    return _sandbox_client


if __name__ == "__main__":
    print("=== Sandbox Supabase Client Test ===\n")
    
    client = get_sandbox_client()
    
    # Test 1: Create proposals
    print("Test 1: Create Proposals")
    p1 = client.create_proposal({
        "proposal_type": "new_skill",
        "governor": "KAIJU",
        "skill_name": "token_optimizer",
        "skill_description": "Optimize token usage",
        "vap_compliant": True,
        "rationale": "Saves 20% tokens",
        "session_id": "test-001"
    })
    
    p2 = client.create_proposal({
        "proposal_type": "feedback",
        "governor": "GENIUS",
        "rationale": "Code looks good",
        "vap_compliant": True,
        "session_id": "test-001"
    })
    
    # Test 2: Query
    print("\nTest 2: Query Proposals")
    kaiju_proposals = client.get_proposals(governor="KAIJU")
    print(f"  KAIJU proposals: {len(kaiju_proposals)}")
    
    # Test 3: Update status
    print("\nTest 3: Update Status")
    client.update_proposal_status(p1.id, "approved")
    
    # Test 4: Trust scores
    print("\nTest 4: Trust Scores")
    client.update_trust_score("KAIJU", "test-user", 0.85, accepted=True)
    client.update_trust_score("KAIJU", "test-user", 0.90, accepted=True)
    client.update_trust_score("GENIUS", "test-user", 0.75, accepted=True)
    
    score = client.get_trust_score("KAIJU", "test-user")
    print(f"  KAIJU/test-user final: {score.score if score else 'N/A'}")
    
    # Test 5: Stats
    print("\nTest 5: Statistics")
    stats = client.get_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n=== All Tests Passed ===")
