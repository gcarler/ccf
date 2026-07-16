import { expect, type Page } from '@playwright/test';
import { spawnSync } from 'node:child_process';

export function seedProjectsDemo() {
  const result = spawnSync('node', ['tests/e2e/seed-projects-demo.mjs'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PROJECTS_DEMO_EMAIL: process.env.E2E_EMAIL || process.env.PROJECTS_DEMO_EMAIL || '',
    },
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(`[projects-demo] Seed failed: ${result.stderr || result.stdout || 'unknown error'}`);
  }
}

export async function openSeededProjectDetailPath(page: Page, projectName = 'Demo Proyecto 1') {
  await page.goto('/plataforma/projects?view=list#projects-list');
  await expect(page.locator('body')).toContainText(projectName, { timeout: 15_000 });
  await page.getByText(projectName, { exact: true }).first().click();
  await expect(page).toHaveURL(/\/plataforma\/projects\/[0-9a-f-]{36}$/);
  return new URL(page.url()).pathname;
}
