#!/usr/bin/env python3
"""GMR & VAP Dependency Harmonization Patch"""
import os

print("Applying surgical import fixes...")

# 1. Fix rotator.py (Inject missing GMRSelection dataclass)
rotator_path = os.path.join("src", "nexus_os", "gmr", "rotator.py")
if os.path.exists(rotator_path):
    with open(rotator_path, "r", encoding="utf-8") as f:
        rotator_code = f.read()

    if "class GMRSelection:" not in rotator_code:
        selection_dataclass = """
@dataclass
class GMRSelection:
    primary: str
    fallbacks: List[str]
    reason: str
    budget_remaining: int
    tier_used: int
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0
"""
        # Inject right before ModelPool
        rotator_code = rotator_code.replace("class ModelPool(Enum):", selection_dataclass + "\nclass ModelPool(Enum):")
        with open(rotator_path, "w", encoding="utf-8") as f:
            f.write(rotator_code)
        print("[✅] Injected GMRSelection into rotator.py")

# 2. Fix gmr/__init__.py (Export GMRSelection)
init_path = os.path.join("src", "nexus_os", "gmr", "__init__.py")
if os.path.exists(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        init_code = f.read()
    
    if "GMRSelection" not in init_code:
        init_code = init_code.replace(
            "GeniusModelRotator, ModelProfile, ModelPool,", 
            "GeniusModelRotator, ModelProfile, ModelPool, GMRSelection,"
        )
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_code)
        print("[✅] Exported GMRSelection in gmr/__init__.py")

# 3. Fix proof_chain.py (Add backward-compatible alias for TrustScoring)
proof_chain_path = os.path.join("src", "nexus_os", "governor", "proof_chain.py")
if os.path.exists(proof_chain_path):
    with open(proof_chain_path, "r", encoding="utf-8") as f:
        pc_code = f.read()
    
    if "ProofChain =" not in pc_code:
        # Add alias at the very end
        pc_code += "\n# Backward compatibility aliases for older modules\nProofChain = VAPProofChain\n"
        
        # Add 'verify' alias inside VAPProofChain if missing
        if "def verify(" not in pc_code:
            pc_code = pc_code.replace(
                "def verify_chain(self", 
                "def verify(self, *args, **kwargs): return self.verify_chain(*args, **kwargs)\n\n    def verify_chain(self"
            )
        
        with open(proof_chain_path, "w", encoding="utf-8") as f:
            f.write(pc_code)
        print("[✅] Added ProofChain and verify() aliases to proof_chain.py")

print("\n[🚀] Fixes applied. Proceed to re-run team_check.py.")