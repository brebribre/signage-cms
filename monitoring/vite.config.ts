import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    // Icons compile to components at build time — nothing is fetched at runtime, and only
    // the icons actually referenced are bundled.
    Icons({ compiler: 'vue3', scale: 1 }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // 5173 is the CMS, 5174 the web player, 5175 the website — see .claude/launch.json.
    port: 5176,
    // Bound to the IPv4 loopback by name, not `localhost`: the CMS dev server is opened as
    // `localhost`, and cookies ignore ports but not hosts, so 127.0.0.1 keeps this app's
    // session separate from the CMS's in the same browser. (Plain `localhost` can also resolve
    // to ::1 only, leaving 127.0.0.1 unanswered.)
    host: '127.0.0.1',
    // The app only ever calls `/api/...` on its own origin, in dev exactly as in production
    // (where server.mjs does this): the session cookie is then first-party everywhere, and
    // the backend needs no CORS entry for this app at all.
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL || 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
