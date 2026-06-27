#!/usr/bin/env python3
"""
NEXUS Archivist Engine v1.0
Karpathy LLM Wiki Architecture implementation for NEXUS OS

Usage:
    python archivist.py ingest [--force]    — Scan all sources, update wiki
    python archivist.py lint [--fix]       — Health check wiki, report issues
    python archivist.py query <question>   — Search wiki and synthesize answer
    python archivist.py boot               — Regenerate boot.md for agents
    python archivist.py status             — Show current wiki status

Dependencies: None (stdlib only)
"""

import logging
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("nexus_os.archivist")

# Fast cryptographic hashing — blake3 is 10x faster than SHA-256
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False
    import hashlib

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(r'C:\Users\speci.000\Documents\NEXUS\nexus_os\archivist')
WIKI_DIR = BASE_DIR / 'wiki'
RAW_DIRS = {
    'archivist': Path(r'C:\Users\speci.000\Downloads\ARCHIVIST'),
    'papers': Path(r'C:\Users\speci.000\Downloads\PAPERS'),
    'nexuslogs': Path(r'C:\Users\speci.000\Downloads\NEXUSlogs'),
    'nexus': Path(r'C:\Users\speci.000\Documents\NEXUS'),
    'gross': Path(r'D:\GROSS'),
}

EXCLUDE_PATTERNS = ['__pycache__', '.git', 'node_modules', 'archive', '.nexus_pi', 'zilliz-cloud-*-username-password.txt']

# =============================================================================
# Utilities
# =============================================================================

def now_iso() -> str:
    return datetime.now().isoformat()

def file_hash(path: Path) -> Optional[str]:
    """Fast fingerprint using size + mtime (not full hash for speed).
    
    For cryptographic integrity checks, use file_hash_blake3() instead.
    
    Returns None on error (e.g. file not found or stat failure).
    """
    try:
        stat = path.stat()
        return f"{stat.st_size}-{stat.st_mtime}"
    except Exception:
        return None

