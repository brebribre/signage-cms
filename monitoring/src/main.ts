import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
// Bundled with the app, not fetched from a font service — same as frontend/.
import '@fontsource-variable/inter'
import '@fontsource-variable/outfit'
import './style.css'

/**
 * Recovering from a deploy that happened while this tab was open. Routes are lazy imports with
 * content-hashed names; a tab loaded before a deploy asks for a chunk that no longer exists and
 * gets a 404 (server.mjs). The only fix is a reload, which is safe here: nothing in this app
 * holds unsaved state across a route change. Once per cooldown, so a genuinely missing chunk
 * shows its error instead of looping.
 */
const RELOAD_MARKER = 'chunk-reload-at'
const RELOAD_COOLDOWN_MS = 30_000

function reloadForNewBuild() {
  let last = 0
  try {
    last = Number(sessionStorage.getItem(RELOAD_MARKER) ?? 0)
    sessionStorage.setItem(RELOAD_MARKER, String(Date.now()))
  } catch {
    // Storage blocked: a single reload is still better than a dead tab.
  }
  if (Date.now() - last < RELOAD_COOLDOWN_MS) return
  window.location.reload()
}

const isStaleChunk = (error: unknown) =>
  /dynamically imported module|Importing a module script failed|error loading dynamically imported module/i
    .test(String(error))

window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  reloadForNewBuild()
})

router.onError((error) => {
  if (isStaleChunk(error)) reloadForNewBuild()
})

createApp(App).use(createPinia()).use(router).mount('#app')
