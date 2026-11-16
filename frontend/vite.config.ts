import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    // Same-origin in dev so the HttpOnly refresh cookie works without CORS.
    proxy: { '/api': { target: process.env.API_URL || 'http://127.0.0.1:5000', changeOrigin: false } },
  },
})
