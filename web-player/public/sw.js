// Keeps the player itself available with no network, so a screen that reboots while the venue's
// router is still coming up opens straight into its cached loop — the web counterpart of an
// installed APK. Media is not handled here; src/mediaCache.ts keeps its own cache.
//
// Network first for everything, falling back to the last copy: a deploy is picked up the
// moment it's reachable, and nothing stale is served while the network is fine.

const SHELL = 'fortu-shell-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.add('/')).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('fortu-shell-') && k !== SHELL).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)
  // The API and the deploy check must always be live; other origins are not ours to cache.
  if (req.method !== 'GET' || url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/') || url.pathname === '/version.json') return

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone()
          // Every navigation is the same SPA shell, so it is kept under one key.
          caches.open(SHELL).then((cache) => cache.put(req.mode === 'navigate' ? '/' : req, copy))
        }
        return res
      })
      .catch(() =>
        caches.match(req.mode === 'navigate' ? '/' : req).then((hit) => hit || Response.error()),
      ),
  )
})
