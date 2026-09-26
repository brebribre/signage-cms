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
  '.mp4': 'video/mp4',
}

// A browser will not send one, but anyone can: `GET /%` is not valid percent-encoding, and
// decodeURIComponent throws URIError on it. Thrown from inside a request handler that is the
// whole process — Node has no default catch there, so one unauthenticated request used to end
// the server, and Railway would restart it into the next one. See SECURITY_REVIEW.md, H1.
function decodePath(rawUrl) {
  const path = (rawUrl ?? '/').split('?')[0]
  try {
    return decodeURIComponent(path)
  } catch {
    return null
  }
}

createServer((req, res) => {
  const urlPath = decodePath(req.url)
  if (urlPath === null) {
    res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('Bad request')
    return
  }
  let filePath = join(DIST, urlPath)
  if (!filePath.startsWith(DIST) || !existsSync(filePath) || statSync(filePath).isDirectory()) {
    if (extname(urlPath)) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('Not found'); return }
    filePath = join(DIST, 'index.html')
  }
  const ext = extname(filePath)
  const size = statSync(filePath).size
  const headers = {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : urlPath.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'public, max-age=3600',
    'Accept-Ranges': 'bytes',
  }
  // A video is fetched in pieces (Safari will not play one otherwise, and seeking needs it), so
  // a Range request gets just the bytes it asked for.
  const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range ?? '')
  if (range && (range[1] || range[2])) {
    const start = range[1] ? Number(range[1]) : Math.max(0, size - Number(range[2]))
    const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1
    if (start >= size || start > end) { res.writeHead(416, { 'Content-Range': `bytes */${size}` }); res.end(); return }
    res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1 })
    createReadStream(filePath, { start, end }).pipe(res)
    return
  }
  res.writeHead(200, { ...headers, 'Content-Length': size })
  createReadStream(filePath).pipe(res)
}).listen(PORT, () => console.log(`Paskall website listening on :${PORT}`))

// Last line of defence. Everything above is meant to answer rather than throw, but a handler
// that throws must not be able to take the site down with it — the failure mode is an outage
// for every screen and every customer, from one bad request.
process.on('uncaughtException', (err) => {
  console.error('uncaught exception, staying up:', err)
})
process.on('unhandledRejection', (err) => {
  console.error('unhandled rejection, staying up:', err)
})
