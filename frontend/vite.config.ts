import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'vendor-vue',
              test: /node_modules[\\/](vue|vue-router|pinia|@vue)[\\/]/,
              priority: 30,
            },
            {
              name: 'vendor-element-plus',
              test: /node_modules[\\/](element-plus|@element-plus)[\\/]/,
              priority: 20,
            },
            {
              name: 'vendor-http',
              test: /node_modules[\\/]axios[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8051',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8051',
        changeOrigin: true,
      },
    },
  },
})
