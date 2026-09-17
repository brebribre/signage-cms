import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
// Bundled with the app, not fetched from a font service: no third-party request, and no flash of
// the fallback face on a slow link. See the type note in style.css.
import '@fontsource-variable/inter'
import '@fontsource-variable/outfit'
import './style.css'

/**
 * Recovering from a deploy that happened while this tab was open.
 *
 * Every route is a lazy import, and the built chunks are content-hashed. A tab loaded before a
 * deploy still holds the old index.html, whose chunk names no longer exist on the server — the
 * next navigation asks for one, gets index.html back (the SPA fallback), and the browser
 * refuses it: "Expected a JavaScript-or-Wasm module script". There is nothing to retry, because
 * that file is genuinely gone; the page has to be reloaded to pick up the new index.html.
 *
 * Reloading is safe here: navigation is the only thing that triggers it, and nothing in this
 * app holds unsaved state across a route change — every editor saves explicitly, and the deploy
 * flow parks its draft in sessionStorage, which survives a reload.
 */
const RELOAD_MARKER = 'chunk-reload-at'
const RELOAD_COOLDOWN_MS = 30_000

function reloadForNewBuild() {
  // Once per cooldown, so a chunk that is genuinely missing (a bad deploy, a broken CDN) shows
  // its error instead of putting the tab in a reload loop.
  let last = 0
  try {
    last = Number(sessionStorage.getItem(RELOAD_MARKER) ?? 0)
    sessionStorage.setItem(RELOAD_MARKER, String(Date.now()))
  } catch {
    // Storage blocked (private mode): fall through and reload anyway — a single reload is
    // still better than a dead tab, and without storage there is no loop to detect.
  }
  if (Date.now() - last < RELOAD_COOLDOWN_MS) return
  window.location.reload()
}

const isStaleChunk = (error: unknown) =>
  /dynamically imported module|Importing a module script failed|error loading dynamically imported module/i
    .test(String(error))

// Vite's own signal for a failed chunk preload; preventDefault stops it also reaching onError.
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  reloadForNewBuild()
})

router.onError((error) => {
  if (isStaleChunk(error)) reloadForNewBuild()
})

createApp(App).use(createPinia()).use(router).mount('#app')
