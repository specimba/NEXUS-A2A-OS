"""Run the loopback-only NEXUS SAGE HTTPS-tunnel edge.

This script starts only the local edge.  It never starts or configures a
Cloudflare, ngrok, Tailscale, or other public tunnel.
"""

from __future__ import annotations

import uvicorn

from nexus_os.sage_gateway.edge import configured_edge_host, configured_edge_port


def main() -> None:
    uvicorn.run(
        "nexus_os.sage_gateway.edge:app",
        host=configured_edge_host(),
        port=configured_edge_port(),
        access_log=False,
        proxy_headers=False,
        server_header=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
