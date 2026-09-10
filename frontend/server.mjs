// Production server for the built frontend: serves `dist/` as a static SPA and proxies
// `/api/*` through to the backend, server-to-server.
//
// The whole point is that the browser then only ever talks to ONE origin — this service's
// own. A browser applies cross-site cookie rules by comparing the page's origin to the
// COOKIE's origin, and `up.railway.app` is on the public suffix list, so two separate
// Railway services (frontend + backend) are cross-site to a browser even though they share
// `railway.app`. Some browsers (Arc among them) block or drop a cross-site cookie outright,
// regardless of `SameSite=None; Secure` being set correctly — that combination is a browser
// COURTESY, not a guarantee, and this stops needing it: once every request the browser makes
// goes to this same origin, the backend's Set-Cookie is host-scoped to THIS domain, and it's
// no longer a cross-site cookie to anyone.
//
// Deliberately dependency-free (no express, no http-proxy-middleware) — this is a small,
// fixed job, and a hand-rolled ~60 line proxy is easier to trust than a new dependency for it.

import { createServer } from 'node:http'
import { request as httpRequest } from 'node:http'
import { request as httpsRequest } from 'node:https'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { extname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const DIST = join(__dirname, 'dist')
const PORT = process.env.PORT || 4173

// Where `/api/*` actually goes. Runtime env var, not `VITE_API_BASE_URL` — that one is
// baked into the client bundle at build time and the client now just calls `/api/...`
// relative to itself; this is read by this server, at request time.
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
  // SPA fallback — the same behaviour `serve -s` gave: an unknown path is a client-side
  // route, not a missing file, so it gets index.html and Vue Router takes over from there.
  if (!filePath.startsWith(DIST) || !existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(DIST, 'index.html')
  }
  const ext = extname(filePath)
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
  createReadStream(filePath).pipe(res)
}

function proxyApi(req, res) {
  const doRequest = backend.protocol === 'https:' ? httpsRequest : httpRequest
  // Strip the /api prefix — the backend's own routes (`/devices`, `/media`, …) are unprefixed.
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
  console.log(`Fortu CMS frontend listening on :${PORT}, proxying /api/* to ${BACKEND_URL}`)
})
