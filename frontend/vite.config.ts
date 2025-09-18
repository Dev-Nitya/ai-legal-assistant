import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Use the standard Vite port
    host: true, // This allows external access if needed
    open: true,  // This will automatically open the browser
    proxy: {
      // Proxy API requests to the backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
