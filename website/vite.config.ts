import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss(), Icons({ compiler: 'vue3', scale: 1 })],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { port: 5175 },
})
