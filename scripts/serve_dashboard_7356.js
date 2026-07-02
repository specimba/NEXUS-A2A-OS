'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const rootDir = path.resolve(__dirname, '..');
const dashboardRoot = path.join(rootDir, 'nexus_os', 'monitoring');
const wikiRoot = path.join(rootDir, 'nexus_os', 'archivist', 'wiki-ui');
const port = Number.parseInt(process.env.PORT || '7356', 10) || 7356;
const host = process.env.HOST || '127.0.0.1';

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.wasm': 'application/wasm',
};

function sendText(res, statusCode, message) {
  res.writeHead(statusCode, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(message);
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

// ── Wiki content API (same-origin; the Next.js /api/wiki sets no CORS) ──
// GET /wiki/api/index          -> file index with frontmatter metadata
// GET /wiki/api/page/<slug>    -> raw markdown

const archivistWikiRoot = path.join(rootDir, 'nexus_os', 'archivist', 'wiki');
const docsRoot = path.join(rootDir, 'docs');
const DOCS_CATEGORIES = [
  'wiki', 'research', 'coordination', 'planning', 'operations',
  'handbook', 'governance', 'hermes', 'grounding',
];
const MAX_INDEX_FILES = 2000;

function parseFrontmatter(content) {
  const meta = { tags: [], confidence: null, priority: null, title: null };
  if (!content.startsWith('---')) return { meta, body: content };
  const end = content.indexOf('\n---', 3);
  if (end === -1) return { meta, body: content };
  const block = content.slice(3, end);
  const body = content.slice(end + 4);
  for (const rawLine of block.split('\n')) {
    const m = rawLine.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!m) continue;
    const [, key, valueRaw] = m;
    const value = valueRaw.trim();
    if (key === 'title') meta.title = value.replace(/^["']|["']$/g, '');
    else if (key === 'confidence') meta.confidence = Number.parseFloat(value) || null;
    else if (key === 'priority') meta.priority = Number.parseFloat(value) || null;
    else if (key === 'tags') {
      const inline = value.match(/^\[(.*)\]$/);
      if (inline) {
        meta.tags = inline[1].split(',').map((t) => t.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      }
    }
  }
  return { meta, body };
}

function describeMarkdown(filePath, slug, category) {
  const stat = fs.statSync(filePath);
  const content = fs.readFileSync(filePath, 'utf-8');
  const { meta, body } = parseFrontmatter(content);
  const headings = [];
  let title = meta.title;
  for (const line of body.split('\n')) {
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      if (!title && h[1] === '#') title = h[2].trim();
      if (h[1] !== '#') headings.push(h[2].trim());
      if (headings.length >= 12) break;
    }
  }
  const excerpt = body
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#') && !l.startsWith('|'))
    .slice(0, 3)
    .join(' ')
    .slice(0, 220);
  return {
    slug,
    title: title || path.basename(filePath, '.md'),
    category,
    updatedAt: stat.mtime.toISOString(),
    size: stat.size,
    headings,
    excerpt,
    frontmatter: { tags: meta.tags, confidence: meta.confidence, priority: meta.priority },
  };
}

function walkMarkdown(dir, onFile) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue; // skip .obsidian and friends
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkMarkdown(full, onFile);
    else if (entry.isFile() && entry.name.endsWith('.md')) onFile(full);
  }
}

function buildWikiIndex() {
  const files = [];
  const push = (filePath, slug, category) => {
    if (files.length >= MAX_INDEX_FILES) return;
    try {
      files.push(describeMarkdown(filePath, slug, category));
    } catch {
      /* unreadable file: skip */
    }
  };

  walkMarkdown(archivistWikiRoot, (filePath) => {
    const rel = path.relative(archivistWikiRoot, filePath).split(path.sep).join('/');
    const sub = rel.includes('/') ? rel.split('/')[0] : 'root';
    push(filePath, `archivist/${rel}`, `archivist/${sub}`);
  });
  for (const cat of DOCS_CATEGORIES) {
    walkMarkdown(path.join(docsRoot, cat), (filePath) => {
      const rel = path.relative(docsRoot, filePath).split(path.sep).join('/');
      push(filePath, `docs/${rel}`, `docs/${cat}`);
    });
  }

  const categories = [...new Set(files.map((f) => f.category))].sort();
  return { files, categories, count: files.length, generatedAt: new Date().toISOString() };
}

function resolveWikiPage(slug) {
  if (slug.includes('..') || slug.includes('\\') || slug.includes('\0') || slug.includes(':')) {
    return null;
  }
  let root;
  let rel;
  if (slug.startsWith('archivist/')) {
    root = archivistWikiRoot;
    rel = slug.slice('archivist/'.length);
  } else if (slug.startsWith('docs/')) {
    root = docsRoot;
    rel = slug.slice('docs/'.length);
    if (!DOCS_CATEGORIES.includes(rel.split('/')[0])) return null;
  } else {
    return null;
  }
  const filePath = path.resolve(root, rel);
  const realRoot = fs.realpathSync.native(root);
  if (!fs.existsSync(filePath)) return null;
  const realFile = fs.realpathSync.native(filePath);
  if (realFile !== realRoot && !realFile.startsWith(`${realRoot}${path.sep}`)) return null;
  if (!realFile.endsWith('.md')) return null;
  return realFile;
}

function handleWikiApi(pathname, res) {
  if (pathname === '/wiki/api/index') {
    sendJson(res, 200, buildWikiIndex());
    return true;
  }
  if (pathname.startsWith('/wiki/api/page/')) {
    const slug = decodeURIComponent(pathname.slice('/wiki/api/page/'.length));
    const filePath = resolveWikiPage(slug);
    if (!filePath) {
      sendJson(res, 404, { error: 'not found' });
      return true;
    }
    const content = fs.readFileSync(filePath, 'utf-8');
    res.writeHead(200, { 'Content-Type': 'text/markdown; charset=utf-8' });
    res.end(content);
    return true;
  }
  return false;
}

function resolveStaticPath(requestUrl) {
  let pathname;

  try {
    pathname = decodeURIComponent(new URL(requestUrl, `http://${host}:${port}`).pathname);
  } catch {
    return null;
  }

  if (pathname.includes('\\') || pathname.includes(':') || pathname.includes('\0')) {
    return null;
  }

  const segments = pathname.split('/').filter(Boolean);
  if (segments.some((segment) => segment === '..')) {
    return null;
  }

  let root = dashboardRoot;
  let relativePath = pathname;

  if (pathname === '/' || pathname === '/dashboard.html') {
    relativePath = '/dashboard.html';
  } else if (pathname === '/wiki' || pathname === '/wiki/') {
    root = wikiRoot;
    relativePath = '/nexus-dashboard.html';
  } else if (pathname.startsWith('/wiki/')) {
    root = wikiRoot;
    relativePath = pathname.slice('/wiki'.length);
  }

  const filePath = path.resolve(root, `.${relativePath}`);
  const realRoot = fs.realpathSync.native(root);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  const realFile = fs.realpathSync.native(filePath);
  if (realFile !== realRoot && !realFile.startsWith(`${realRoot}${path.sep}`)) {
    return null;
  }

  return realFile;
}

const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendText(res, 405, 'Method Not Allowed');
    return;
  }

  let apiPathname = null;
  try {
    apiPathname = decodeURIComponent(new URL(req.url || '/', `http://${host}:${port}`).pathname);
  } catch {
    apiPathname = null;
  }
  if (apiPathname && apiPathname.startsWith('/wiki/api/')) {
    try {
      if (handleWikiApi(apiPathname, res)) return;
    } catch (err) {
      sendJson(res, 500, { error: String(err && err.message ? err.message : err) });
      return;
    }
  }

  const filePath = resolveStaticPath(req.url || '/');
  if (!filePath) {
    sendText(res, 404, 'Not Found');
    return;
  }

  fs.stat(filePath, (statError, stat) => {
    if (statError || !stat.isFile()) {
      sendText(res, 404, 'Not Found');
      return;
    }

    const headers = {
      'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream',
      'Content-Length': stat.size,
    };

    res.writeHead(200, headers);

    if (req.method === 'HEAD') {
      res.end();
      return;
    }

    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(port, host, () => {
  const baseUrl = `http://${host === '127.0.0.1' ? 'localhost' : host}:${port}`;

  console.log(`NEXUS HTML dashboard active at ${baseUrl}/`);
  console.log(`Quality × Health Matrix: ${baseUrl}/dashboard.html`);
  console.log(`Wiki dashboard: ${baseUrl}/wiki/`);
  console.log('ModelRelay API expected at http://localhost:7350/v1 (Node) | fallback http://localhost:7355 (Python)');
});
