import { expect, test, type APIRequestContext } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from '../helpers/authSession';

const apiBaseUrl = getPlatformApiBaseUrl();
const TEST_ARTIFACT_PREFIX = 'e2e-delete-';
const TINY_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

async function cleanPreviousTestArtifacts(
  request: APIRequestContext,
  headers: Record<string, string>,
) {
  const response = await request.get(
    `${apiBaseUrl}/api/cms/media?query=${encodeURIComponent(TEST_ARTIFACT_PREFIX)}&include_archived=true&limit=500`,
    { headers },
  );
  if (!response.ok()) return;

  const payload = (await response.json()) as {
    items?: Array<{ id?: string; filename?: string }>;
  };
  for (const item of payload.items ?? []) {
    if (!item.id || !item.filename?.startsWith(TEST_ARTIFACT_PREFIX)) continue;
    const permanentCleanup = await request.delete(
      `${apiBaseUrl}/api/cms/media/${item.id}?permanent=true`,
      { headers },
    );
    if (!permanentCleanup.ok()) {
      await request.delete(`${apiBaseUrl}/api/cms/media/${item.id}`, { headers });
    }
  }
}

test.describe('CMS media live deletion', () => {
  requirePlatformAuthE2E();
  test.setTimeout(90_000);

  test.beforeAll(async ({ request }) => {
    await preloadPlatformAccessTokens(request);
  });

  test.beforeEach(async ({ page }) => {
    await installPlatformAuthSession(page);
  });

  test('@auth @cms verifies permanent media deletion through the real API', async ({ page, request }) => {
    // addInitScript runs on a document navigation, so establish the real
    // platform document before reading the token from sessionStorage.
    await page.goto('/plataforma/cms/media', { waitUntil: 'domcontentloaded' });
    const accessToken = await page.evaluate(() => sessionStorage.getItem('ccf_token'));
    expect(accessToken, 'The authenticated E2E session must expose an access token').toBeTruthy();

    const headers = {
      Authorization: `Bearer ${accessToken}`,
      Accept: 'application/json',
    };
    await cleanPreviousTestArtifacts(request, headers);
    const filename = `${TEST_ARTIFACT_PREFIX}${Date.now()}-${Math.random().toString(16).slice(2)}.png`;
    let mediaId: string | undefined;

    try {
      const uploadResponse = await request.post(`${apiBaseUrl}/api/cms/media/upload`, {
        headers,
        multipart: {
          file: {
            name: filename,
            mimeType: 'image/png',
            buffer: TINY_PNG,
          },
          alt_text: filename,
          section: 'e2e-test',
          tags: 'e2e,cleanup',
          optimize: 'false',
        },
      });
      expect(uploadResponse.ok(), await uploadResponse.text()).toBeTruthy();
      expect(uploadResponse.status()).toBe(201);
      mediaId = (await uploadResponse.json()).id as string;
      expect(mediaId).toBeTruthy();

      await page.reload({ waitUntil: 'domcontentloaded' });
      const search = page.getByPlaceholder(/Buscar archivos/i);
      await expect(search).toBeVisible();
      await search.fill(filename);

      const mediaCard = page.locator('div.group.relative.aspect-square').first();
      await expect(mediaCard).toBeVisible({ timeout: 20_000 });
      await mediaCard.hover();
      await mediaCard.getByRole('button', { name: 'Eliminar', exact: true }).click();

      const confirmationModal = page.locator('div.fixed.inset-0').filter({
        hasText: '¿Eliminar permanentemente?',
      });
      await expect(confirmationModal).toBeVisible();

      const deleteResponsePromise = page.waitForResponse((response) => {
        return (
          response.request().method() === 'DELETE' &&
          response.url().includes(`/api/cms/media/${mediaId}?permanent=true`)
        );
      });
      await confirmationModal.getByRole('button', { name: 'Eliminar', exact: true }).click();
      const deleteResponse = await deleteResponsePromise;
      expect(deleteResponse.status(), await deleteResponse.text()).toBe(204);

      const verifyResponse = await request.get(`${apiBaseUrl}/api/cms/media/${mediaId}`, { headers });
      expect(verifyResponse.status()).toBe(404);
    } finally {
      if (mediaId) {
        const remainingResponse = await request.get(`${apiBaseUrl}/api/cms/media/${mediaId}`, { headers });
        if (remainingResponse.ok()) {
          const permanentCleanup = await request.delete(
            `${apiBaseUrl}/api/cms/media/${mediaId}?permanent=true`,
            { headers },
          );
          // If an older deployment still rejects the local storage URL, at
          // least archive the temporary row so it does not remain active.
          if (!permanentCleanup.ok()) {
            await request.delete(`${apiBaseUrl}/api/cms/media/${mediaId}`, { headers });
          }
        }
      }
    }
  });
});
