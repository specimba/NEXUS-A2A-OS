import http from 'http'
import fs from 'fs'
import path from 'path'

const PORT = 3000
const STATIC_DIR = path.join(process.cwd(), '.next', 'standalone')
const PUBLIC_DIR = path.join(process.cwd(), 'public')

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
}

function serveStatic(filePath, res) {
  if (!fs.existsSync(filePath)) return false
  const stat = fs.statSync(filePath)
  if (stat.isDirectory()) return false
  
  const ext = path.extname(filePath)
  const contentType = MIME_TYPES[ext] || 'application/octet-stream'
  
  const data = fs.readFileSync(filePath)
  res.writeHead(200, { 
    'Content-Type': contentType,
    'Cache-Control': 'public, max-age=3600'
  })
  res.end(data)
  return true
}

const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0]
  
  // Serve static files from .next/standalone
  if (urlPath.startsWith('/_next/')) {
    const filePath = path.join(STATIC_DIR, urlPath)
    if (serveStatic(filePath, res)) return
  }
  
  // Serve public files
  if (!urlPath.startsWith('/_next') && !urlPath.startsWith('/api')) {
    const publicPath = path.join(PUBLIC_DIR, urlPath)
    if (serveStatic(publicPath, res)) return
  }
  
  // Serve index.html for SPA routes
  const indexPath = path.join(STATIC_DIR, 'index.html')
  if (fs.existsSync(indexPath)) {
    serveStatic(indexPath, res)
    return
  }
  
  res.writeHead(404, { 'Content-Type': 'text/plain' })
  res.end('Not Found')
})

server.listen(PORT, () => {
  console.log(`Lightweight server running on http://localhost:${PORT}`)
})
