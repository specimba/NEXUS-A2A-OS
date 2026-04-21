from supabase import create_client
import os

# Initialize
supabase = create_client(
    os.getenv("SUPABASE_URL", "https://your-project.supabase.co"),
    os.getenv("SUPABASE_KEY", "eyJhbGc...")
)

def save_proposal(proposal_data):
    """Save GSPP proposal to Supabase"""
    result = supabase.table("proposals").insert({
        "proposal_id": proposal_data["proposal_id"],
        "model_id": proposal_data["model_id"],
        "skill_name": proposal_data["skill"]["name"],
        "status": "pending",
        "tokens_estimated": proposal_data["skill"]["estimated_tokens"]
    }).execute()
    return result

def update_trust(model_id, delta):
    """Update trust score"""
    # Get current
    current = supabase.table("trust_scores").select("*").eq("model_id", model_id).execute()
    if current.data:
        new_score = current.data[0]["trust_score"] + delta
        supabase.table("trust_scores").update({
            "trust_score": new_score,
            "total_proposals": current.data[0]["total_proposals"] + 1
        }).eq("model_id", model_id).execute()
    else:
        supabase.table("trust_scores").insert({
            "model_id": model_id,
            "trust_score": 50.0 + delta,
            "total_proposals": 1
        }).execute()