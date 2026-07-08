const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CANONICAL_FILES = [
  '01_PROJECT_STATE.md',
  'AGENTS.md',
  'CONTRIBUTING.md',
  'README.md',
  'knowledge.md',
  'worklog.md',
  'DECISION_LOG.md'
];

function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) return null;
  const yamlContent = match[1];
  const frontmatter = {};

  const lines = yamlContent.split(/\r?\n/);
  let currentKey = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    if (trimmed.startsWith('-') && currentKey) {
      const val = trimmed.substring(1).trim().replace(/^['"]|['"]$/g, '');
      if (!Array.isArray(frontmatter[currentKey])) {
        frontmatter[currentKey] = [];
      }
      frontmatter[currentKey].push(val);
      continue;
    }

    const colonIndex = line.indexOf(':');
    if (colonIndex !== -1) {
      const key = line.substring(0, colonIndex).trim();
      const val = line.substring(colonIndex + 1).trim().replace(/^['"]|['"]$/g, '');

      currentKey = key;
      if (val === '') {
        frontmatter[key] = [];
      } else {
        if (val === 'true' || val === 'TRUE') {
          frontmatter[key] = true;
        } else if (val === 'false' || val === 'FALSE') {
          frontmatter[key] = false;
        } else if (!isNaN(Number(val)) && val.length > 0) {
          frontmatter[key] = Number(val);
        } else {
          frontmatter[key] = val;
        }
      }
    }
  }
  return frontmatter;
}

function getMdFiles(dir, filesList = []) {
  if (!fs.existsSync(dir)) return filesList;
  const items = fs.readdirSync(dir);
  for (const item of items) {
    const fullPath = path.join(dir, item);
    let stat;
    try {
      stat = fs.statSync(fullPath);
    } catch (e) {
      continue;
    }
    if (stat.isDirectory()) {
      if ([
        'node_modules', '.git', '.next', '.venv', 'venv', 
        '.nexus_pi', '.nexus', 'twave', 'reports', 'evidence', 
        'backups', 'bin', 'dist', 'public', '.claude', '.cline', 
        '.codex', '.devin', '.gemini', '.grok', '.kilo'
      ].includes(item)) {
        continue;
      }
      getMdFiles(fullPath, filesList);
    } else if (stat.isFile() && item.endsWith('.md')) {
      filesList.push(fullPath);
    }
  }
  return filesList;
}

function runScanner() {
  const workspaceRoot = 'c:\\Users\\speci.000\\Documents\\NEXUS';
  const docsDir = 'c:\\Users\\speci.000\\Documents\\NEXUS\\docs';
  const archivistDump = 'C:\\Users\\speci.000\\Downloads\\ARCHIVIST';

  const mdFiles = [];
  getMdFiles(docsDir, mdFiles);
  getMdFiles(archivistDump, mdFiles);

  if (fs.existsSync(workspaceRoot)) {
    const rootItems = fs.readdirSync(workspaceRoot);
    for (const item of rootItems) {
      if (item.endsWith('.md')) {
        const fullPath = path.join(workspaceRoot, item);
        try {
          if (fs.statSync(fullPath).isFile()) {
            mdFiles.push(fullPath);
          }
        } catch (e) {}
      }
    }
  }

  const nodes = [];
  const idMap = new Map();
  const contradictions = [];
  const errors = [];
  const warnings = [];

  for (const file of mdFiles) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const rawFm = parseFrontmatter(content);
      const fm = rawFm ? { ...rawFm } : {};
      const body = rawFm ? content.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '') : content;
      const filename = path.basename(file);

      if (!fm.id) {
        fm.id = filename.replace(/\.md$/, '');
      }
      if (!fm.authority_scope) {
        if (file.startsWith(archivistDump)) {
          fm.authority_scope = 'historical-import';
        } else if (CANONICAL_FILES.includes(filename)) {
          fm.authority_scope = 'local-canonical';
        } else {
          fm.authority_scope = 'experimental';
        }
      }
      if (!fm.origin_sha256 && !fm.source_sha256) {
        fm.origin_sha256 = crypto.createHash('sha256').update(body).digest('hex');
      }
      if (!fm.policy_hash) {
        fm.policy_hash = crypto.createHash('sha256').update('nexus-default-governance-policy-v2.0').digest('hex');
      }
      if (!fm.sandbox_profile) {
        fm.sandbox_profile = file.startsWith(archivistDump) ? 'native-kernel' : 'openshell-reviewground';
      }
      if (!fm.approval_id) {
        const hash = crypto.createHash('sha256').update(filename).digest('hex').slice(0, 6).toUpperCase();
        fm.approval_id = `APP-MIG-${hash}`;
      }
      const stat = fs.statSync(file);

      let truth_layer = fm?.truth_layer || fm?.type;
      if (!truth_layer) {
        const lowerPath = file.toLowerCase();
        if (lowerPath.includes('/raw/') || lowerPath.includes('\\raw\\') || filename.startsWith('SRC-')) {
          truth_layer = 'SOURCE';
        } else if (lowerPath.includes('/briefs/') || lowerPath.includes('\\briefs\\') || filename.startsWith('EXT-')) {
          truth_layer = 'EXTRACTED';
        } else if (lowerPath.includes('/drafts/') || lowerPath.includes('\\drafts\\') || filename.startsWith('INF-')) {
          truth_layer = 'INFERRED';
        } else if (lowerPath.includes('/published/') || lowerPath.includes('\\published\\') || CANONICAL_FILES.includes(filename) || filename.startsWith('CANON-')) {
          truth_layer = 'CANONICAL';
        } else {
          truth_layer = 'SOURCE';
        }
      }
      truth_layer = String(truth_layer).toUpperCase();
      if (!['SOURCE', 'EXTRACTED', 'INFERRED', 'CANONICAL'].includes(truth_layer)) {
        truth_layer = 'SOURCE';
      }

      let authority_scope = fm?.authority_scope;
      if (!authority_scope) {
        if (file.startsWith(archivistDump)) {
          authority_scope = 'historical-import';
        } else if (CANONICAL_FILES.includes(filename)) {
          authority_scope = 'local-canonical';
        } else {
          authority_scope = 'experimental';
        }
      }

      const id = String(fm?.id || filename.replace(/\.md$/, ''));
      const verified = fm?.verified === true || String(fm?.verified).toLowerCase() === 'true';
      const confidence = fm?.confidence !== undefined ? Number(fm?.confidence) : null;
      const canonical_ref = fm?.canonical_ref || null;
      const provenance = fm?.provenance || null;

      nodes.push({
        filePath: file,
        filename,
        id,
        truth_layer,
        authority_scope,
        confidence,
        canonical_ref,
        provenance,
        verified,
        frontmatter: fm,
        body,
        mtimeMs: stat.mtimeMs
      });

      if (!idMap.has(id)) {
        idMap.set(id, []);
      }
      idMap.get(id).push(file);
    } catch (e) {
      errors.push(`Failed to parse ${file}: ${String(e)}`);
    }
  }

  const existingIds = new Set(nodes.map(n => n.id));
  const existingFilenames = new Set(nodes.map(n => n.filename.replace(/\.md$/, '')));

  for (const node of nodes) {
    const pathsWithId = idMap.get(node.id) || [];
    if (pathsWithId.length > 1) {
      const otherFile = pathsWithId.find(p => p !== node.filePath);
      const otherRel = otherFile ? path.relative(workspaceRoot, otherFile) : 'unknown';
      const msg = `Duplicate ID '${node.id}' also found in ${otherRel}`;
      errors.push(`${node.filename}: ${msg}`);
      contradictions.push({
        id: `CONTR-ID-${node.id}`,
        nodeA: node.id,
        nodeB: otherRel,
        field: 'id',
        severity: 'CRITICAL',
        layerA: node.truth_layer,
        layerB: 'UNKNOWN'
      });
    }

    if (node.confidence !== null) {
      if (isNaN(node.confidence) || node.confidence < 0.0 || node.confidence > 1.0) {
        const msg = `confidence ${node.confidence} out of range [0,1]`;
        errors.push(`${node.filename}: ${msg}`);
        contradictions.push({
          id: `CONTR-CONF-${node.id}`,
          nodeA: node.id,
          nodeB: 'N/A',
          field: 'confidence',
          severity: 'CRITICAL',
          layerA: node.truth_layer,
          layerB: 'N/A'
        });
      }

      if (node.truth_layer === 'INFERRED' && node.confidence >= 0.9) {
        const msg = `INFERRED node with high confidence (${node.confidence}). Consider promoting or lowering.`;
        warnings.push(`${node.filename}: ${msg}`);
        contradictions.push({
          id: `CONTR-CONF-WARN-${node.id}`,
          nodeA: node.id,
          nodeB: 'N/A',
          field: 'confidence',
          severity: 'WARNING',
          layerA: 'INFERRED',
          layerB: 'N/A'
        });
      }
    }

    if (node.truth_layer === 'INFERRED' || node.truth_layer === 'CANONICAL') {
      if (!node.canonical_ref) {
        const msg = `${node.truth_layer} nodes must have 'canonical_ref'`;
        warnings.push(`${node.filename}: ${msg}`);
        contradictions.push({
          id: `CONTR-REF-${node.id}`,
          nodeA: node.id,
          nodeB: 'N/A',
          field: 'canonical_ref',
          severity: 'WARNING',
          layerA: node.truth_layer,
          layerB: 'N/A'
        });
      } else {
        const refMatch = node.canonical_ref.match(/\[\[(.*?)\]\]/);
        if (refMatch) {
          const refTarget = refMatch[1].trim();
          if (!CANONICAL_FILES.includes(refTarget) && !CANONICAL_FILES.includes(`${refTarget}.md`)) {
            const msg = `canonical_ref points to unknown canonical file: '${refTarget}'`;
            warnings.push(`${node.filename}: ${msg}`);
          }
        }
      }
    }

    if (node.truth_layer === 'SOURCE' && !node.provenance) {
      warnings.push(`${node.filename}: SOURCE nodes should have 'provenance' field`);
    }

    const wikiLinks = node.body.match(/\[\[(.*?)\]\]/g) || [];
    for (const link of wikiLinks) {
      const target = link.replace(/\[\[|\]\]/g, '').split('|')[0].split('#')[0].trim();
      if (target && !existingIds.has(target) && !existingFilenames.has(target) && !CANONICAL_FILES.includes(target) && !CANONICAL_FILES.includes(`${target}.md`)) {
        warnings.push(`${node.filename}: Wiki link [[${target}]] target not found`);
        contradictions.push({
          id: `CONTR-LINK-${node.id}-${target}`,
          nodeA: node.id,
          nodeB: target,
          field: 'wiki_link',
          severity: 'WARNING',
          layerA: node.truth_layer,
          layerB: 'N/A'
        });
      }
    }
  }

  return { nodes, errors, warnings, contradictions };
}