def file_hash_blake3(path: Path, max_size_mb: int = 100) -> Optional[str]:
    """Cryptographic hash using blake3 (10x faster than SHA-256).
    
    Skips files larger than max_size_mb for performance.
    Returns '' for oversized files.
    Returns None on error.
    """
    try:
        size = path.stat().st_size
        if size > max_size_mb * 1024 * 1024:
            return ''  # Skip large files
        
        if HAS_BLAKE3:
            hasher = blake3.blake3()
        else:
            hasher = hashlib.sha256()
        
        with open(path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB chunks
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception:
        return None

def should_exclude(path: Path) -> bool:
    for pat in EXCLUDE_PATTERNS:
        pat_lower = pat.lower()
        if any(part.lower() == pat_lower for part in Path(path).parts):
            return True
    return False

def scan_directory(dir_path: Path, max_depth: int = 3, max_size_mb: int = 100) -> list:
    """Recursively scan directory, return list of file metadata."""
    files = []
    if not os.path.isdir(str(dir_path)):
        return files
    count = 0
    try:
        for root, dirs, filenames in os.walk(dir_path):
            depth = root.count(os.sep) - str(dir_path).count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            for fname in filenames:
                if should_exclude(Path(fname)):
                    continue
                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    if size_mb > max_size_mb:
                        continue  # Skip very large files
                    files.append({
                        'path': str(fpath.relative_to(dir_path)),
                        'full_path': str(fpath),
                        'size': stat.st_size,
                        'mtime': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'hash': file_hash(fpath),
                    })
                    count += 1
                    if count % 500 == 0:
                        logger.debug("Scanned %d files", count)
                except (PermissionError, OSError) as e:
                    logger.debug("Failed to stat %s: %s", fpath, e)
    except Exception as e:
        logger.warning("Error scanning %s: %s", dir_path, e)
    return files

# Bridge mapping for callers that consume categorize_file() output.
# Maps archivist's string category labels to import_stage's FileType enum.
# This is THE single source of truth for extension-to-type classification.
# When adding a new FileType, add a mapping here AND update categorize_file() below.
CATEGORIZE_TO_FILETYPE = {
    "paper": "PAPER",
    "log": "LOG",
    "code": "CODE",
    "config": "CONFIG",
    "documentation": "MARKDOWN",
    "plan": "MARKDOWN",
    "report": "LOG",
    "text": "LOG",
    "image": "IMAGE",
    "notebook": "NOTEBOOK",
    "data": "DATA",
    "archive": "UNKNOWN",
    "other": "UNKNOWN",
}

def categorize_file(path: str) -> str:
    """Categorize file by extension and name.

    Returns string category labels that CATEGORIZE_TO_FILETYPE maps to FileType enum
    values. Both this function and the mapping must stay in sync — add new extension
    patterns here and their mapping above.
    """
    p = path.lower()
    if p.endswith('.pdf'):
        return 'paper'
    elif p.endswith('.md'):
        if 'plan' in p or 'implementation' in p:
            return 'plan'
        elif 'report' in p or 'log' in p:
            return 'report'
        elif 'readme' in p:
            return 'documentation'
        else:
            return 'documentation'
    elif p.endswith('.log'):
        return 'log'
    elif p.endswith('.txt'):
        if 'log' in p:
            return 'log'
        else:
            return 'text'
    elif p.endswith('.py') or p.endswith('.js') or p.endswith('.ts'):
        return 'code'
    elif p.endswith('.rs') or p.endswith('.go') or p.endswith('.java'):
        return 'code'
    elif p.endswith('.c') or p.endswith('.cpp') or p.endswith('.h'):
        return 'code'
    elif p.endswith('.json') or p.endswith('.yaml') or p.endswith('.yml'):
        return 'config'
    elif p.endswith('.toml') or p.endswith('.ini') or p.endswith('.cfg'):
        return 'config'
    elif p.endswith('.png') or p.endswith('.jpg') or p.endswith('.jpeg'):
        return 'image'
    elif p.endswith('.gif') or p.endswith('.bmp') or p.endswith('.webp') or p.endswith('.svg'):
        return 'image'
    elif p.endswith('.ipynb'):
        return 'notebook'
    elif p.endswith('.csv') or p.endswith('.parquet') or p.endswith('.jsonl'):
        return 'data'
    elif p.endswith('.zip') or p.endswith('.tar.gz'):
        return 'archive'
    else:
        return 'other'

# =============================================================================
# Wiki Page Generators
# =============================================================================

def generate_index(wiki_state: dict) -> str:
    """Generate the master index.md page."""
    lines = [
        "# NEXUS Archivist — Index",
        f"",
        f"**Generated:** {now_iso()}",
        f"**Total Wiki Pages:** {wiki_state.get('page_count', 0)}",
        f"**Total Sources Indexed:** {wiki_state.get('source_count', 0)}",
        f"**Last Ingest:** {wiki_state.get('last_ingest', 'never')}",
        f"",
        "---",
        f"",
        "## Quick Navigation",
        f"",
        "| Category | Pages | Description |",
        "|----------|-------|-------------|",
        "| [[Entities]] | 4 | Models, providers, agents, projects |",
        "| [[Concepts]] | 4 | Benchmarking, security, architecture, governance |",
        "| [[Sources]] | 4 | ARCHIVIST, PAPERS, NEXUSlogs, GROSS |",
        "| [[Logs]] | 1 | Operation history |",
        "",
        "---",
        f"",
        "## Entity Pages",
        f"",
    ]
    
    for page in sorted(wiki_state.get('entities', []), key=lambda x: x['name']):
        lines.append(f"- [[{page['name']}]] — {page.get('summary', 'No summary')}")
    
    lines.extend([
        f"",
        "## Concept Pages",
        f"",
    ])
    
    for page in sorted(wiki_state.get('concepts', []), key=lambda x: x['name']):
        lines.append(f"- [[{page['name']}]] — {page.get('summary', 'No summary')}")
    
    lines.extend([
        f"",
        "## Source Pages",
        f"",
    ])
    
    for page in sorted(wiki_state.get('sources', []), key=lambda x: x['name']):
        lines.append(f"- [[{page['name']}]] — {page.get('summary', 'No summary')}")
    
    lines.extend([
        f"",
        "## Recent Log Entries",
        f"",
    ])
    
    for entry in wiki_state.get('recent_logs', [])[:10]:
        lines.append(f"- `{entry['time']}` — {entry['action']}: {entry['summary']}")
    
    lines.extend([
        f"",
        "---",
        f"",
        "*This index is auto-generated by `archivist.py ingest`. Do not edit manually.*",
    ])
    
    return '\n'.join(lines)

def generate_log_entry(action: str, summary: str, details: dict = None) -> str:
    """Generate a single log entry in markdown format."""
    entry = f"## [{now_iso()}] {action} | {summary}\n\n"
    if details:
        entry += f"```json\n{json.dumps(details, indent=2, default=str)}\n```\n\n"
    return entry

def generate_boot(wiki_state: dict) -> str:
    """Generate boot.md — 60-second fast sync for any agent."""
    lines = [
        "# NEXUS OS — Fast Boot Sync",
        f"**Generated:** {now_iso()}",
        f"**Version:** 2026-06-09",
        f"",
        "> **For any agent:** Read this file in 60 seconds to understand the entire system state.",
        f"",
        "---",
        f"",
        "## 1. Active Services (Ports)",
        f"",
        "| Port | Service | Status | Best For |",
        "|------|---------|--------|----------|",
        "| 7352 | ModelRelay (Node.js) | ONLINE | Model health, discovery |",
        "| 7354 | GROSS MCP Bridge | ONLINE | Grok audit (confidential) |",
        "| 7356 | Dashboard (HTML) | ONLINE | Quality × Health Matrix |",
        "| 7357 | God Mode Proxy v3 | ONLINE | Smart model routing |",
        "| 11435 | Ollama | ONLINE | Local GPU inference |",
        f"",
        "---",
        f"",
        "## 2. Top Working Models (by Intelligence)",
        f"",
    ]
    
    for model in wiki_state.get('top_models', [])[:5]:
        lines.append(f"| {model['name']} | {model['intell']} | {model['provider']} | {model['status']} |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## 3. Provider Status",
        f"",
        "| Provider | UP | DOWN | Key Issue |",
        "|----------|----|------|-----------|",
    ])
    
    for prov in wiki_state.get('providers', []):
        lines.append(f"| {prov['name']} | {prov['up']} | {prov['down']} | {prov.get('issue', 'None')} |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## 4. Recent Changes (Last 24h)",
        f"",
    ])
    
    for change in wiki_state.get('recent_changes', [])[:5]:
        lines.append(f"- {change}")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## 5. Open Issues",
        f"",
    ])
    
    for issue in wiki_state.get('open_issues', [])[:5]:
        lines.append(f"- {issue}")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## 6. Critical Rules",
        f"",
        "1. **GROSS is confidential** — Read-only, no modifications without SPECI approval",
        "2. **Git discipline** — Never `git add .`, stage explicit paths only",
        "3. **ModelRelay path** — Run from `AppData\\Roaming\\npm\\node_modules\\modelrelay\\bin\\modelrelay.js` (NOT npx)",
        "4. **Scores in scores.js** — Must restart ModelRelay to reload after edits",
        "5. **Dashboard API** — Uses `/api/models` and `/api/config` (not `/api/providers` or `/api/status`)",
        f"",
        "---",
        f"",
        "## 7. Quick Commands",
        f"",
        "```bash",
        "# Check system status",
        "curl -s http://localhost:7352/api/models | python -c \"import sys,json; d=json.load(sys.stdin); print(f'Total: {len(d[chr(39)+chr(39)]models[chr(39)+chr(39)])}, UP: {len([m for m in d[chr(39)+chr(39)]models[chr(39)+chr(39)] if m[chr(39)+chr(39)]status[chr(39)+chr(39)]==chr(39)+chr(39)]up[chr(39)+chr(39)]])}')\"",
        "",
        "# Test God Mode routing",
        "curl -X POST http://localhost:7357/v1/chat/completions -H 'Authorization: Bearer god-smart' -d '{\"model\":\"god-smart\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'",
        "",
        "# Check GPU",
        "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv",
        "```",
        f"",
        "---",
        f"",
        "*This file is auto-generated by `archivist.py boot`. Do not edit manually — it will be overwritten.*",
        f"",
        "**Next Steps:** Read `schema.md` for agent conventions, then `index.md` for full content catalog.",
    ])
    
    return '\n'.join(lines)

