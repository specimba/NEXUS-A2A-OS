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
