"""
DoppelGround → Nexus GSPP Converter
"""
import json, re, uuid
from pathlib import Path
from datetime import datetime
import hashlib

class DoppelGroundConverter:
    def __init__(self, session_dir: str):
        self.session_path = Path(session_dir)
        self.export_md = self.session_path / "SESSION_EXPORT.md"
        self.mission_json = self.session_path / "mission_batch_v2.json"

    def parse_export(self):
        if not self.export_md.exists(): return {}
        content = self.export_md.read_text(encoding='utf-8')
        sections, current = {}, None
        for line in content.split('\n'):
            if line.startswith('## '):
                current = line[3:].strip().lower().replace(' ', '_')
                sections[current] = []
            elif current: sections[current].append(line)
        return {k: '\n'.join(v).strip() for k,v in sections.items()}

    def to_gspp_proposal(self, model_id: str):
        export_data = self.parse_export()
        proposal_id = str(uuid.uuid4())
        return {
            "proposal_id": proposal_id,
            "model_id": model_id,
            "skill": {
                "name": f"dg-session-{proposal_id[:8]}",
                "version": "0.1.0",
                "estimated_tokens": 12000
            },
            "rationale": export_data.get('executive_summary', 'DoppelGround session')[:500],
            "timestamp": datetime.now().isoformat() + "Z"
        }

if __name__ == "__main__":
    import sys
    converter = DoppelGroundConverter(sys.argv[2] if len(sys.argv)>2 else "./runs/latest")
    proposal = converter.to_gspp_proposal(sys.argv[4] if len(sys.argv)>4 else "test")
    print(json.dumps(proposal, indent=2))