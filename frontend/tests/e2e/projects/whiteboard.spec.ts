import { expect, test, type Page } from '@playwright/test';
import {
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';
import { openSeededProjectDetailPath, seedProjectsDemo } from '../helpers/projectsDemo';
import { installRuntimeGuards } from '../helpers/runtimeGuards';

test.describe('whiteboard editor e2e', () => {
  requirePlatformAuthE2E();
  test.setTimeout(90_000);

  test.beforeAll(async ({ request }) => {
    seedProjectsDemo();
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  /**
   * Opens the whiteboard route for the seeded demo project and waits for the
   * canvas to become interactive.
   */
  async function openWhiteboard(page: Page) {
    const detailPath = await openSeededProjectDetailPath(page);
    const projectId = detailPath.split('/').pop();
    if (!projectId) {
      throw new Error('Could not resolve seeded project id from detail path');
    }

    const whiteboardPath = `/plataforma/whiteboard/${projectId}`;
    await page.goto(whiteboardPath);

    await page.locator('canvas.whiteboard-canvas').waitFor({ state: 'visible', timeout: 15_000 });
    await expect(page.getByTestId('whiteboard-export-png')).toBeEnabled({ timeout: 15_000 });

    return { projectId, whiteboardPath };
  }

  /**
   * Wait until the whiteboard save request has been processed by the backend
   * and the UI badge reflects the saved state.
   */
  async function waitForWhiteboardSaved(page: Page) {
    const savePromise = page.waitForResponse((response) => {
      return response.url().includes('/whiteboard') && response.request().method() === 'POST' && response.status() < 400;
    }, { timeout: 10_000 });
    await savePromise;
    await expect(page.getByTestId('whiteboard-save-status')).toHaveText('Guardado', { timeout: 5_000 });
  }

  /**
   * Count how many layer items are currently rendered in the layers panel.
   */
  function getLayerCount(page: Page) {
    return page.getByTestId('whiteboard-layers').locator('button').count();
  }

  /**
   * Return the visible layer labels in the order they appear in the panel
   * (top-most object first).
   */
  async function getLayerLabels(page: Page): Promise<string[]> {
    const buttons = page.getByTestId('whiteboard-layers').locator('button');
    return buttons.allTextContents();
  }

  test('@auth @whiteboard can add text, format it, export, and survive reload', async ({ page }) => {
    const runtime = installRuntimeGuards(page);
    await openWhiteboard(page);

    // ── Add text object ─────────────────────────────────────────────────────
    await page.getByTestId('whiteboard-add-text').click();

    // A new text object is created at a fixed position; it should appear both
    // on the canvas and in the layers panel.
    const layersPanel = page.locator('aside');
    await expect(layersPanel.getByText('Nuevo texto', { exact: false })).toBeVisible({ timeout: 5_000 });

    // ── Apply bold and italic formatting ──────────────────────────────────────
    const boldButton = page.getByRole('button', { name: /Negrita/i });
    const italicButton = page.getByRole('button', { name: /Cursiva/i });

    await boldButton.click();
    await italicButton.click();

    // Verify the formatting buttons reflect the active state.
    await expect(boldButton).toHaveClass(/bg-\[hsl\(var\(--primary\)\)\]/);
    await expect(italicButton).toHaveClass(/bg-\[hsl\(var\(--primary\)\)\]/);

    // ── Export PNG / SVG / JSON ───────────────────────────────────────────────
    const pngPromise = page.waitForEvent('download');
    await page.getByTestId('whiteboard-export-png').click();
    const pngDownload = await pngPromise;
    expect(pngDownload.suggestedFilename()).toMatch(/\.png$/i);

    const svgPromise = page.waitForEvent('download');
    await page.getByTestId('whiteboard-export-svg').click();
    const svgDownload = await svgPromise;
    expect(svgDownload.suggestedFilename()).toMatch(/\.svg$/i);

    const jsonPromise = page.waitForEvent('download');
    await page.getByTestId('whiteboard-export-json').click();
    const jsonDownload = await jsonPromise;
    expect(jsonDownload.suggestedFilename()).toMatch(/\.json$/i);

    // ── Reload and verify persistence ───────────────────────────────────────
    await waitForWhiteboardSaved(page);
    await page.reload();

    await page.locator('canvas.whiteboard-canvas').waitFor({ state: 'visible', timeout: 15_000 });
    await expect(page.getByTestId('whiteboard-export-png')).toBeEnabled({ timeout: 15_000 });
    await expect(layersPanel.getByText('Nuevo texto', { exact: false })).toBeVisible({ timeout: 5_000 });

    // No runtime regressions should have happened during the whole flow.
    expect(runtime.assetErrors).toEqual([]);
    expect(runtime.apiErrors).toEqual([]);
    expect(runtime.pageErrors).toEqual([]);
    expect(runtime.consoleErrors).toEqual([]);
  });

  test('@auth @whiteboard can add shapes and layers are reflected in the panel', async ({ page }) => {
    const runtime = installRuntimeGuards(page);
    await openWhiteboard(page);

    const layersPanel = page.locator('aside');

    // Capture the initial layer labels so we can isolate the newly added ones.
    const initialLabels = await getLayerLabels(page);

    // Rect/Circle live inside the "Formas" submenu (v3 toolbar) — open it first.
    await page.getByTestId('whiteboard-open-shapes').click();
    await page.getByTestId('whiteboard-add-rect').click();
    // The demo board ships with starter objects (incl. a rect), so the regex
    // may match several layer rows — any match proves the new shape is there.
    await expect(layersPanel.getByText(/Rectángulo \d+/).first()).toBeVisible({ timeout: 5_000 });

    await page.getByTestId('whiteboard-open-shapes').click();
    await page.getByTestId('whiteboard-add-circle').click();
    await expect(layersPanel.getByText(/Círculo \d+/).first()).toBeVisible({ timeout: 5_000 });

    await page.getByTestId('whiteboard-add-text').click();
    await expect(layersPanel.getByText('Nuevo texto', { exact: false })).toBeVisible({ timeout: 5_000 });

    // The layer count should have increased.
    const layerCountAfter = await getLayerCount(page);
    expect(layerCountAfter).toBeGreaterThanOrEqual(3);

    // The panel renders layers top-to-bottom, and the most recently added
    // object sits on top. Isolate the new layers so the starter rectangle does
    // not interfere with the order assertions.
    const finalLabels = await getLayerLabels(page);
    const newLabels = finalLabels.filter((label) => !initialLabels.includes(label));

    expect(newLabels.length).toBeGreaterThanOrEqual(3);
    expect(newLabels[0]).toMatch(/Nuevo texto/);
    expect(newLabels[1]).toMatch(/Círculo/);
    expect(newLabels[2]).toMatch(/Rectángulo/);

    expect(runtime.assetErrors).toEqual([]);
    expect(runtime.apiErrors).toEqual([]);
    expect(runtime.pageErrors).toEqual([]);
    expect(runtime.consoleErrors).toEqual([]);
  });

  test('@auth @whiteboard can undo and redo object additions', async ({ page }) => {
    const runtime = installRuntimeGuards(page);
    await openWhiteboard(page);

    const layersPanel = page.locator('aside');

    // Capture the initial layer count after the starter objects are loaded.
    const initialLayerCount = await getLayerCount(page);

    // Add a new shape (open the "Formas" submenu first) and confirm it appears.
    await page.getByTestId('whiteboard-open-shapes').click();
    await page.getByTestId('whiteboard-add-rect').click();
    await expect(layersPanel.getByText(/Rectángulo \d+/).first()).toBeVisible({ timeout: 5_000 });
    expect(await getLayerCount(page)).toBe(initialLayerCount + 1);

    // Undo should remove the newly added rectangle.
    await page.getByTestId('whiteboard-undo').click();
    await expect.poll(async () => getLayerCount(page)).toBe(initialLayerCount);

    // Redo should restore the rectangle.
    await page.getByTestId('whiteboard-redo').click();
    await expect.poll(async () => getLayerCount(page)).toBe(initialLayerCount + 1);

    expect(runtime.assetErrors).toEqual([]);
    expect(runtime.apiErrors).toEqual([]);
    expect(runtime.pageErrors).toEqual([]);
    expect(runtime.consoleErrors).toEqual([]);
  });
});
