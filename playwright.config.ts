import { defineConfig, devices } from '@playwright/test';

// Check if running in E2E mode (e.g., set by a specific script or env var)
const isE2ETesting = process.env.E2E_TESTING === 'true';

console.log(`[Playwright Config] E2E_TESTING env var: ${process.env.E2E_TESTING}`);
console.log(`[Playwright Config] isE2ETesting variable: ${isE2ETesting}`);

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/reporting */
  reporter: 'list',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5178/claims-ai/',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    // Pass the E2E flag to the browser context
    launchOptions: {
      // Consider adding slowMo for debugging if needed: slowMo: 50, 
      env: {
        VITE_E2E_TESTING: 'true'
      }
    },

    // Set the environment variable for the browser context
    // This makes import.meta.env.VITE_E2E_TESTING available in the frontend code
    // Make sure the key matches exactly what Vite expects (VITE_...)
    serviceWorkers: 'block', // Often needed for reliable testing
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    // Command to start the dev server
    command: 'cd frontend && pnpm dev --port 5178',
    // URL to wait for before starting tests
    url: 'http://localhost:5178/claims-ai/',
    // Reuse existing server if running locally, start fresh in CI
    reuseExistingServer: false,
    // Set env var for the web server process itself
    env: {
      VITE_E2E_TESTING: 'true'
    },
    stdout: 'pipe', 
    stderr: 'pipe',
    timeout: 120 * 1000, // Increase timeout for server start
  },

  // Increase default timeout (default is 30s)
  timeout: 60 * 1000, // 60 seconds
  expect: {
    // Increase default expect timeout (default is 5s)
    timeout: 15 * 1000, // 15 seconds
  },
}); 