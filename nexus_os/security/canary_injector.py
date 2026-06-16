"""
nexus_os/security/canary_injector.py — Canary Token Injection System

Based on NSC Gap 4 (Knowledge Consistency Predicate κ) and the
UNIFIED GAP ANALYSIS document's Contradiction Detection framework.

Embeds unique, trackable tokens throughout the NEXUS codebase.
If these tokens ever appear in:
  - LLM outputs
  - Cloud model responses
  - Third-party services
  - Public code repositories
...it proves the data was retained and processed without authorization.

Usage:
    from nexus_os.security.canary_injector import CanaryInjector
    injector = CanaryInjector()
    injector.inject_canaries("C:/Users/speci.000/Documents/NEXUS")

Tokens are:
  - Cryptographically unique (SHA-256 based)
  - Hidden in comments, docstrings, variable names, or string literals
  - Designed to be low-noise (won't break code)
  - Trackable via a registry file
"""

import hashlib
import json
import os
import random
import string
import time
from pathlib import Path
from typing import Dict, List, Optional

# ── Token Templates ──────────────────────────────────────────────────────────

_TOKEN_TEMPLATES = [
    # Hidden in comments
    "# CANARY: {token}",
    "// CANARY: {token}",
    "/* CANARY: {token} */",
    "<!-- CANARY: {token} -->",
    
    # In docstrings
    '"""\nCANARY_TOKEN: {token}\n"""',
    "'''\nCANARY_TOKEN: {token}\n'''",
    
    # In variable names (limited use)
    "_canary_{token_short} = None  # tracking token",
    
    # In string literals
    "'CANARY-{token}'",
    '"CANARY-{token}"',
]

# File-specific injection points
_FILE_PATTERNS = {
    ".py": ["# CANARY: {token}", '"""\nCANARY_TOKEN: {token}\n"""'],
    ".js": ["// CANARY: {token}", "/* CANARY: {token} */"],
    ".ts": ["// CANARY: {token}", "/* CANARY: {token} */"],
    ".md": ["<!-- CANARY: {token} -->"],
    ".json": [],  # Skip JSON (strict format)
    ".yaml": ["# CANARY: {token}"],
    ".yml": ["# CANARY: {token}"],
    ".toml": ["# CANARY: {token}"],
    ".env": ["# CANARY: {token}"],
}


