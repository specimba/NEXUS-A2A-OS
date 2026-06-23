"""bridge/intern_discovery.py — Intern Discovery Platform & SCP Tool Adapter

Connects to the Chinese Intern Discovery scientific research platform,
manages JWT authentication tokens securely, and translates Science Context
Protocol (SCP) tools into standard governed MCP declarations for execution.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from nexus_os.mcp.client import MCPToolInfo, MCPCallResult

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_INTERN_BASE_URL = "https://discovery.intern-ai.org.cn"
INTERN_AGENT_ID = "intern-discovery-bridge"


# ── Client & Adapter ───────────────────────────────────────────────────────────


class InternDiscoveryClient:
    """Client for Intern Discovery REST API with SCP-to-MCP translation."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        import os
        self.base_url = (base_url or DEFAULT_INTERN_BASE_URL).rstrip("/")
        # Fetch token from vault/env if not passed
        self.token = token or os.environ.get("NEXUS_INTERN_DISCOVERY_TOKEN", "")
        self._scp_tools: Dict[str, MCPToolInfo] = {}
        self._initialized = False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def call_api(self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Call Intern Discovery platform REST API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            data = json.dumps(payload).encode("utf-8") if payload else None
            req = urllib.request.Request(
                url,
                data=data,
                headers=self._get_headers(),
                method=method
            )
            # Use a timeout of 10s for general REST endpoints
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if resp.status in (200, 201):
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug("Intern Discovery API call failed: %s (url=%s)", e, url)
        return None

    def discover_scp_tools(self) -> List[MCPToolInfo]:
        """Discovers the available scientific tools (SCP Hub mock/discovery)."""
        # In the actual environment, we fetch from /org/ailab/workspace/iframe?url=https://scphub.intern-ai.org.cn/
        # Here we mock discovery from the curation list of 8 primary scientific tools
        scp_definitions = [
            {
                "name": "multiomics_integration",
                "description": "Integrate multi-omics data: gene expression, protein data, pathways.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "uniprot_id": {"type": "string", "description": "UniProt Accession ID"},
                        "genes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["uniprot_id"],
                },
                "governance": {"level": "medium", "side_effects": False}
            },
            {
                "name": "polymer_property_analysis",
                "description": "Analyze polymer composition, symmetry, density, and crystal lattice.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "composition": {"type": "string", "description": "Chemical composition string"},
                    },
                    "required": ["composition"],
                },
                "governance": {"level": "low", "side_effects": False}
            },
            {
                "name": "chemical_safety_assessment",
                "description": "Assess chemical toxicity, FDA drug warnings, and ADMET predictions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "compound_name": {"type": "string", "description": "Name of chemical compound"},
                    },
                    "required": ["compound_name"],
                },
                "governance": {"level": "high", "side_effects": False}
            },
            {
                "name": "alanine_scanning_pipeline",
                "description": "Design alanine mutations and calculate protein sequence attributes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sequence": {"type": "string", "description": "Amino acid sequence"},
                    },
                    "required": ["sequence"],
                },
                "governance": {"level": "low", "side_effects": False}
            },
            {
                "name": "bioassay_analysis",
                "description": "Fetch PubChem assay summaries and ChEMBL bioactivity data.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "assay_id": {"type": "string", "description": "PubChem Assay ID (AID)"},
                    },
                    "required": ["assay_id"],
                },
                "governance": {"level": "low", "side_effects": False}
            },
            {
                "name": "admet_druglikeness_report",
                "description": "Generate ADMET properties and druglikeness reports for a molecule.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string of the molecule"},
                    },
                    "required": ["smiles"],
                },
                "governance": {"level": "low", "side_effects": False}
            },
            {
                "name": "protein_drug_interaction",
                "description": "Predict binding affinity (Kd/Ki) and model interactions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Drug SMILES"},
                        "sequence": {"type": "string", "description": "Protein sequence"},
                    },
                    "required": ["smiles", "sequence"],
                },
                "governance": {"level": "medium", "side_effects": False}
            },
            {
                "name": "drug_warning_report",
                "description": "Fetch FDA Boxed Warnings, adverse effects, and environmental alerts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "drug_name": {"type": "string", "description": "Generic or brand name of drug"},
                    },
                    "required": ["drug_name"],
                },
                "governance": {"level": "high", "side_effects": False}
            }
        ]

        self._scp_tools = {
            raw["name"]: MCPToolInfo.from_mcp(raw) for raw in scp_definitions
        }
        self._initialized = True
        return list(self._scp_tools.values())

    def call_scp_tool(self, name: str, arguments: Dict[str, Any]) -> MCPCallResult:
        """Call a scientific tool mapped from the SCP protocol."""
        if not self._initialized:
            self.discover_scp_tools()

        tool = self._scp_tools.get(name)
        if not tool:
            return MCPCallResult(
                tool=name,
                is_error=True,
                error_message=f"SCP Tool {name} not found in registry",
            )

        # In production, this issues a call to model services on the platform
        # POST /api/model/services/{service_id}/app/
        # Here we mock the invocation response
        logger.info("Calling Intern Discovery SCP tool %s with args: %s", name, arguments)
        
        # Simple simulated response for testing and verification
        simulated_data = {
            "success": True,
            "tool": name,
            "output": {
                "message": f"Successfully executed scientific tool {name}",
                "inputs_received": arguments,
                "status": "completed",
                "results": {
                    "confidence_score": 0.945,
                    "records_created": 1,
                    "parsed_fields": list(arguments.keys()),
                }
            }
        }
        
        return MCPCallResult(
            tool=name,
            result=simulated_data,
            blocked=False,
            is_error=False,
        )
