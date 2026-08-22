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
  await page.goto('/plataforma/projects?view=list#projects-dashboard');
  await expect(page.locator('body')).toContainText(projectName, { timeout: 15_000 });
  const projectLink = page
    .locator('a[href^="/plataforma/projects/"]')
    .filter({ hasText: projectName })
    .first();
  await expect(projectLink).toBeVisible({ timeout: 15_000 });
  await projectLink.click();
  // The detail view preserves the ?view= query param (ProjectsLayoutClient
  // links to /plataforma/projects/<uuid>?view=list), so accept an optional
  // query string after the project id.
  await expect(page).toHaveURL(/\/plataforma\/projects\/[0-9a-f-]{36}(\?.*)?$/);
  return new URL(page.url()).pathname;
}
