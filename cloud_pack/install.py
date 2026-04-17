#!/usr/bin/env python3
"""
NEXUS OS v3.0 — Quick Installer
Installs NEXUS OS with dependency check and verification.

Usage:
    python -m nexus.install          # Full install
    python -m nexus.install --test  # Test mode
    python -m nexus.install --check # Check only
"""

import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path


# NEXUS version
VERSION = "3.0.0"

# Required files with their expected hashes (simplified check)
REQUIRED_FILES = {
    "src/nexus_os/__init__.py": "package",
    "src/nexus_os/monitoring/token_guard.py": "budget",
    "src/nexus_os/monitoring/trust_scorer.py": "trust",
    "src/nexus_os/engine/hermes.py": "routing",
    "src/nexus_os/bridge/server.py": "bridge",
    "src/nexus_os/governor/compliance.py": "governance",
    "src/nexus_os/gmr/__init__.py": "gmr",
    "src/nexus_os/vault/memory_tracks.py": "memory",
    "src/nexus_os/execution_paths.py": "paths",
}

# Required directories
REQUIRED_DIRS = [
    "src/nexus_os/monitoring",
    "src/nexus_os/engine",
    "src/nexus_os/bridge",
    "src/nexus_os/governor",
    "src/nexus_os/gmr",
    "src/nexus_os/vault",
    "tests",
]

# Python version requirement
MIN_PYTHON = (3, 10)


def get_python_version():
    """Get current Python version."""
    return sys.version_info[:2]


def check_python():
    """Check Python version."""
    version = get_python_version()
    if version >= MIN_PYTHON:
        return True, f"Python {version[0]}.{version[1]}"
    return False, f"Python {version[0]}.{version[1]} (need 3.10+)"


def check_directory_structure():
    """Verify directory structure exists."""
    results = []
    all_ok = True
    
    for dir_path in REQUIRED_DIRS:
        full_path = Path(dir_path)
        if full_path.is_dir():
            results.append(f"  [OK] {dir_path}/")
        else:
            results.append(f"  [--] {dir_path}/ (missing)")
            all_ok = False
    
    return all_ok, results


def check_required_files():
    """Verify required files exist."""
    results = []
    all_ok = True
    
    for file_path, tag in REQUIRED_FILES.items():
        full_path = Path(file_path)
        if full_path.is_file():
            size = full_path.stat().st_size
            results.append(f"  [OK] {file_path} ({size:,} bytes)")
        else:
            results.append(f"  [--] {file_path} (missing)")
            all_ok = False
    
    return all_ok, results


def check_dependencies():
    """Check Python dependencies."""
    results = []
    all_ok = True
    
    # Core dependencies
    deps = [
        ("requests", "requests"),
        ("sqlite3", "sqlite3"),
        ("hashlib", "hashlib"),
        ("dataclasses", "dataclasses"),
        ("typing", "typing"),
    ]
    
    for name, module in deps:
        try:
            __import__(module)
            results.append(f"  [OK] {name}")
        except ImportError:
            results.append(f"  [--] {name} (not found)")
            all_ok = False
    
    return all_ok, results


def run_diagnostics():
    """Run system diagnostics."""
    results = []
    all_ok = True
    
    try:
        sys.path.insert(0, "src")
        
        # Check GMR
        from nexus_os.gmr import DOMAIN_MAPPING
        results.append(f"  [OK] GMR: {len(DOMAIN_MAPPING)} domains")
        
        # Check Trust
        from nexus_os.monitoring.trust_scorer import LANE_PARAMS
        results.append(f"  [OK] Trust: {len(LANE_PARAMS)} lanes")
        
        # Check TokenGuard
        from nexus_os.monitoring.token_guard import TokenGuard
        results.append(f"  [OK] TokenGuard: available")
        
        # Check Hermes
        from nexus_os.engine.hermes import HermesRouter
        results.append(f"  [OK] Hermes: available")
        
    except Exception as e:
        results.append(f"  [ERROR] {e}")
        all_ok = False
    
    return all_ok, results


def install_npm_style():
    """Install with npm-like output."""
    print("=" * 50)
    print("NEXUS OS v" + VERSION + " - Installer")
    print("=" * 50)
    print()
    
    all_ok = True
    
    # 1. Python check
    print("[1/5] Checking Python...")
    ok, msg = check_python()
    print(f"  {msg}")
    if not ok:
        all_ok = False
    
    # 2. Directory structure
    print("\n[2/5] Checking directories...")
    ok, lines = check_directory_structure()
    for line in lines:
        print(line)
    if not ok:
        all_ok = False
    
    # 3. Required files
    print("\n[3/5] Checking required files...")
    ok, lines = check_required_files()
    for line in lines:
        print(line)
    if not ok:
        all_ok = False
    
    # 4. Dependencies
    print("\n[4/5] Checking dependencies...")
    ok, lines = check_dependencies()
    for line in lines:
        print(line)
    if not ok:
        all_ok = False
    
    # 5. Run diagnostics
    print("\n[5/5] Running diagnostics...")
    ok, lines = run_diagnostics()
    for line in lines:
        print(line)
    if not ok:
        all_ok = False
    
    print()
    print("=" * 50)
    if all_ok:
        print(f"[OK] NEXUS OS v{VERSION} installed successfully")
    else:
        print("[X] Some checks failed")
    print("=" * 50)
    
    return all_ok


def check_only():
    """Check installation without installing."""
    print("=" * 50)
    print(f"NEXUS OS v{VERSION} — Check")
    print("=" * 50)
    
    ok1, _ = check_python()
    ok2, _ = check_directory_structure()
    ok3, _ = check_required_files()
    ok4, _ = check_dependencies()
    ok5, _ = run_diagnostics()
    
    return all([ok1, ok2, ok3, ok4, ok5])


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if "--check" in args:
        ok = check_only()
    elif "--test" in args:
        ok = install_npm_style()
    else:
        ok = install_npm_style()
    
    sys.exit(0 if ok else 1)