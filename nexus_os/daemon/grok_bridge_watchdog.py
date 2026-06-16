"""
NEXUS Grok MCP Bridge Watchdog
Ensures the Grok MCP server stays alive and tunnels remain connected.
Auto-restarts on failure and updates A2A_PUBLIC_URL on tunnel changes.
"""
import asyncio
import logging
import subprocess
import time
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp

logger = logging.getLogger("nexus.grok_watchdog")

class TunnelInfo:
    def __init__(self, url: str, type: str, process=None):
        self.url = url
        self.type = type
        self.process = process
        self.started_at = datetime.now()
        self.last_check = None
        self.is_alive = True

class GrokBridgeWatchdog:
    """
    Watches grok_mcp_server.py and tunnel processes
    Auto-restarts on failure, monitors tunnel health
    """

    GROK_SERVER = r"D:\GROSS\grok_mcp_server.py"
    GROK_PORT = 7354
    TUNNEL_CHECK_INTERVAL = 30
    SERVER_RESTART_DELAY = 5
    MAX_RESTART_ATTEMPTS = 5

    def __init__(self):
        self.running = False
        self.server_process: Optional[subprocess.Popen] = None
        self.tunnel: Optional[TunnelInfo] = None
        self.restart_count = 0
        self.last_restart = None
        self.public_url = None

        self.tunnel_priority = [
            ("cloudflared", self._start_cloudflared),
            ("ngrok", self._start_ngrok),
            ("pinggy", self._start_pinggy),
        ]

    async def start(self):
        """Start watchdog loop"""
        if self.running:
            logger.warning("Watchdog already running")
            return
        self.running = True
        logger.info("Starting Grok MCP Bridge Watchdog")

        try:
            await self._start_server()
            await self._establish_tunnel()
            await self._monitor_loop()
        except Exception as e:
            logger.error(f"Watchdog fatal error: {e}")
            await self.stop()

    async def stop(self):
        """Stop watchdog and all processes"""
        self.running = False
        await self._stop_tunnel()
        await self._stop_server()
        logger.info("Watchdog stopped")

    async def _start_server(self):
        """Start the Grok MCP server"""
        logger.info(f"Starting Grok MCP server: {self.GROK_SERVER}")

        env = os.environ.copy()
        env["A2A_PUBLIC_URL"] = self.public_url or f"http://localhost:{self.GROK_PORT}"

        self.server_process = subprocess.Popen(
            ["python", self.GROK_SERVER],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        await asyncio.sleep(3)
        if self.server_process.poll() is None:
            logger.info(f"Grok server started (PID {self.server_process.pid})")
            self.restart_count = 0
        else:
            raise RuntimeError(f"Server failed to start (exit code: {self.server_process.returncode})")

    async def _stop_server(self):
        """Stop the Grok MCP server"""
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            logger.info("Grok server stopped")

    async def _establish_tunnel(self):
        """Try tunnel chain: cloudflared -> ngrok -> pinggy"""
        for tunnel_type, start_func in self.tunnel_priority:
            try:
                logger.info(f"Trying {tunnel_type} tunnel...")
                tunnel_info = await start_func()
                if tunnel_info:
                    self.tunnel = tunnel_info
                    self.public_url = tunnel_info.url
                    logger.info(f"Tunnel established: {tunnel_type} -> {tunnel_info.url}")
                    await self._restart_server_with_public_url()
                    return
            except Exception as e:
                logger.warning(f"{tunnel_type} failed: {e}")
                continue

        logger.warning("No tunnel established - server only available locally")
        self.public_url = f"http://localhost:{self.GROK_PORT}"

    async def _restart_server_with_public_url(self):
        """Restart server with updated A2A_PUBLIC_URL"""
        logger.info(f"Restarting server with A2A_PUBLIC_URL={self.public_url}")
        await self._stop_server()
        await asyncio.sleep(2)
        await self._start_server()

    async def _start_cloudflared(self) -> Optional[TunnelInfo]:
        """Start cloudflared quick tunnel"""
        try:
            # Find cloudflared executable
            cloudflared = self._find_executable([
                r"C:\Program Files\Cloudflare\cloudflared.exe",
                os.path.expanduser(r"~\cloudflared\cloudflared.exe"),
                "cloudflared"
            ])

            if not cloudflared:
                return None

            proc = subprocess.Popen(
                [cloudflared, "tunnel", "--url", f"http://localhost:{self.GROK_PORT}", "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # Wait for tunnel URL to appear in stderr
            for _ in range(20):
                await asyncio.sleep(0.5)
                line = proc.stderr.readline()
                if line:
                    text = line.decode('utf-8', errors='ignore')
                    match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
                    if match:
                        url = match.group(0)
                        return TunnelInfo(url, "cloudflared", proc)

            proc.terminate()
            return None
        except Exception as e:
            logger.debug(f"Cloudflared error: {e}")
            return None

    async def _start_ngrok(self) -> Optional[TunnelInfo]:
        """Start ngrok tunnel"""
        try:
            ngrok = self._find_executable([
                os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\ngrok.exe"),
                "ngrok"
            ])

            if not ngrok:
                return None

            proc = subprocess.Popen(
                [ngrok, "http", str(self.GROK_PORT), "--log=stdout"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            await asyncio.sleep(5)

            # Check ngrok API
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:4040/api/tunnels", timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("tunnels"):
                            url = data["tunnels"][0]["public_url"]
                            return TunnelInfo(url, "ngrok", proc)

            proc.terminate()
            return None
        except Exception as e:
            logger.debug(f"Ngrok error: {e}")
            return None

    async def _start_pinggy(self) -> Optional[TunnelInfo]:
        """Start pinggy tunnel via SSH"""
        try:
            ssh = self._find_executable(["ssh"])
            if not ssh:
                return None

            proc = subprocess.Popen(
                [ssh, "-p", "443", "-R", f"0:localhost:{self.GROK_PORT}",
                 "-o", "StrictHostKeyChecking=no",
                 "-o", "ServerAliveInterval=30",
                 "a.pinggy.io"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            for _ in range(10):
                await asyncio.sleep(0.5)
                line = proc.stdout.readline()
                if line:
                    text = line.decode('utf-8', errors='ignore')
                    match = re.search(r'https?://[a-z0-9-]+\.pinggy\.link', text)
                    if match:
                        url = match.group(0)
                        return TunnelInfo(url, "pinggy", proc)

            proc.terminate()
            return None
        except Exception as e:
            logger.debug(f"Pinggy error: {e}")
            return None

    def _find_executable(self, candidates: List[str]) -> Optional[str]:
        """Find first existing executable from candidates"""
        for path in candidates:
            if os.path.isabs(path):
                if os.path.exists(path):
                    return path
            else:
                # Check PATH
                try:
                    result = subprocess.run(["where", path], capture_output=True, text=True)
                    if result.returncode == 0:
                        return result.stdout.strip().split('\n')[0]
                except Exception:
                    pass
        return None

    async def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Entering monitor loop")
        while self.running:
            try:
                await self._check_server()
                await self._check_tunnel()
                await asyncio.sleep(self.TUNNEL_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)

    async def _check_server(self):
        """Check if Grok server is alive"""
        if not self.server_process or self.server_process.poll() is not None:
            logger.warning("Grok server is down, attempting restart...")

            if self.restart_count >= self.MAX_RESTART_ATTEMPTS:
                logger.error(f"Max restart attempts ({self.MAX_RESTART_ATTEMPTS}) reached")
                await self.stop()
                return

            self.restart_count += 1
            self.last_restart = datetime.now()

            try:
                await self._start_server()
                logger.info(f"Server restarted successfully (attempt {self.restart_count})")
            except Exception as e:
                logger.error(f"Server restart failed: {e}")
                await asyncio.sleep(self.SERVER_RESTART_DELAY)
        else:
            # Server alive - verify HTTP health
            if self.public_url:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.public_url}/health", timeout=5) as resp:
                            if resp.status != 200:
                                logger.warning(f"Health check returned {resp.status}")
                except Exception as e:
                    logger.debug(f"Health check failed: {e}")

    async def _check_tunnel(self):
        """Check if tunnel is alive"""
        if not self.tunnel:
            return

        if self.tunnel.process and self.tunnel.process.poll() is not None:
            logger.warning(f"{self.tunnel.type} tunnel died, attempting reconnection...")
            self.tunnel = None
            await self._establish_tunnel()

    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "running": self.running,
            "server": {
                "alive": self.server_process.poll() is None if self.server_process else False,
                "pid": self.server_process.pid if self.server_process else None,
                "restart_count": self.restart_count,
                "last_restart": self.last_restart.isoformat() if self.last_restart else None
            },
            "tunnel": {
                "type": self.tunnel.type if self.tunnel else None,
                "url": self.tunnel.url if self.tunnel else None,
                "alive": self.tunnel.is_alive if self.tunnel else False,
                "started_at": self.tunnel.started_at.isoformat() if self.tunnel else None
            },
            "public_url": self.public_url,
            "a2a_card": f"{self.public_url}/.well-known/agent.json" if self.public_url else None
        }


async def main():
    """CLI entry point for watchdog"""
    import argparse
    parser = argparse.ArgumentParser(description="Grok MCP Bridge Watchdog")
    parser.add_argument("--start", action="store_true", help="Start watchdog")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--stop", action="store_true", help="Stop watchdog")
    args = parser.parse_args()

    watchdog = GrokBridgeWatchdog()

    if args.start:
        await watchdog.start()
    elif args.status:
        print(json.dumps(watchdog.get_status(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
