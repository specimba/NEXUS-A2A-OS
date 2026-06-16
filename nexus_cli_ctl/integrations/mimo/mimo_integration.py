"""
NEXUS Mimo CLI Integration & Stability
Syncs active models from ModelRelay to Mimo CLI config.
Implements connection testing and auto-retry with exponential backoff.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger("nexus.mimo")

class MimoConfig:
    """Mimo CLI configuration manager"""

    MIMO_CONFIG_PATH = Path(os.path.expanduser("~/.config/mimocode/mimocode.jsonc"))
    OPENCODE_CONFIG_PATH = Path(os.path.expanduser("~/.config/opencode/opencode.json"))
    MODELRELAY_URL = "http://127.0.0.1:7355/v1"
    RETRY_ATTEMPTS = 5
    RETRY_BACKOFF_BASE = 2

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load Mimo config from disk"""
        if not self.MIMO_CONFIG_PATH.exists():
            logger.warning(f"Mimo config not found: {self.MIMO_CONFIG_PATH}")
            return {"providers": {}}
        try:
            with open(self.MIMO_CONFIG_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                # Strip JSONC comments
                lines = []
                for line in content.split('\n'):
                    stripped = line.split('//')[0]
                    lines.append(stripped)
                return json.loads('\n'.join(lines))
        except Exception as e:
            logger.error(f"Failed to load Mimo config: {e}")
            return {"providers": {}}

    def _save_config(self) -> bool:
        """Save Mimo config to disk"""
        try:
            self.MIMO_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(self.config, indent=2)
            with open(self.MIMO_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to save Mimo config: {e}")
            return False

    def configure_nexus_god_relay(self) -> bool:
        """Configure the 'nexus GOD relay' provider in Mimo"""
        # Turkish-character-safe API key (uses dummy for URL safety)
        provider = {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Nexus God Relay",
            "options": {
                "baseURL": "http://127.0.0.1:7355/v1",
                "apiKey": "nexus-god-relay-dummy"
            },
            "models": {}
        }

        self.config.setdefault("providers", {})
        self.config["providers"]["nexus-god-relay"] = provider
        return self._save_config()

    async def sync_models(self) -> Dict:
        """Sync active models from ModelRelay to Mimo config"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.MODELRELAY_URL}/models", timeout=10) as resp:
                    if resp.status != 200:
                        return {"success": False, "error": f"HTTP {resp.status}"}
                    data = await resp.json()

            # Filter to only UP models
            models = []
            if isinstance(data, dict) and "data" in data:
                models = data["data"]
            elif isinstance(data, list):
                models = data

            active_models = [m for m in models if m.get("status") == "up"]
            logger.info(f"Found {len(active_models)} active models from ModelRelay")

            # Update Mimo config
            provider = self.config.setdefault("providers", {}).setdefault("nexus-god-relay", {})
            provider.setdefault("models", {})

            for model in active_models:
                model_id = model.get("id") or model.get("name")
                if model_id:
                    provider["models"][model_id] = {
                        "name": model_id,
                        "status": "active",
                        "synced_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }

            success = self._save_config()
            return {
                "success": success,
                "models_synced": len(active_models),
                "total_available": len(models)
            }
        except Exception as e:
            logger.error(f"Model sync failed: {e}")
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> Dict:
        """Test Mimo → ModelRelay connection stability"""
        results = {
            "config_valid": False,
            "config_path": str(self.MIMO_CONFIG_PATH),
            "providers_configured": [],
            "modelrelay_reachable": False,
            "test_results": []
        }

        # Check config file
        if self.MIMO_CONFIG_PATH.exists():
            results["config_valid"] = True
            results["providers_configured"] = list(self.config.get("providers", {}).keys())

        # Test ModelRelay reachability
        try:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(f"{self.MODELRELAY_URL}/models", timeout=5) as resp:
                    latency = (time.time() - start) * 1000
                    results["modelrelay_reachable"] = resp.status == 200
                    results["modelrelay_latency_ms"] = round(latency, 2)
                    results["modelrelay_status"] = resp.status
        except Exception as e:
            results["modelrelay_error"] = str(e)

        # Test with retry/backoff
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                start = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.MODELRELAY_URL}/chat/completions",
                        json={
                            "model": "test",
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        },
                        timeout=10
                    ) as resp:
                        latency = (time.time() - start) * 1000
                        results["test_results"].append({
                            "attempt": attempt + 1,
                            "status": resp.status,
                            "latency_ms": round(latency, 2),
                            "success": resp.status in [200, 404]  # 404 = model not found, but server reachable
                        })
            except Exception as e:
                results["test_results"].append({
                    "attempt": attempt + 1,
                    "success": False,
                    "error": str(e)
                })

            if attempt < self.RETRY_ATTEMPTS - 1:
                backoff = self.RETRY_BACKOFF_BASE ** attempt
                await asyncio.sleep(backoff)

        # Summary
        successes = sum(1 for r in results["test_results"] if r.get("success"))
        results["success_rate"] = f"{successes}/{self.RETRY_ATTEMPTS}"
        results["stable"] = successes >= 3

        return results

    def get_status(self) -> Dict:
        """Get current Mimo integration status"""
        return {
            "config_path": str(self.MIMO_CONFIG_PATH),
            "config_exists": self.MIMO_CONFIG_PATH.exists(),
            "providers": list(self.config.get("providers", {}).keys()),
            "nexus_god_relay_configured": "nexus-god-relay" in self.config.get("providers", {}),
            "models_count": len(self.config.get("providers", {}).get("nexus-god-relay", {}).get("models", {}))
        }


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS Mimo CLI Integration")
    parser.add_argument("--configure", action="store_true", help="Configure nexus-god-relay provider")
    parser.add_argument("--sync", action="store_true", help="Sync models from ModelRelay")
    parser.add_argument("--test", action="store_true", help="Test connection stability")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    mimo = MimoConfig()

    if args.configure:
        success = mimo.configure_nexus_god_relay()
        print(f"Configure: {'OK' if success else 'FAILED'}")
    elif args.sync:
        result = await mimo.sync_models()
        print(json.dumps(result, indent=2))
    elif args.test:
        result = await mimo.test_connection()
        print(json.dumps(result, indent=2))
    elif args.status:
        print(json.dumps(mimo.get_status(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
