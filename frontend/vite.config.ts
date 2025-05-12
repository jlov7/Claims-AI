import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const isPreview = command === 'preview';
  
  console.log(`[vite.config.ts] RUNNING CONFIGURATION`)
  console.log(`[vite.config.ts] Mode: ${mode}`)
  console.log(`[vite.config.ts] Command: ${command}`)
  console.log(`[vite.config.ts] isPreview: ${isPreview}`)
  console.log(`[vite.config.ts] Base path: ${isPreview ? '/claims-ai/' : '/'}`)

  return {
    plugins: [react()],
    base: isPreview ? '/claims-ai/' : '/',
    define: {
      'import.meta.env.APP_BASE': JSON.stringify(isPreview ? '/claims-ai/' : '/'),
      'import.meta.env.VITE_E2E_TESTING': JSON.stringify(process.env.VITE_E2E_TESTING),
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: 'src/setupTests.ts'
    }
  }
})
