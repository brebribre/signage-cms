// Production server for the web player: serves `dist/` and proxies `/api/*` to the backend,
// server-to-server — the same job, and the same reasoning, as frontend/server.mjs.
//
// A screen only ever talks to this one origin. That keeps the backend's CORS list out of the
// picture entirely (a TV browser pointed at the player needs no allow-listing anywhere), and it
// means the address a screen is set up with never changes when the backend's does — only this
// service's BACKEND_URL does.
//
// Plus one thing frontend/server.mjs has no need for: `/version.json`, which names the deploy
// this process is serving. A running screen checks it and reloads itself when it changes — the
// web player's counterpart to the Android player installing a new APK.
//
// Deliberately dependency-free, like its sibling.

import { createServer } from 'node:http'
import { request as httpRequest } from 'node:http'
import { request as httpsRequest } from 'node:https'
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs'
import { extname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const DIST = join(__dirname, 'dist')
const PORT = process.env.PORT || 4174

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001'
const backend = new URL(BACKEND_URL)

const { version } = JSON.parse(readFileSync(join(__dirname, 'package.json'), 'utf8'))
// Railway gives every deploy its own id. Anywhere else, a restart is as close to "a new deploy"
// as this process can tell.
const BUILD = process.env.RAILWAY_DEPLOYMENT_ID || process.env.RAILWAY_GIT_COMMIT_SHA || String(Date.now())

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
}

function serveVersion(res) {
  res.writeHead(200, { 'Content-Type': MIME['.json'], 'Cache-Control': 'no-store' })
  // apiHost is what the pairing screen shows as "the server it is talking to" — the backend
  // itself, since this proxy is transparent and naming it would help nobody diagnose anything.
  res.end(JSON.stringify({ version: `web-${version}`, build: BUILD, apiHost: backend.host }))
}

function serveStatic(req, res) {
  const urlPath = decodeURIComponent(req.url.split('?')[0])
  let filePath = join(DIST, urlPath)
  const missing = !filePath.startsWith(DIST) || !existsSync(filePath) || statSync(filePath).isDirectory()

  if (missing) {
    // A missing file is a 404, never index.html — see frontend/server.mjs for the deploy-time
    // failure that answering a hashed chunk with HTML causes.
    if (extname(urlPath)) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' })
      res.end('Not found')
      return
    }
    filePath = join(DIST, 'index.html')
  }

  const ext = extname(filePath)
  // Pages name the hashed chunks they load, and sw.js must be re-checked to ever change.
  const noCache = ext === '.html' || urlPath === '/sw.js'
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Cache-Control': noCache
      ? 'no-cache'
      : urlPath.startsWith('/assets/')
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=3600',
  })
  createReadStream(filePath).pipe(res)
}

function proxyApi(req, res) {
  const doRequest = backend.protocol === 'https:' ? httpsRequest : httpRequest
  const upstreamPath = req.url.replace(/^\/api/, '') || '/'

  const proxyReq = doRequest(
    {
      protocol: backend.protocol,
      hostname: backend.hostname,
      port: backend.port || (backend.protocol === 'https:' ? 443 : 80),
      path: upstreamPath,
      method: req.method,
      headers: { ...req.headers, host: backend.host },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers)
      proxyRes.pipe(res)
    },
  )
  proxyReq.on('error', (err) => {
    console.error('proxy error:', err.message)
    if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ detail: 'Could not reach the API' }))
  })
  req.pipe(proxyReq)
}

createServer((req, res) => {
  if (req.url.startsWith('/api/') || req.url === '/api') proxyApi(req, res)
  else if (req.url.split('?')[0] === '/version.json') serveVersion(res)
  else serveStatic(req, res)
}).listen(PORT, () => {
  console.log(`Fortu web player (web-${version}, build ${BUILD}) on :${PORT}, proxying /api/* to ${BACKEND_URL}`)
})
