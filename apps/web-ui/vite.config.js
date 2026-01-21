import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 9300,
    proxy: {
      '/api/v1/ingest': {
        target: 'http://localhost:9305',
        changeOrigin: true,
      },
      '/api/v1/documents': {
        target: 'http://localhost:9305',
        changeOrigin: true,
      },
      '/api/v1/search': {
        target: 'http://localhost:9305',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:9301',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