def generate_models_page(models_data: list) -> str:
    """Generate entities/models.md from ModelRelay API data."""
    up_models = [m for m in models_data if m.get('status') == 'up']
    down_models = [m for m in models_data if m.get('status') == 'down']
    
    lines = [
        "---",
        "date: " + now_iso(),
        "category: entity",
        "status: active",
        "confidence: verified",
        "---",
        f"",
        "# Models Entity",
        f"",
        f"**Total Discovered:** {len(models_data)}",
        f"**UP:** {len(up_models)} | **DOWN:** {len(down_models)}",
        f"**Generated:** {now_iso()}",
        f"",
        "---",
        f"",
        "## Top Models by Intelligence (UP only)",
        f"",
        "| Model | Intelligence | Provider | Latency | Context | Status |",
        "|-------|-------------|----------|---------|---------|--------|",
    ]
    
    sorted_models = sorted(up_models, key=lambda x: x.get('intell', 0), reverse=True)
    for m in sorted_models[:20]:
        lines.append(f"| {m.get('modelId', 'unknown')} | {m.get('intell', 'N/A')} | {m.get('providerKey', 'unknown')} | {m.get('avg', 'N/A')}ms | {m.get('ctx', 'N/A')} | {m.get('status', 'unknown')} |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## Down Models (Top 10 by Intelligence)",
        f"",
        "| Model | Intelligence | Provider | Error |",
        "|-------|-------------|----------|-------|",
    ])
    
    sorted_down = sorted(down_models, key=lambda x: x.get('intell', 0), reverse=True)
    for m in sorted_down[:10]:
        err = m.get('lastError', {}).get('code', 'unknown') if m.get('lastError') else 'unknown'
        lines.append(f"| {m.get('modelId', 'unknown')} | {m.get('intell', 'N/A')} | {m.get('providerKey', 'unknown')} | {err} |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "*Auto-generated from ModelRelay API. Update with `archivist.py ingest --models`.*",
    ])
    
    return '\n'.join(lines)

