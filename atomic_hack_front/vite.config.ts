import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5435,
    open: true
  },
  optimizeDeps: {
    include: ['react', 'react-dom']
  }
})
