import os
import re

def parse_frontmatter(content):
    match = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n', content)
    if not match: return None
    fm = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        if ':' in line:
            parts = line.split(':', 1)
            k = parts[0].strip()
            v = parts[1].strip().strip('\'\"')
            fm[k] = v
    return fm

def get_md_files(d, fl):
    if not os.path.exists(d): return
    for root, dirs, files in os.walk(d):
        # Skip ignored directories
        dirs[:] = [dir for dir in dirs if dir not in [
            'node_modules', '.git', '.next', '.venv', 'venv', 
            '.nexus_pi', '.nexus', 'twave', 'reports', 'evidence', 
            'backups', 'bin', 'dist', 'public', '.claude', '.cline', 
            '.codex', '.devin', '.gemini', '.grok', '.kilo'
        ]]
        for f in files:
            if f.endswith('.md'):
                fl.append(os.path.join(root, f))

fl = []
get_md_files('c:/Users/speci.000/Documents/NEXUS/docs', fl)
get_md_files('C:/Users/speci.000/Downloads/ARCHIVIST', fl)

# Also check workspace root .md files
for item in os.listdir('c:/Users/speci.000/Documents/NEXUS'):
    if item.endswith('.md') and os.path.isfile(os.path.join('c:/Users/speci.000/Documents/NEXUS', item)):
        fl.append(os.path.join('c:/Users/speci.000/Documents/NEXUS', item))

print(f'Total markdown files found: {len(fl)}')
missing_fields = { 'authority_scope': 0, 'origin_sha256': 0, 'policy_hash': 0, 'sandbox_profile': 0, 'approval_id': 0 }
total = len(fl)
for f_path in fl:
    try:
        content = open(f_path, 'r', encoding='utf-8').read()
        fm = parse_frontmatter(content) or {}
        if not fm.get('authority_scope'): missing_fields['authority_scope'] += 1
        if not (fm.get('origin_sha256') or fm.get('source_sha256')): missing_fields['origin_sha256'] += 1
        if not fm.get('policy_hash'): missing_fields['policy_hash'] += 1
        if not fm.get('sandbox_profile'): missing_fields['sandbox_profile'] += 1
        if not fm.get('approval_id'): missing_fields['approval_id'] += 1
    except Exception as e:
        print(f'Error reading {f_path}: {e}')

print('Missing fields summary:', missing_fields)