def generate_providers_page() -> str:
    """Generate entities/providers.md from .modelrelay.json."""
    config_path = Path(r'C:\Users\speci.000\.modelrelay.json')
    providers = []
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            for key, prov in config.get('providers', {}).items():
                providers.append({
                    'name': key,
                    'interval': prov.get('pingIntervalMinutes', 'default'),
                    'discover': prov.get('discoverModels', False),
                    'baseUrl': prov.get('baseUrl', 'default'),
                })
        except Exception as e:
            providers = [{'name': 'error', 'interval': f'load failed: {e}'}]
    
    lines = [
        "---",
        "date: " + now_iso(),
        "category: entity",
        "status: active",
        "confidence: verified",
        "---",
        f"",
        "# Providers Entity",
        f"",
        "**Source:** `.modelrelay.json`",
        f"**Generated:** {now_iso()}",
        f"",
        "---",
        f"",
        "| Provider | Ping Interval | Discover | Base URL |",
        "|----------|--------------|----------|----------|",
    ]
    
    for p in sorted(providers, key=lambda x: x['name']):
        lines.append(f"| {p['name']} | {p['interval']} min | {p['discover']} | {p['baseUrl']} |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "*Auto-generated from .modelrelay.json. Update with `archivist.py ingest --models`.*",
    ])
    
    return '\n'.join(lines)

def generate_sources_page(name: str, dir_path: Path, files: list) -> str:
    """Generate a source summary page."""
    categories = defaultdict(list)
    for f in files:
        cat = categorize_file(f['path'])
        categories[cat].append(f)
    
    lines = [
        "---",
        f"date: {now_iso()}",
        "category: source",
        "status: active",
        "confidence: verified",
        "---",
        f"",
        f"# Source: {name}",
        f"",
        f"**Path:** `{dir_path}`",
        f"**Total Files:** {len(files)}",
        f"**Total Size:** {sum(f['size'] for f in files) / (1024*1024):.1f} MB",
        f"**Generated:** {now_iso()}",
        f"",
        "---",
        f"",
        "## File Categories",
        f"",
        "| Category | Count | Total Size |",
        "|----------|-------|------------|",
    ]
    
    for cat, cat_files in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        total_size = sum(f['size'] for f in cat_files)
        lines.append(f"| {cat} | {len(cat_files)} | {total_size / (1024*1024):.1f} MB |")
    
    lines.extend([
        f"",
        "---",
        f"",
        "## Recent Files (Top 20)",
        f"",
    ])
    
    sorted_files = sorted(files, key=lambda x: x['mtime'], reverse=True)
    for f in sorted_files[:20]:
        size_str = f"{f['size'] / 1024:.1f} KB" if f['size'] < 1024*1024 else f"{f['size'] / (1024*1024):.1f} MB"
        lines.append(f"- `{f['path']}` — {size_str}, {f['mtime']}")
    
    lines.extend([
        f"",
        "---",
        f"",
        f"*Auto-generated from directory scan. Update with `archivist.py ingest`.*",
    ])
    
    return '\n'.join(lines)

