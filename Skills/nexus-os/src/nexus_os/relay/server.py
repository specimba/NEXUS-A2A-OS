#!/usr/bin/env python3
"""Relay server entry point — starts NEXUS OS relay on port 7352."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if __name__ == "__main__":
    print("NexusRelay: use update_space_route() or register_user_service() to host.")
    print("Import dashboard_stats, GovernorRelay, VAPProofChain from nexus_os.relay")
