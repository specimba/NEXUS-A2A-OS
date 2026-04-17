#!/usr/bin/env python3
"""GMR Heartbeat Bootstrapper & Stub Fixer"""
import os

print("Initiating GMR Heartbeat sequence...")

# 1. Fix hermes.py (Inject missing SkillRecord for TeamCoordinator)
hermes_path = os.path.join("src", "nexus_os", "engine", "hermes.py")
if os.path.exists(hermes_path):
    with open(hermes_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    if "class SkillRecord" not in code:
        stub = "\n@dataclass\nclass SkillRecord:\n    name: str\n    description: str = ''\n    risk_level: str = 'low'\n"
        with open(hermes_path, "a", encoding="utf-8") as f:
            f.write(stub)
        print("[✅] Injected SkillRecord into hermes.py")

# 2. Inject Telemetry Heartbeat into BridgeServer
bridge_path = os.path.join("src", "nexus_os", "bridge", "server.py")
if os.path.exists(bridge_path):
    with open(bridge_path, "r", encoding="utf-8") as f:
        bridge_code = f.read()

    if "RefreshScheduler" not in bridge_code:
        imports = "from nexus_os.gmr.scheduler import RefreshScheduler\nfrom nexus_os.gmr.telemetry import TelemetryIngest\n"
        bridge_code = bridge_code.replace("import logging", "import logging\n" + imports)
        
        # Inject into __init__
        boot_logic = """        # ── Start GMR Telemetry Heartbeat ──
        self.telemetry = TelemetryIngest()
        self.gmr_scheduler = RefreshScheduler(self.telemetry, interval_seconds=300)
        self.gmr_scheduler.start()
        logger.info("NEXUS OS Boot: GMR Telemetry Heartbeat Started")\n"""
        
        # We find the end of __init__ and append it
        target_hook = "self.compliance = ComplianceEngine(token_guard=self.guard)"
        if target_hook in bridge_code:
            bridge_code = bridge_code.replace(target_hook, target_hook + "\n" + boot_logic)
            with open(bridge_path, "w", encoding="utf-8") as f:
                f.write(bridge_code)
            print("[✅] Wired GMR Telemetry Heartbeat into BridgeServer boot sequence.")
        else:
            print("[⚠️] Could not find boot hook in BridgeServer.")

print("\n[🚀] Heartbeat configured. Re-running team_check.py.")