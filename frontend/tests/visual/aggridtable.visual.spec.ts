import { test, expect, type Page } from '@playwright/test';

/**
 * Visual regression tests for AgGridTable stories.
 *
 * These tests assume Storybook is running or has been built and served at
 * the baseURL configured in playwright.visual.config.ts.
 */

// Story IDs are derived from the title and export names in
// src/components/ui/AgGridTable.stories.tsx. If the story title or export
// names change, these IDs must be updated to match Storybook's slugification.
const STORY_IDS = {
  light: 'ui-aggridtable--light-mode',
  dark: 'ui-aggridtable--dark-mode',
  selected: 'ui-aggridtable--selected-row',
};

async function waitForGrid(page: Page) {
  // Wait for the grid container and at least one rendered row so snapshots
  // capture the fully populated table rather than a loading/empty state.
  await page.waitForSelector('.ag-root-wrapper .ag-row', { timeout: 10000 });
}

function storyUrl(storyId: string) {
  return `/iframe.html?id=${storyId}&viewMode=story`;
}

test.describe('AgGridTable visual regression', () => {
  test('renders correctly in light mode', async ({ page }) => {
    await page.goto(storyUrl(STORY_IDS.light));
    await waitForGrid(page);
    await expect(page).toHaveScreenshot('aggrid-light.png', { fullPage: true, animations: 'disabled' });
  });

  test('renders correctly in dark mode', async ({ page }) => {
    await page.goto(storyUrl(STORY_IDS.dark));
    await waitForGrid(page);
    await expect(page).toHaveScreenshot('aggrid-dark.png', { fullPage: true, animations: 'disabled' });
  });

  test('renders selected row correctly', async ({ page }) => {
    await page.goto(storyUrl(STORY_IDS.selected));
    await waitForGrid(page);
    await expect(page).toHaveScreenshot('aggrid-selected.png', { fullPage: true, animations: 'disabled' });
  });
});
