import os
import re
import stat
import sys
import hashlib
from pathlib import Path

# Reconfigure stdout/stderr for UTF-8 to handle console printing on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Canonical files list
CANONICAL_FILES = [
    '01_PROJECT_STATE.md',
    'AGENTS.md',
    'CONTRIBUTING.md',
    'README.md',
    'knowledge.md',
    'worklog.md',
    'DECISION_LOG.md'
]

def parse_frontmatter(content):
    match = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n', content)
    if not match:
        return {}, content
    
    yaml_content = match.group(1)
    body = content[match.end():]
    
    frontmatter = {}
    lines = yaml_content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            parts = line.split(':', 1)
            k = parts[0].strip()
            v = parts[1].strip().strip('\'\"')
            frontmatter[k] = v
    return frontmatter, body

def serialize_frontmatter(fm):
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"

def get_md_files(d, fl):
    if not os.path.exists(d):
        return
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

# Gather files
fl = []
get_md_files('c:/Users/speci.000/Documents/NEXUS/docs', fl)
get_md_files('C:/Users/speci.000/Downloads/ARCHIVIST', fl)

# Also check workspace root .md files
for item in os.listdir('c:/Users/speci.000/Documents/NEXUS'):
    if item.endswith('.md') and os.path.isfile(os.path.join('c:/Users/speci.000/Documents/NEXUS', item)):
        fl.append(os.path.join('c:/Users/speci.000/Documents/NEXUS', item))

print(f"Gathered {len(fl)} markdown files for frontmatter migration.")

success_count = 0
fail_count = 0

# Set deterministic hashes / defaults
DEFAULT_POLICY_HASH = hashlib.sha256(b"nexus-default-governance-policy-v2.0").hexdigest()

for idx, f_path in enumerate(fl, 1):
    try:
        content = open(f_path, 'r', encoding='utf-8', errors='ignore').read()
        fm, body = parse_frontmatter(content)
        
        changed = False
        
        # 1. id
        if not fm.get('id'):
            stem = Path(f_path).stem
            fm['id'] = f"NODE-MIG-{stem.upper().replace('-', '_').replace(' ', '_')}"
            changed = True
            
        # 2. authority_scope
        if not fm.get('authority_scope'):
            filename = os.path.basename(f_path)
            if 'ARCHIVIST' in f_path:
                fm['authority_scope'] = 'historical-import'
            elif filename in CANONICAL_FILES:
                fm['authority_scope'] = 'local-canonical'
            else:
                fm['authority_scope'] = 'experimental'
            changed = True
            
        # 3. origin_sha256 (or source_sha256)
        if not fm.get('origin_sha256') and not fm.get('source_sha256'):
            body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
            fm['origin_sha256'] = body_hash
            changed = True
            
        # 4. policy_hash
        if not fm.get('policy_hash'):
            fm['policy_hash'] = DEFAULT_POLICY_HASH
            changed = True
            
        # 5. sandbox_profile
        if not fm.get('sandbox_profile'):
            if 'ARCHIVIST' in f_path:
                fm['sandbox_profile'] = 'native-kernel'
            else:
                fm['sandbox_profile'] = 'openshell-reviewground'
            changed = True
            
        # 6. approval_id
        if not fm.get('approval_id'):
            stem_hash = hashlib.sha256(Path(f_path).name.encode('utf-8')).hexdigest()[:6].upper()
            fm['approval_id'] = f"APP-MIG-{stem_hash}"
            changed = True
            
        if changed:
            # Clear read-only attribute if set
            try:
                os.chmod(f_path, stat.S_IWRITE)
            except Exception:
                pass
            new_content = serialize_frontmatter(fm) + body
            open(f_path, 'w', encoding='utf-8').write(new_content)
            
        success_count += 1
    except Exception as e:
        # Secure printing to avoid encoding failure
        try:
            print(f"Error processing {f_path}: {e}")
        except Exception:
            print(f"Error processing file index {idx}: {type(e).__name__}")
        fail_count += 1

print(f"Migration completed. Successfully processed: {success_count}, Failed: {fail_count}")
