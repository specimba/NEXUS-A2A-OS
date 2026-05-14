import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3000;

// Pre-load ALL content into memory at startup
const fileCache = new Map();
const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ico': 'image/x-icon',
  '.map': 'application/json',
  '.txt': 'text/plain',
};

function loadDirectory(dir, urlPrefix) {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const urlPath = urlPrefix + entry.name;
      if (entry.isDirectory()) {
        loadDirectory(fullPath, urlPath + '/');
      } else {
        try {
          const data = fs.readFileSync(fullPath);
          const ext = path.extname(entry.name);
          fileCache.set(urlPath, { data, contentType: mimeTypes[ext] || 'application/octet-stream' });
        } catch (e) { /* skip unreadable files */ }
      }
    }
  } catch (e) { /* skip unreadable dirs */ }
}

// Load index.html
let indexHTML = '';
try {
  indexHTML = fs.readFileSync(path.join(__dirname, '.next/server/app/index.html'), 'utf8');
  fileCache.set('/', { data: Buffer.from(indexHTML), contentType: 'text/html; charset=utf-8' });
  console.log(`Loaded index.html: ${indexHTML.length} bytes`);
} catch (e) {
  console.error('Failed to load index.html:', e.message);
}

// Load all static files into memory
loadDirectory(path.join(__dirname, '.next/static'), '/_next/static/');
console.log(`Loaded ${fileCache.size} files into memory`);

// Load public files
loadDirectory(path.join(__dirname, 'public'), '/');
console.log(`Total cached files: ${fileCache.size}`);

const server = http.createServer((req, res) => {
  try {
    const url = new URL(req.url || '/', `http://localhost:${PORT}`);
    let urlPath = url.pathname;
    
    // Remove trailing backslash from escaped paths
    urlPath = urlPath.replace(/\\/g, '');
    
    // Root path → index.html
    if (urlPath === '/' || urlPath === '') urlPath = '/';
    
    // Try cache first
    const cached = fileCache.get(urlPath);
    if (cached) {
      const cacheControl = urlPath.startsWith('/_next/static/') 
        ? 'public, max-age=31536000, immutable' 
        : 'no-cache';
      res.writeHead(200, { 
        'Content-Type': cached.contentType, 
        'Cache-Control': cacheControl,
        'Access-Control-Allow-Origin': '*',
      });
      res.end(cached.data);
      return;
    }
    
    // Try without query string (some chunks may have different naming)
    // Also try finding the file by prefix match for hash-based filenames
    
    // API routes - return mock data
    if (urlPath.startsWith('/api/')) {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
      res.end(JSON.stringify({ status: 'ok', timestamp: Date.now() }));
      return;
    }
    
    // SPA fallback: serve index.html for any unmatched route
    if (!urlPath.includes('.') && urlPath !== '/') {
      res.writeHead(200, { 
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Access-Control-Allow-Origin': '*',
      });
      res.end(indexHTML);
      return;
    }
    
    // 404
    res.writeHead(404, { 'Access-Control-Allow-Origin': '*' });
    res.end('Not found');
  } catch (e) {
    try { res.writeHead(500); res.end('Error'); } catch (e2) {}
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`NEXUS-OS lightweight server on port ${PORT} (${fileCache.size} files cached)`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 5000);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 5000);
});

// Keep process alive
setInterval(() => {
  // heartbeat - prevents the process from being garbage collected
}, 30000);
