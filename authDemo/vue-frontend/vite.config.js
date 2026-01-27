import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // Allow access via IP
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:9306',
        changeOrigin: true
      }
    }
  }
})
