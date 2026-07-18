import { defineConfig, devices } from '@playwright/test';

const port = Number(process.env.PLAYWRIGHT_PORT || 4173);
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${port}`;
const useManagedWebServer =
  process.env.PLAYWRIGHT_MANAGED_WEBSERVER === '1' && !process.env.PLAYWRIGHT_BASE_URL;
const reuseManagedWebServer = process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER === '1';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: useManagedWebServer
    ? {
        command: `npm run start -- -p ${port}`,
        url: `${baseURL}/login`,
        reuseExistingServer: reuseManagedWebServer,
        timeout: 120000,
        gracefulShutdown: {
          signal: 'SIGTERM',
          timeout: 5000,
        },
      }
    : undefined,
});
