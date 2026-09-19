// Serves the built site from dist/. Dependency-free, like the CMS frontend's server.
import { createServer } from 'node:http'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { extname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const DIST = join(fileURLToPath(new URL('.', import.meta.url)), 'dist')
const PORT = process.env.PORT || 4175
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
}

createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url ?? '/').split('?')[0])
  let filePath = join(DIST, urlPath)
  if (!filePath.startsWith(DIST) || !existsSync(filePath) || statSync(filePath).isDirectory()) {
    if (extname(urlPath)) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('Not found'); return }
    filePath = join(DIST, 'index.html')
  }
  const ext = extname(filePath)
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : urlPath.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'public, max-age=3600',
  })
  createReadStream(filePath).pipe(res)
}).listen(PORT, () => console.log(`Paskall website listening on :${PORT}`))
