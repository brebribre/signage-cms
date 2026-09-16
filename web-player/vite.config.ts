import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitest/config'

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))

export default defineConfig({
  define: {
    // Reported to the CMS as the screen's app version, prefixed so a web screen can never be
    // mistaken for an Android build number.
    __PLAYER_VERSION__: JSON.stringify(`web-${pkg.version}`),
  },
  build: {
    // Smart TV browsers run Chromium several years old (Tizen 5 is Chromium 69, webOS 5 is 68).
    // Syntax is lowered to what they parse; nothing here needs a runtime polyfill.
    target: 'es2017',
    rollupOptions: {
      // Two pages: the shell a screen opens (index.html, holds full screen) and the player it
      // frames (player.html) — see src/shell.ts.
      input: {
        shell: fileURLToPath(new URL('./index.html', import.meta.url)),
        player: fileURLToPath(new URL('./player.html', import.meta.url)),
      },
    },
  },
  server: {
    port: 5174,
    // Same shape as production's server.mjs: the player calls /api on its own origin.
    proxy: {
      '/api': { target: 'http://localhost:8001', rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
