"""
NEXUS A2A Bridge Health Monitor
Continuously monitors the Grok MCP Bridge A2A endpoints:
- /.well-known/agent.json (Agent Card discovery)
- /a2a/tasks/send (JSON-RPC submit)
- /a2a/tasks/get (JSON-RPC fetch)
- /health (server health)
- /a2a/discover (discovery alias)

Reports status to UnifiedStateManager and alerts on failure.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional
import aiohttp

logger = logging.getLogger("nexus.a2a_monitor")


class A2ABridgeHealthMonitor:
    """Monitor A2A bridge health and report to state manager"""

    CHECK_INTERVAL = 30
    REQUEST_TIMEOUT = 10

    def __init__(self, state_manager=None):
        self.sm = state_manager
        self.running = False
        self.local_url = "http://localhost:7354"
        self.public_url: Optional[str] = None
        self.last_status = {}
        self.failure_count = 0
        self.success_count = 0

    async def start(self):
        """Start the monitor"""
        if self.running:
            return
        self.running = True
        logger.info("A2A Bridge Health Monitor started")
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self.running = False

    async def _monitor_loop(self):
        """Run checks on interval"""
        while self.running:
            try:
                await self._run_checks()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _run_checks(self):
        """Run all health checks and update state"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "local": await self._check_endpoint(f"{self.local_url}/health", "Health"),
            "agent_card": await self._check_endpoint(
                f"{self.local_url}/.well-known/agent.json", "Agent Card"
            ),
            "discover": await self._check_endpoint(
                f"{self.local_url}/a2a/discover", "Discover"
            ),
            "tasks_get": await self._check_jsonrpc(
                f"{self.local_url}/a2a/tasks/get", "Tasks Get", test=True
            ),
        }

        # If we have a public URL, check that too
        if self.public_url:
            result["public"] = await self._check_endpoint(
                f"{self.public_url}/health", "Public Health"
            )

        # Determine overall status
        local_healthy = (
            result["local"].get("ok", False) and
            result["agent_card"].get("ok", False)
        )

        if local_healthy:
            self.success_count += 1
            self.failure_count = 0
        else:
            self.failure_count += 1

        result["healthy"] = local_healthy
        result["consecutive_failures"] = self.failure_count
        result["consecutive_successes"] = self.success_count
        result["public_url"] = self.public_url

        self.last_status = result

        # Publish to state manager
        if self.sm:
            await self.sm.publish(
                "integrations.a2a_bridge",
                {
                    "url": self.public_url or self.local_url,
                    "alive": local_healthy,
                    "details": result,
                    "consecutive_failures": self.failure_count
                },
                source="a2a_monitor"
            )

        if not local_healthy and self.failure_count == 3:
            logger.critical(f"A2A Bridge down for {self.failure_count} consecutive checks!")

    async def _check_endpoint(self, url: str, name: str) -> Dict:
        """Check a simple GET endpoint"""
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.REQUEST_TIMEOUT) as resp:
                    latency = (time.time() - start) * 1000
                    ok = resp.status == 200
                    body_preview = ""
                    if ok:
                        try:
                            body = await resp.json()
                            if name == "Agent Card":
                                body_preview = {
                                    "name": body.get("name"),
                                    "version": body.get("version"),
                                    "skill_count": len(body.get("skills", []))
                                }
                        except Exception:
                            pass
                    return {
                        "ok": ok,
                        "status": resp.status,
                        "latency_ms": round(latency, 2),
                        "name": name,
                        "body_preview": body_preview
                    }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e), "name": name}

    async def _check_jsonrpc(self, url: str, name: str, test: bool = False) -> Dict:
        """Check a JSON-RPC endpoint (POST)"""
        if not test:
            return {"ok": True, "skipped": True, "name": name}
        try:
            start = time.time()
            # Try to get a non-existent task to verify endpoint works
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/get",
                "params": {"id": "nonexistent-test"}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.REQUEST_TIMEOUT) as resp:
                    latency = (time.time() - start) * 1000
                    # 404 is OK (task not found, but endpoint works)
                    ok = resp.status in [200, 404]
                    return {
                        "ok": ok,
                        "status": resp.status,
                        "latency_ms": round(latency, 2),
                        "name": name
                    }
        except Exception as e:
            return {"ok": False, "error": str(e), "name": name}

    def set_public_url(self, url: str):
        """Update the public URL when tunnel changes"""
        self.public_url = url
        logger.info(f"A2A public URL updated: {url}")

    def get_status(self) -> Dict:
        return self.last_status


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="A2A Bridge Health Monitor")
    parser.add_argument("--start", action="store_true", help="Start monitor")
    parser.add_argument("--check", action="store_true", help="Run one check and exit")
    parser.add_argument("--public-url", help="Set public URL")
    args = parser.parse_args()

    monitor = A2ABridgeHealthMonitor()

    if args.public_url:
        monitor.set_public_url(args.public_url)

    if args.check:
        await monitor._run_checks()
        print(json.dumps(monitor.get_status(), indent=2))
    elif args.start:
        await monitor.start()
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            await monitor.stop()
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
