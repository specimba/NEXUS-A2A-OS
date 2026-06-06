"""
NEXUS OS Governance API Server
==============================
Runs the canonical FastAPI governance server on port 7352.

Usage:
    python run_governance_api.py
    python run_governance_api.py --port 7352 --host 0.0.0.0
"""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="NEXUS OS Governance API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7352, help="Port to bind (default: 7352)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")
    args = parser.parse_args()

    # Import here so any import errors surface before uvicorn starts
    from nexus_os.bridge.server import create_app
    app = create_app()

    print(f"[=NEXUS=] Governance API starting on http://{args.host}:{args.port}")
    print(f"[=NEXUS=] Endpoints: /health, /tasks/submit, /tasks/status, /tasks/heartbeat, /tasks/result")
    print(f"[=NEXUS=]            /skills/propose, /skills/status/{{id}}")
    print(f"[=NEXUS=]            /dashboard/stats, /governance/proposals, /governance/approve")
    print(f"[=NEXUS=]            /vault/read, /vault/write, / (JSON-RPC router)")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        access_log=True,
    )


if __name__ == "__main__":
    main()
