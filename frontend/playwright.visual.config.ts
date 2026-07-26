import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for visual regression tests against Storybook.
 *
 * It builds Storybook once and serves the static files on port 6006.
 * Tests navigate to the isolated iframe of each story and use
 * `toHaveScreenshot` to compare against baselines.
 */
const storybookPort = Number(process.env.STORYBOOK_PORT || 6006);
const storybookBaseUrl = `http://localhost:${storybookPort}`;

export default defineConfig({
  testDir: './tests/visual',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  snapshotPathTemplate: '{testDir}/{testFilePath}-snapshots/{arg}{ext}',
  use: {
    baseURL: storybookBaseUrl,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npx http-server storybook-static -p ${storybookPort} --silent`,
    url: storybookBaseUrl,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
