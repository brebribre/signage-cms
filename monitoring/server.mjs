// Production server for the built monitoring app: serves `dist/` as a static SPA and proxies
// `/api/*` through to the backend, server-to-server — the same arrangement as frontend/,
// for the same reason. The browser only ever talks to THIS origin, so the backend's session
// cookie arrives looking first-party and every browser accepts it; see DEPLOY.md, "Why the
// frontend proxies the API". Dependency-free on purpose.

import { createServer } from 'node:http'
import { request as httpRequest } from 'node:http'
import { request as httpsRequest } from 'node:https'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { extname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const DIST = join(__dirname, 'dist')
const PORT = process.env.PORT || 4174

// Runtime env var, read at request time — not a VITE_ variable baked into the bundle. The
// client just calls `/api/...` on its own origin and never knows this address.
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001'
const backend = new URL(BACKEND_URL)

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.webmanifest': 'application/manifest+json',
}

function serveStatic(req, res) {
  const urlPath = decodeURIComponent(req.url.split('?')[0])
  let filePath = join(DIST, urlPath)
  const missing =
    !filePath.startsWith(DIST) || !existsSync(filePath) || statSync(filePath).isDirectory()

  if (missing) {
    // A missing *file* is a 404 the app can recognise and recover from by reloading (a tab
    // open across a deploy asking for a chunk that no longer exists — see main.ts). Only a
    // path with no extension is a client-side route, and gets index.html.
    if (extname(urlPath)) {
      res.writeHead(404, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
      })
      res.end('Not found')
      return
    }
    filePath = join(DIST, 'index.html')
  }

  const ext = extname(filePath)
  const isIndex = filePath === join(DIST, 'index.html')
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    // index.html maps routes to hashed chunk names, so it must always be revalidated; the
    // hashed files under /assets/ can be cached hard — a new build means a new name.
    'Cache-Control': isIndex
      ? 'no-cache'
      : urlPath.startsWith('/assets/')
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=3600',
  })
  createReadStream(filePath).pipe(res)
}

function proxyApi(req, res) {
  const doRequest = backend.protocol === 'https:' ? httpsRequest : httpRequest
  // Strip the /api prefix — the backend's own routes (`/admin/...`) are unprefixed.
  const upstreamPath = req.url.replace(/^\/api/, '') || '/'

  const proxyReq = doRequest(
    {
      protocol: backend.protocol,
      hostname: backend.hostname,
      port: backend.port || (backend.protocol === 'https:' ? 443 : 80),
      path: upstreamPath,
      method: req.method,
      // Host rewritten to the backend's — everything else (cookies, content-type, the
      // browser's real Origin) passes through untouched.
      headers: { ...req.headers, host: backend.host },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers)
      proxyRes.pipe(res)
    },
  )
  proxyReq.on('error', (err) => {
    console.error('proxy error:', err.message)
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' })
    }
    res.end(JSON.stringify({ detail: 'Could not reach the API' }))
  })
  req.pipe(proxyReq)
}

createServer((req, res) => {
  if (req.url.startsWith('/api/') || req.url === '/api') {
    proxyApi(req, res)
  } else {
    serveStatic(req, res)
  }
}).listen(PORT, () => {
  console.log(`Paskall monitoring listening on :${PORT}, proxying /api/* to ${BACKEND_URL}`)
})