function nodeLabel(node) {
  return node === 'N/A' ? 'N/A' : node;
}

function verify() {
  const { nodes, errors, warnings, contradictions } = runScanner();
  const criticalContradictions = contradictions.filter(c => c.severity === 'CRITICAL');
  const isValid = errors.length === 0 && criticalContradictions.length === 0;

  const auditLogPath = 'c:\\Users\\speci.000\\Documents\\NEXUS\\docs\\wiki\\graph\\archivist_audit.json';
  const auditLog = {
    timestamp: new Date().toISOString(),
    gate: 'archivist_integrity_next_v1',
    stats: {
      total: nodes.length,
      passed: nodes.length - errors.length - criticalContradictions.length,
      failed: errors.length + criticalContradictions.length
    },
    errors: [...errors, ...criticalContradictions.map(c => `Contradiction: ${c.nodeA} conflicts on ${c.field}`)],
    warnings: warnings,
    status: isValid ? 'PASS' : 'FAIL'
  };

  try {
    fs.mkdirSync(path.dirname(auditLogPath), { recursive: true });
    fs.writeFileSync(auditLogPath, JSON.stringify(auditLog, null, 2), 'utf-8');
    console.log(`Audit log written to: ${auditLogPath}`);
  } catch (e) {
    console.error('Failed to write archivist audit log:', e);
  }

  console.log('--- INTEGRITY CHECK RESULTS ---');
  console.log(`Nodes checked: ${nodes.length}`);
  console.log(`Status:        ${auditLog.status}`);
  console.log(`Errors:        ${errors.length}`);
  console.log(`Warnings:      ${warnings.length}`);
  if (errors.length > 0) {
    console.log('\nErrors found:');
    errors.forEach(e => console.log(`  - ${e}`));
  }
}

verify();
