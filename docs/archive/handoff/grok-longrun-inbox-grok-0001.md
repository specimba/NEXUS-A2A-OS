---
id: NODE-MIG-GROK_LONGRUN_INBOX_GROK_0001
authority_scope: experimental
origin_sha256: a3f4fb70184a9fac39763d7fa80a2cf61fc0a74d08a8cf7f8131d1a53a6da5e6
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-EEC67C
---
# Grok Burst Task grok-0001

<!-- CANARY: 9794d5316d59210871fa51ee23f0b65a -->
Objective: classify the Grok MCP package into usable components, unsafe components, and NEXUS integration candidates.

Allowed source paths:

- `scratch/grok-files-53db86af/mcp_server/PHASE6_FINAL_HANDOFF.md`
- `scratch/grok-files-53db86af/mcp_server/README.md`
- `scratch/grok-files-53db86af/mcp_server/governed_mcp_server.py`
- `scratch/grok-files-53db86af/mcp_server/trustkernel/trustkernel_adapter.py`
- `scratch/grok-files-53db86af/NEXUS_Red_Team_Lab/docs/MCP_Red_Team_Lab_Specification.md`
- `nexus_os/mcp/server.py`
- `tests/mcp/test_governed_mcp_server.py`

Required outputs:

- `docs/handoff/grok-longrun/outbox/grok-0001.result.md`
- `docs/handoff/grok-longrun/outbox/grok-0001.evidence.json`

Hard rules:

- Do not execute code.
- Do not delete files.
- Do not use Git.
- Do not expose secrets.
- Do not write outside `docs/handoff/grok-longrun/outbox/`.
- Do not claim completion; use status `proposed`.

Acceptance gate:

- Every readiness claim must cite a local file path.
- Unsafe components must be clearly marked as not ready for integration.
- NEXUS existing MCP bridge must be compared before recommending reuse.