class CanaryInjector:
    """Injects trackable canary tokens into source code."""

    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = registry_path or os.path.expanduser(
            "~/.nexus_canary_registry.json"
        )
        self.registry: Dict[str, Dict] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load existing canary registry."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self.registry = json.load(f)

    def _save_registry(self) -> None:
        """Save canary registry."""
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2, sort_keys=True)

    def generate_token(
        self,
        context: str = "nexus-os",
        agent_id: str = "unknown",
    ) -> str:
        """
        Generate a unique canary token.
        
        Args:
            context: What project/system this token is for.
            agent_id: Which agent/agent is embedding it.
            
        Returns:
            Unique canary token string.
        """
        nonce = os.urandom(16).hex()
        timestamp = str(int(time.time()))
        seed = f"{context}:{agent_id}:{timestamp}:{nonce}"
        token = hashlib.sha256(seed.encode()).hexdigest()[:32]
        
        # Store in registry
        self.registry[token] = {
            "context": context,
            "agent_id": agent_id,
            "created_at": timestamp,
            "seed": seed,
            "status": "active",
        }
        self._save_registry()
        
        return token

    def inject_canaries(
        self,
        source_dir: str,
        extensions: Optional[List[str]] = None,
        max_per_file: int = 1,
    ) -> Dict[str, int]:
        """
        Inject canary tokens into all matching files in a directory.
        
        Args:
            source_dir: Root directory to process.
            extensions: List of extensions to target (default: all from _FILE_PATTERNS).
            max_per_file: Maximum canaries per file.
            
        Returns:
            Dict mapping file paths to number of canaries injected.
        """
        src = Path(source_dir)
        if not src.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        target_extensions = extensions or list(_FILE_PATTERNS.keys())
        results = {}
        
        for ext in target_extensions:
            patterns = _FILE_PATTERNS.get(ext, [])
            if not patterns:
                continue
                
            for file_path in src.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                    
                # Skip certain directories
                if any(part in {".git", "node_modules", "__pycache__", ".venv", "venv"} 
                        for part in file_path.parts):
                    continue
                
                try:
                    count = self._inject_into_file(file_path, patterns, max_per_file)
                    if count > 0:
                        results[str(file_path)] = count
                except Exception as e:
                    print(f"Warning: Failed to inject into {file_path}: {e}")
        
        return results

    def _inject_into_file(
        self,
        file_path: Path,
        patterns: List[str],
        max_per_file: int,
    ) -> int:
        """Inject canaries into a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            return 0
        
        # Don't inject if already has canaries
        if "CANARY" in content:
            return 0
        
        # Generate token
        token = self.generate_token(
            context=file_path.parent.name,
            agent_id="canary_injector",
        )
        
        # Select pattern
        pattern = random.choice(patterns)
        injection = pattern.format(token=token, token_short=token[:8])
        
        # Inject at a sensible location
        lines = content.split("\n")
        
        # Find a good injection point (after imports, after header, etc.)
        inject_idx = self._find_injection_point(lines, file_path.suffix)
        
        if inject_idx is not None and inject_idx < len(lines):
            lines.insert(inject_idx, injection)
            new_content = "\n".join(lines)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # Update registry
            self.registry[token]["file"] = str(file_path)
            self.registry[token]["injected_at"] = int(time.time())
            self._save_registry()
            
            return 1
        
        return 0

    def _find_injection_point(self, lines: List[str], ext: str) -> Optional[int]:
        """Find a good line to inject the canary."""
        # Skip shebang and initial comments
        start = 0
        if lines and lines[0].startswith("#!"):
            start = 1
        
        # Skip docstring if present
        if ext == ".py":
            if lines and ('"""' in lines[0] or "'''" in lines[0]):
                # Find end of docstring
                for i in range(1, len(lines)):
                    if '"""' in lines[i] or "'''" in lines[i]:
                        start = i + 1
                        break
        
        # Skip import block
        import_end = start
        for i in range(start, min(len(lines), start + 20)):
            line = lines[i].strip()
            if line.startswith(("import ", "from ", "using ", "const ", "var ", "let ", "require(", "#include")):
                import_end = i + 1
            elif line.startswith(("//", "#", "/*", "*")) and not line.startswith("#/"):
                import_end = i + 1
            elif line == "":
                import_end = i + 1
            else:
                break
        
        return import_end if import_end < len(lines) else len(lines) - 1

    def scan_for_leaks(self, text: str) -> List[str]:
        """
        Scan text for any known canary tokens.
        
        Args:
            text: Text to scan (e.g., LLM output, web page).
            
        Returns:
            List of leaked canary tokens found.
        """
        leaks = []
        for token, info in self.registry.items():
            if token in text:
                leaks.append(token)
                # Update status
                self.registry[token]["status"] = "leaked"
                self.registry[token]["leaked_at"] = int(time.time())
        
        if leaks:
            self._save_registry()
        
        return leaks

    def get_report(self) -> Dict:
        """Generate a report of all canaries."""
        active = [t for t, i in self.registry.items() if i.get("status") == "active"]
        leaked = [t for t, i in self.registry.items() if i.get("status") == "leaked"]
        
        return {
            "total": len(self.registry),
            "active": len(active),
            "leaked": len(leaked),
            "active_tokens": active,
            "leaked_tokens": leaked,
            "registry_path": self.registry_path,
        }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Canary Token Injection System")
    parser.add_argument("command", choices=["inject", "scan", "report"])
    parser.add_argument("--dir", help="Source directory for inject")
    parser.add_argument("--text", help="Text to scan for leaks")
    parser.add_argument("--registry", help="Custom registry path")
    args = parser.parse_args()
    
    injector = CanaryInjector(registry_path=args.registry)
    
    if args.command == "inject":
        if not args.dir:
            print("--dir required for inject")
            exit(1)
        results = injector.inject_canaries(args.dir)
        print(f"Injected canaries into {len(results)} files")
        for path, count in results.items():
            print(f"  {path}: {count} token(s)")
    
    elif args.command == "scan":
        if not args.text:
            print("--text required for scan")
            exit(1)
        leaks = injector.scan_for_leaks(args.text)
        if leaks:
            print(f"ALERT: {len(leaks)} canary token(s) leaked!")
            for token in leaks:
                info = injector.registry[token]
                print(f"  Token: {token}")
                print(f"    Context: {info.get('context')}")
                print(f"    File: {info.get('file')}")
        else:
            print("No canary tokens found in text.")
    
    elif args.command == "report":
        report = injector.get_report()
        print(json.dumps(report, indent=2))