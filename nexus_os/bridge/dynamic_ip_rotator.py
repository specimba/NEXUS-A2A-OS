"""Dynamic IP Rotator — UPnP-based WAN IP reset for provider block evasion.

Plan 18 trick: Uses UPnP WANIPConnection ForceTermination to cycle the
modem/router's WAN interface and acquire a fresh public IP, bypassing
provider rate limits or IP-based signup blocks.

Usage:
    python -m nexus_os.bridge.dynamic_ip_rotator --check     # detect UPnP + show current IP
    python -m nexus_os.bridge.dynamic_ip_rotator --rotate    # force WAN disconnect/reconnect
    python -m nexus_os.bridge.dynamic_ip_rotator --monitor   # watch IP for N minutes

Supports:
  - UPnP WANIPConnection (ForceTermination) — universal router standard
  - Web API fallbacks for known router models (TP-Link, ASUS, Netgear)
  - No external dependencies — pure Python stdlib
"""
from __future__ import annotations

import json
import logging
import socket
import sys
import time
import urllib.request
from http.client import HTTPConnection
from typing import Any

logger = logging.getLogger(__name__)

UPNP_MSEARCH_ADDR = "239.255.255.250"
UPNP_MSEARCH_PORT = 1900
UPNP_MSEARCH_MSG = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: urn:schemas-upnp-org:service:WANIPConnection:1\r\n"
    "\r\n"
)

ROUTER_WEB_API: dict[str, dict[str, Any]] = {
    "tp-link": {
        "reboot_url": "http://192.168.1.1/cgi-bin/luci/;stok=/admin/system/reboot",
        "method": "POST",
    },
    "asus": {
        "reboot_url": "http://192.168.1.1/reboot.cgi",
        "method": "POST",
    },
    "netgear": {
        "reboot_url": "http://192.168.1.1/setup.cgi?todo=reboot",
        "method": "GET",
    },
}


def _get_current_ip() -> str | None:
    """Get current public IP from multiple fallback services."""
    services = [
        "https://api.ipify.org?format=json",
        "https://api.my-ip.io/ip.json",
        "https://httpbin.org/ip",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, timeout=5)
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode("utf-8"))
                for key in ("ip", "origin"):
                    if key in data:
                        ip = data[key]
                        if isinstance(ip, str) and ":" not in ip:
                            return ip.split(",")[0].strip()
                        if isinstance(ip, str) and ":" in ip:
                            return ip.split(",")[0].strip()
        except Exception:
            continue
    return None