# =============================================================================
# Main Commands
# =============================================================================

def cmd_ingest(force: bool = False):
    """Ingest all sources and update wiki."""
    print("NEXUS Archivist — Ingest Mode")
    print("=" * 60)
    
    wiki_state = {
        'page_count': 0,
        'source_count': 0,
        'last_ingest': now_iso(),
        'entities': [],
        'concepts': [],
        'sources': [],
        'recent_logs': [],
        'top_models': [],
        'providers': [],
        'recent_changes': [],
        'open_issues': [],
    }
    
    # Scan raw directories
    print("\n[1/6] Scanning raw sources...")
    all_files = {}
    for name, dir_path in RAW_DIRS.items():
        # Use depth 2 for large directories, depth 3 for smaller ones
        max_d = 2 if name in ('archivist', 'papers') else 3
        files = scan_directory(dir_path, max_depth=max_d, max_size_mb=50)
        all_files[name] = files
        wiki_state['source_count'] += len(files)
        print(f"  {name}: {len(files)} files")
    
    # Generate source pages
    print("\n[2/6] Generating source pages...")
    for name, files in all_files.items():
        page_path = WIKI_DIR / 'sources' / f'{name}.md'
        content = generate_sources_page(name, RAW_DIRS[name], files)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(content)
        wiki_state['sources'].append({'name': name, 'summary': f'{len(files)} files scanned'})
        print(f"  Written: {page_path}")
    
    # Fetch model data from ModelRelay
    print("\n[3/6] Fetching model data from ModelRelay...")
    models_data = []
    try:
        import urllib.request
        req = urllib.request.Request('http://localhost:7352/api/models')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            models_data = data.get('models', [])
        print(f"  Fetched {len(models_data)} models")
    except Exception as e:
        print(f"  Warning: Could not fetch model data: {e}")
    
    # Generate entity pages
    print("\n[4/6] Generating entity pages...")
    
    # Models
    models_page = WIKI_DIR / 'entities' / 'models.md'
    with open(models_page, 'w', encoding='utf-8') as f:
        f.write(generate_models_page(models_data))
    wiki_state['entities'].append({'name': 'Models', 'summary': f'{len(models_data)} models tracked'})
    print(f"  Written: {models_page}")
    
    # Providers
    providers_page = WIKI_DIR / 'entities' / 'providers.md'
    with open(providers_page, 'w', encoding='utf-8') as f:
        f.write(generate_providers_page())
    wiki_state['entities'].append({'name': 'Providers', 'summary': 'Provider configurations'})
    print(f"  Written: {providers_page}")
    
    # Agents (placeholder — can be expanded)
    agents_page = WIKI_DIR / 'entities' / 'agents.md'
    with open(agents_page, 'w', encoding='utf-8') as f:
        f.write("# Agents Entity\n\n**Status:** Placeholder\n\nAgent definitions tracked here.\n")
    wiki_state['entities'].append({'name': 'Agents', 'summary': 'Agent definitions'})
    print(f"  Written: {agents_page}")
    
    # Projects
    projects_page = WIKI_DIR / 'entities' / 'projects.md'
    with open(projects_page, 'w', encoding='utf-8') as f:
        f.write("# Projects Entity\n\n**Status:** Placeholder\n\nProject state tracked here.\n")
    wiki_state['entities'].append({'name': 'Projects', 'summary': 'Project states'})
    print(f"  Written: {projects_page}")
    
    # Generate concept pages (placeholders for now)
    print("\n[5/6] Generating concept pages...")
    concepts = ['benchmarking', 'security', 'architecture', 'governance']
    for concept in concepts:
        page_path = WIKI_DIR / 'concepts' / f'{concept}.md'
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(f"# {concept.title()} Concept\n\n**Status:** Placeholder\n\nConcept page for {concept}.\n")
        wiki_state['concepts'].append({'name': concept.title(), 'summary': f'{concept} concept page'})
        print(f"  Written: {page_path}")
    
    # Build state from models_data
    if models_data:
        up_models = [m for m in models_data if m.get('status') == 'up']
        sorted_up = sorted(up_models, key=lambda x: x.get('intell', 0), reverse=True)
        wiki_state['top_models'] = [
            {
                'name': m.get('modelId', 'unknown'),
                'intell': m.get('intell', 'N/A'),
                'provider': m.get('providerKey', 'unknown'),
                'status': m.get('status', 'unknown'),
            }
            for m in sorted_up[:10]
        ]
        
        # Provider summary
        provider_counts = defaultdict(lambda: {'up': 0, 'down': 0})
        for m in models_data:
            pk = m.get('providerKey', 'unknown')
            status = m.get('status', 'unknown')
            if status == 'up':
                provider_counts[pk]['up'] += 1
            else:
                provider_counts[pk]['down'] += 1
        
        for pk, counts in sorted(provider_counts.items(), key=lambda x: x[1]['up'], reverse=True):
            wiki_state['providers'].append({
                'name': pk,
                'up': counts['up'],
                'down': counts['down'],
                'issue': 'None' if counts['down'] == 0 else f'{counts["down"]} down',
            })
    
    # Recent changes and issues
    wiki_state['recent_changes'] = [
        'NVIDIA models fixed: 14 models now UP (was 0)',
        'Intelligence scores updated with Arena benchmark data',
        'ModelRelay ping intervals increased: 1min → 5-60min',
        'Sensitive files moved to vault: sshkey.pem, env.txt, zilliz credentials',
        'ARCHIVIST index created: 1,590 files catalogued',
    ]
    wiki_state['open_issues'] = [
        'NVIDIA: 19 models still DOWN (404/500 on non-existent endpoints)',
        'Google AI: 11 models DOWN (credits depleted, need new key)',
        'GitHub Models: 0 UP (1500/day limit exceeded, ~5.6h cooldown)',
        'Cerebras: 0 UP (paywalled, payment_required)',
        'Next.js Dashboard: Port 3000 occupied by WSL relay (needs reconfiguration)',
    ]
    
    # Update log
    print("\n[6/6] Updating index and log...")
    log_entry = generate_log_entry('ingest', f'Scanned {wiki_state["source_count"]} files, {len(models_data)} models', {
        'sources': {k: len(v) for k, v in all_files.items()},
        'models_up': len(up_models) if models_data else 0,
        'models_down': len(models_data) - len(up_models) if models_data else 0,
    })
    
    log_path = WIKI_DIR / 'log.md'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')
    print(f"  Appended to: {log_path}")
    
    # Add to recent logs
    wiki_state['recent_logs'].append({
        'time': now_iso(),
        'action': 'ingest',
        'summary': f'Scanned {wiki_state["source_count"]} files, {len(models_data)} models',
    })
    
    # Generate index
    wiki_state['page_count'] = len(wiki_state['entities']) + len(wiki_state['concepts']) + len(wiki_state['sources']) + 2  # + index + log
    index_path = WIKI_DIR / 'index.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(generate_index(wiki_state))
    print(f"  Written: {index_path}")
    
    # Generate boot
    boot_path = WIKI_DIR / 'boot.md'
    with open(boot_path, 'w', encoding='utf-8') as f:
        f.write(generate_boot(wiki_state))
    print(f"  Written: {boot_path}")
    
    # Save wiki state
    state_path = BASE_DIR / 'wiki_state.json'
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(wiki_state, f, indent=2, default=str)
    print(f"  Written: {state_path}")
    
    print("\n" + "=" * 60)
    print("Ingest complete!")
    print(f"Wiki pages: {wiki_state['page_count']}")
    print(f"Sources indexed: {wiki_state['source_count']}")
    print(f"Models tracked: {len(models_data)}")
    print(f"\nNext: Read {boot_path} for fast agent sync")

