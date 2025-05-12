import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isE2ETesting = env.VITE_E2E_TESTING === 'true'
  const basePath = isE2ETesting ? '/' : '/claims-ai/'

  console.log(`[vite.config.ts] RUNNING CONFIGURATION`)
  console.log(`[vite.config.ts] Mode: ${mode}`)
  console.log(`[vite.config.ts] VITE_E2E_TESTING from env: ${env.VITE_E2E_TESTING}`)
  console.log(`[vite.config.ts] isE2ETesting variable: ${isE2ETesting}`)
  console.log(`[vite.config.ts] Determined base path: ${basePath}`)

  return {
    plugins: [react()],
    base: basePath,
    define: {
      'import.meta.env.VITE_E2E_TESTING': JSON.stringify(env.VITE_E2E_TESTING),
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: 'src/setupTests.ts'
    }
  }
})