def discover_upnp_gateway() -> str | None:
    """Discover UPnP-capable gateway via SSDP M-SEARCH."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(3)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    try:
        sock.sendto(UPNP_MSEARCH_MSG.encode(), (UPNP_MSEARCH_ADDR, UPNP_MSEARCH_PORT))
        start = time.time()
        while time.time() - start < 3:
            try:
                data, addr = sock.recvfrom(1024)
                response = data.decode("utf-8", errors="replace")
                if "WANIPConnection" in response or "InternetGatewayDevice" in response:
                    for line in response.split("\r\n"):
                        if line.lower().startswith("location:"):
                            return line.split(":", 1)[1].strip()
            except socket.timeout:
                break
    except Exception as exc:
        logger.debug("UPnP discovery failed: %s", exc)
    finally:
        sock.close()
    return None


def _upnp_soap_action(control_url: str, service_type: str, action: str) -> bool:
    """Send a UPnP SOAP action to the gateway."""
    soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:{action} xmlns:u="{service_type}">
    </u:{action}>
  </s:Body>
</s:Envelope>"""
    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPAction": f'"{service_type}#{action}"',
    }
    try:
        req = urllib.request.Request(control_url, data=soap_body.encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as exc:
        logger.debug("UPnP SOAP action %s failed: %s", action, exc)
        return False


def rotate_via_upnp() -> dict[str, Any]:
    """Force WAN disconnect/reconnect via UPnP ForceTermination."""
    location = discover_upnp_gateway()
    if not location:
        return {"ok": False, "detail": "no UPnP gateway detected"}

    ip_before = _get_current_ip()
    control_url = location.rstrip("/") + "/control?WANIPConnection"
    service_type = "urn:schemas-upnp-org:service:WANIPConnection:1"

    success = _upnp_soap_action(control_url, service_type, "ForceTermination")
    if not success:
        return {"ok": False, "detail": "ForceTermination failed", "ip_before": ip_before}

    logger.info("UPnP ForceTermination sent, waiting for new IP...")
    for _ in range(30):
        time.sleep(2)
        ip_after = _get_current_ip()
        if ip_after and ip_after != ip_before:
            return {"ok": True, "ip_before": ip_before, "ip_after": ip_after, "detail": "IP rotated via UPnP"}

    return {"ok": False, "detail": "IP did not change after ForceTermination", "ip_before": ip_before}


def rotate_via_router_web(router_model: str | None = None) -> dict[str, Any]:
    """Attempt router reboot via known Web APIs."""
    if router_model and router_model in ROUTER_WEB_API:
        cfg = ROUTER_WEB_API[router_model]
        try:
            req = urllib.request.Request(
                cfg["reboot_url"],
                method=cfg.get("method", "POST"),
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return {"ok": r.status == 200, "detail": f"{router_model} reboot attempted", "status": r.status}
        except Exception as exc:
            return {"ok": False, "detail": f"{router_model} web API failed: {exc}"}
    return {"ok": False, "detail": f"unknown router model: {router_model}"}


def rotate_ip(router_model: str | None = None) -> dict[str, Any]:
    """Rotate public IP: try UPnP first, fall back to router web API."""
    result = rotate_via_upnp()
    if result.get("ok"):
        return result
    if router_model:
        return rotate_via_router_web(router_model)
    return result


class DynamicIPRotator:
    """Class-based IP rotator with auto-rotation on provider block and rate limiting."""

    def __init__(self, auto_rotate_on_block: bool = True, max_rotations_per_hour: int = 3):
        self.auto_rotate_on_block = auto_rotate_on_block
        self.max_rotations_per_hour = max_rotations_per_hour
        self._rotation_times: list[float] = []

    def get_rotation_count(self, hours: int = 1) -> int:
        """Return number of IP rotations in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        self._rotation_times = [t for t in self._rotation_times if t > cutoff]
        return len(self._rotation_times)

    def try_rotate_on_block(self, provider_id: str) -> dict[str, Any]:
        """Attempt IP rotation if auto_rotate_on_block is enabled and rate limit not exceeded."""
        if not self.auto_rotate_on_block:
            return {"rotated": False, "new_ip": None, "reason": "auto_rotate_on_block disabled"}
        if self.get_rotation_count(1) >= self.max_rotations_per_hour:
            return {"rotated": False, "new_ip": None, "reason": f"rate limit: {self.max_rotations_per_hour}/hour exceeded"}
        result = rotate_ip()
        self._rotation_times.append(time.time())
        ip_after = result.get("ip_after") or _get_current_ip()
        return {
            "rotated": result.get("ok", False),
            "new_ip": ip_after,
            "reason": result.get("detail", "unknown"),
        }


def cli_main():
    import argparse
    ap = argparse.ArgumentParser(description="NEXUS Dynamic IP Rotator (Plan 18)")
    ap.add_argument("--check", action="store_true", help="Detect UPnP gateway + show current IP")
    ap.add_argument("--rotate", action="store_true", help="Force WAN IP rotation")
    ap.add_argument("--monitor", type=int, default=0, help="Monitor IP for N minutes and report changes")
    ap.add_argument("--router", default=None, help="Router model for web API fallback (tp-link, asus, netgear)")
    args = ap.parse_args()

    if args.check:
        ip = _get_current_ip()
        print(f"Current public IP: {ip or 'unknown'}")
        gw = discover_upnp_gateway()
        print(f"UPnP gateway: {gw or 'not found'}")
        return

    if args.rotate:
        result = rotate_ip(router_model=args.router)
        print(json.dumps(result, indent=2))
        return

    if args.monitor:
        ip_start = _get_current_ip()
        print(f"Monitoring IP (start: {ip_start}) for {args.monitor} minutes...")
        for _ in range(args.monitor * 30):
            time.sleep(2)
            ip_now = _get_current_ip()
            if ip_now and ip_now != ip_start:
                print(f"IP CHANGED: {ip_start} -> {ip_now}")
                return
        print(f"No IP change detected in {args.monitor} minutes")
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