def cmd_lint(fix: bool = False):
    """Health check the wiki."""
    print("NEXUS Archivist — Lint Mode")
    print("=" * 60)
    
    issues = []
    
    # Check for orphan pages
    print("\n[1/3] Checking for orphan pages...")
    wiki_files = list(WIKI_DIR.rglob('*.md'))
    all_content = {}
    for wf in wiki_files:
        with open(wf, 'r', encoding='utf-8') as f:
            all_content[wf.name] = f.read()
    
    for wf in wiki_files:
        name = wf.stem
        if name in ('index', 'log', 'boot'):
            continue
        found = any(f'[[{name}]]' in content or f'[[{name.title()}]]' in content for content in all_content.values())
        if not found:
            issues.append(f"Orphan page: {wf.relative_to(WIKI_DIR)}")
    
    print(f"  Found {len(issues)} orphans")
    
    # Check for stale pages
    print("\n[2/3] Checking for stale pages...")
    for wf in wiki_files:
        mtime = datetime.fromtimestamp(wf.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        if age_days > 30:
            with open(wf, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'status: active' in content and 'Auto-generated' in content:
                issues.append(f"Stale page: {wf.relative_to(WIKI_DIR)} ({age_days} days)")
    
    print(f"  Total issues: {len(issues)}")
    
    # Check for missing concepts
    print("\n[3/3] Checking for missing pages...")
    expected_pages = ['entities/models.md', 'entities/providers.md', 'concepts/benchmarking.md']
    for ep in expected_pages:
        if not (WIKI_DIR / ep).exists():
            issues.append(f"Missing page: {ep}")
    
    print(f"\n{'=' * 60}")
    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues[:20]:
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("Wiki is healthy! No issues found.")
    
    if fix and issues:
        print("\nFix mode: Running ingest to regenerate auto-generated pages...")
        cmd_ingest(force=True)

def cmd_status():
    """Show current wiki status."""
    state_path = BASE_DIR / 'wiki_state.json'
    if not state_path.exists():
        print("Wiki not initialized. Run: python archivist.py ingest")
        return
    
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    print("NEXUS Archivist — Status")
    print("=" * 60)
    print(f"Last ingest: {state.get('last_ingest', 'never')}")
    print(f"Wiki pages: {state.get('page_count', 0)}")
    print(f"Sources indexed: {state.get('source_count', 0)}")
    print(f"Entities: {len(state.get('entities', []))}")
    print(f"Concepts: {len(state.get('concepts', []))}")
    print(f"Sources: {len(state.get('sources', []))}")
    print(f"\nTop 5 models:")
    for m in state.get('top_models', [])[:5]:
        print(f"  {m['name']}: {m['intell']} ({m['provider']})")
    print(f"\nProviders:")
    for p in state.get('providers', [])[:5]:
        print(f"  {p['name']}: {p['up']} UP, {p['down']} DOWN")

def cmd_boot():
    """Regenerate boot.md only."""
    state_path = BASE_DIR / 'wiki_state.json'
    if not state_path.exists():
        print("Wiki not initialized. Run: python archivist.py ingest")
        return
    
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    boot_path = WIKI_DIR / 'boot.md'
    with open(boot_path, 'w', encoding='utf-8') as f:
        f.write(generate_boot(state))
    
    print(f"Regenerated: {boot_path}")
    print(f"Agents can now fast-sync by reading this file.")

# =============================================================================
# Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='NEXUS Archivist Engine')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # ingest
    ingest_parser = subparsers.add_parser('ingest', help='Scan sources and update wiki')
    ingest_parser.add_argument('--force', action='store_true', help='Force full re-ingest')
    
    # lint
    lint_parser = subparsers.add_parser('lint', help='Health check wiki')
    lint_parser.add_argument('--fix', action='store_true', help='Auto-fix issues by re-ingesting')
    
    # status
    subparsers.add_parser('status', help='Show wiki status')
    
    # boot
    subparsers.add_parser('boot', help='Regenerate boot.md')
    
    args = parser.parse_args()
    
    if args.command == 'ingest':
        cmd_ingest(force=args.force)
    elif args.command == 'lint':
        cmd_lint(fix=args.fix)
    elif args.command == 'status':
        cmd_status()
    elif args.command == 'boot':
        cmd_boot()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python archivist.py ingest       # Scan all sources")
        print("  python archivist.py status       # Show status")
        print("  python archivist.py lint         # Check wiki health")
        print("  python archivist.py boot         # Regenerate boot.md")

if __name__ == '__main__':
    main()
