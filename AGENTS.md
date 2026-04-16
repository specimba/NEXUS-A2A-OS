NEXUS OS Agent Protocol v3.0
============================
Bootstrap: Read 00_QUICKSTART.md first.
Source of Truth: cloud_pack/2_NEXUS_SOURCE.txt (Optimized Agent Logic)
Governance: 04_GOVERNANCE.md (KAIJU Rules)

Agent Limits:
- Hard-stop enforced by TokenGuard (5000 token reservation)
- Trust scoring via O(1) hot-path
- All actions audited in VAP Chain

Onboarding:
1. Clone & Install (see 00_QUICKSTART.md)
2. Run C5 Gate to verify environment
3. Review cloud_pack for low-token optimization patterns
