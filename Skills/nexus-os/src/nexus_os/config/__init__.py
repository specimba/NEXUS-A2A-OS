"""NEXUS OS — Config module: Governance constitution."""
CONSTITUTION = {
    "version": "3.0.0",
    "name": "Nexus OS",
    "gov": {
        "max_agents": 5,
        "max_api": 20,
        "max_concurrent": 2,
        "max_writes": 30,
    },
    "auth": {
        "kaiju": True,
        "trust": True,
    },
}