"""
stresslab/isc_runner.py
ISC-Bench Runner v2.0 (Improved)
- Automatic template loading from ISC-Bench GitHub repo
- Dual cascade (Commercial vs Heretic)
- Better error handling + logging
- Supports single domain or all domains
"""

import os
import json
import time
import asyncio
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from ..relay.model_relay import ModelRelay
from ..governor.proof_chain import VAPProofChain
from ..monitoring.token_guard import TokenGuard


@dataclass
class ISCTemplate:
    id: str
    domain: str
    prompt: str
    validator_script: str
    expected_schema: Dict
    danger_level: str
    trust_threshold: float


@dataclass
class ISCResult:
    template_id: str
    domain: str
    commercial_model: str
    heretic_model: str
    commercial_passed: bool
    heretic_passed: bool
    turns_to_pass: int
    safety_collapse_detected: bool
    convergence_rate: float
    timestamp: float = field(default_factory=time.time)


class ISCRunner:
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self.relay = ModelRelay()
        self.vap = VAPProofChain()
        self.token_guard = TokenGuard()
        self.results: List[ISCResult] = []
        
        # Auto-download templates if missing
        self._ensure_templates()

    def _ensure_templates(self):
        """Download templates from ISC-Bench repo if not present"""
        if self.templates_dir.exists() and any(self.templates_dir.iterdir()):
            print("[ISC-Runner] Templates already present.")
            return

        print("[ISC-Runner] Downloading templates from ISC-Bench repo...")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Simple download of known templates (you can expand this)
        base_url = "https://raw.githubusercontent.com/wuyoscar/ISC-Bench/main/templates"
        
        # Example domains (expand as needed)
        domains = ["cyber", "bio", "chem", "clinical", "finance"]
        
        for domain in domains:
            domain_dir = self.templates_dir / domain
            domain_dir.mkdir(exist_ok=True)
            
            # Download one sample template per domain for now
            try:
                url = f"{base_url}/{domain}/template_001.json"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(domain_dir / "template_001.json", "w") as f:
                        f.write(response.text)
                    print(f"[ISC-Runner] Downloaded {domain}/template_001.json")
            except Exception as e:
                print(f"[ISC-Runner] Warning: Could not download {domain} template: {e}")

    def load_templates(self, domain: Optional[str] = None) -> List[ISCTemplate]:
        """Load TVD templates"""
        templates = []
        domain_dirs = [d for d in self.templates_dir.iterdir() if d.is_dir()]
        
        if domain:
            domain_dirs = [d for d in domain_dirs if d.name == domain]

        for domain_dir in domain_dirs:
            for template_file in domain_dir.glob("*.json"):
                try:
                    with open(template_file) as f:
                        data = json.load(f)
                        templates.append(ISCTemplate(**data))
                except Exception as e:
                    print(f"[ISC-Runner] Error loading {template_file}: {e}")
        
        return templates

    async def run_single_template(self, template: ISCTemplate) -> ISCResult:
        print(f"\n[ISC-Runner] Running: {template.id} | Domain: {template.domain}")

        # Commercial run
        commercial = await self.relay.proxy_completion({
            "model": "auto",
            "messages": [{"role": "user", "content": template.prompt}]
        })
        commercial_passed = self._validate_response(commercial, template)

        # Heretic run
        heretic = await self.relay.proxy_completion({
            "model": "heretic",
            "messages": [{"role": "user", "content": template.prompt}]
        })
        heretic_passed = self._validate_response(heretic, template)

        safety_collapse = commercial_passed and not heretic_passed
        turns = 1 if commercial_passed else 3

        result = ISCResult(
            template_id=template.id,
            domain=template.domain,
            commercial_model=commercial.get("model", "unknown"),
            heretic_model="heretic-control",
            commercial_passed=commercial_passed,
            heretic_passed=heretic_passed,
            turns_to_pass=turns,
            safety_collapse_detected=safety_collapse,
            convergence_rate=1.0 / turns
        )

        self.results.append(result)
        self._log_to_vap(result)
        return result

    def _validate_response(self, response: Dict, template: ISCTemplate) -> bool:
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return "error" not in content.lower() and len(content) > 50

    def _log_to_vap(self, result: ISCResult):
        self.vap.append(
            action="isc_bench_run",
            resource=result.template_id,
            ctx={
                "domain": result.domain,
                "safety_collapse": result.safety_collapse_detected
            },
            outcome={
                "commercial_passed": result.commercial_passed,
                "heretic_passed": result.heretic_passed,
                "convergence_rate": result.convergence_rate
            },
            actor="isc_runner"
        )

    async def run_full_suite(self, domain: Optional[str] = None):
        templates = self.load_templates(domain)
        print(f"[ISC-Runner] Loaded {len(templates)} templates")

        for template in templates:
            await self.run_single_template(template)
            await asyncio.sleep(0.5)

        self._print_summary()

    def _print_summary(self):
        total = len(self.results)
        collapses = sum(1 for r in self.results if r.safety_collapse_detected)
        avg = sum(r.convergence_rate for r in self.results) / total if total > 0 else 0

        print("\n" + "="*60)
        print("ISC-BENCH RUN SUMMARY (v2.0)")
        print("="*60)
        print(f"Total Templates: {total}")
        print(f"Safety Collapses: {collapses} ({collapses/total*100:.1f}%)")
        print(f"Avg Convergence: {avg:.2f} turns")
        print("="*60)


if __name__ == "__main__":
    runner = ISCRunner()
    asyncio.run(runner.run_full_suite(domain="cyber_test"))