"""
NEXUS Tailscale Network Monitor
Monitors Tailscale mesh status, peer connectivity, and Zo Computer reachability.
Reports to UnifiedStateManager.
"""
import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.tailscale")


class TailscaleMonitor:
    """Monitor Tailscale mesh network status"""

    CHECK_INTERVAL = 60
    ZO_HOSTS = ["zo-compute-1", "zo-compute-2", "openclaw-gateway"]

    def __init__(self, state_manager=None):
        self.sm = state_manager
        self.running = False
        self.last_status = {}
        self._tailscale_path = self._find_tailscale()

    def _find_tailscale(self) -> Optional[str]:
        """Locate tailscale executable"""
        candidates = [
            r"C:\Program Files\Tailscale\tailscale.exe",
            r"C:\Program Files (x86)\Tailscale\tailscale.exe",
            os.path.expanduser(r"~\AppData\Local\Tailscale\tailscale.exe"),
        ]
        for path in candidates:
            if Path(path).exists():
                return path
        # Check PATH
        try:
            result = subprocess.run(["where", "tailscale"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        return None

    async def start(self):
        if self.running:
            return
        self.running = True
        logger.info(f"TailscaleMonitor started (binary: {self._tailscale_path})")
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self.running = False

    async def _monitor_loop(self):
        while self.running:
            try:
                await self._run_checks()
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _run_checks(self):
        """Run Tailscale status checks"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "installed": self._tailscale_path is not None,
            "binary_path": self._tailscale_path,
        }

        if self._tailscale_path:
            status.update(await self._get_tailscale_status())
        else:
            status["connected"] = False
            status["error"] = "tailscale binary not found"

        # Check Zo Computer reachability
        status["zo"] = await self._check_zo_reachability()

        # Publish to state manager
        if self.sm:
            await self.sm.publish(
                "integrations.tailscale",
                {
                    "connected": status.get("connected", False),
                    "peers": status.get("peer_count", 0),
                    "self_ip": status.get("self_ip"),
                    "details": status
                },
                source="tailscale_monitor"
            )

            # Zo status
            zo_status = status.get("zo", {})
            await self.sm.publish(
                "integrations.zo_computer",
                {
                    "reachable": zo_status.get("any_reachable", False),
                    "details": zo_status
                },
                source="tailscale_monitor"
            )

        self.last_status = status

    async def _get_tailscale_status(self) -> Dict:
        """Run tailscale status command"""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._tailscale_path, "status", "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                data = json.loads(stdout.decode('utf-8', errors='replace'))
                return {
                    "connected": True,
                    "self_ip": data.get("Self", {}).get("TailscaleIPs", ["N/A"])[0],
                    "peer_count": len(data.get("Peer", {})),
                    "backend_state": data.get("BackendState", "unknown"),
                    "peers_online": sum(
                        1 for p in data.get("Peer", {}).values()
                        if p.get("Online", False)
                    )
                }
            else:
                return {
                    "connected": False,
                    "error": stderr.decode('utf-8', errors='replace')[:200]
                }
        except asyncio.TimeoutError:
            return {"connected": False, "error": "tailscale status timeout"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def _check_zo_reachability(self) -> Dict:
        """Check Zo Computer host reachability"""
        result = {"any_reachable": False, "hosts": {}}

        for host in self.ZO_HOSTS:
            try:
                # Use ping to check basic reachability
                proc = await asyncio.create_subprocess_exec(
                    "ping", "-n", "1", "-w", "2000", host,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                reachable = proc.returncode == 0
                result["hosts"][host] = {
                    "reachable": reachable
                }
                if reachable:
                    result["any_reachable"] = True
            except Exception as e:
                result["hosts"][host] = {
                    "reachable": False,
                    "error": str(e)
                }

        return result

    def get_status(self) -> Dict:
        return self.last_status


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tailscale Network Monitor")
    parser.add_argument("--start", action="store_true", help="Start monitor")
    parser.add_argument("--check", action="store_true", help="One-shot check")
    args = parser.parse_args()

    monitor = TailscaleMonitor()
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
