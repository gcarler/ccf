import { expect, test } from '@playwright/test';
import {
  getPlatformApiBaseUrl,
  installPlatformAuthSession,
  preloadPlatformAccessTokens,
  requirePlatformAuthE2E,
} from './authSession';
import { installRuntimeGuards, waitForStableRoute } from './runtimeGuards';

type SmokeRoute = {
  id: string;
  path: string;
  expectedText: RegExp;
};

type AuthenticatedModuleSmokeOptions = {
  suiteName: string;
  tag: string;
  routes: readonly SmokeRoute[];
};

export function defineAuthenticatedModuleRouteSmoke({
  suiteName,
  tag,
  routes,
}: AuthenticatedModuleSmokeOptions) {
  test.describe(suiteName, () => {
    requirePlatformAuthE2E();
    test.setTimeout(60_000);

    test.beforeAll(async ({ request }) => {
      await preloadPlatformAccessTokens(request);
    });

    test.beforeEach(async ({ page }) => {
      await installPlatformAuthSession(page);
    });

    for (const route of routes) {
      test(`@auth ${tag} ${route.id} loads without runtime regressions`, async ({ page }) => {
        const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());

        await waitForStableRoute(page, route.path);
        await expect(page.locator('body')).toContainText(route.expectedText, { timeout: 15_000 });

        expect(runtime.assetErrors, `${route.path} should not emit _next/static 4xx/5xx`).toEqual([]);
        expect(runtime.apiErrors, `${route.path} should not emit API 4xx/5xx`).toEqual([]);
        expect(runtime.pageErrors, `${route.path} should not emit page errors`).toEqual([]);
        expect(runtime.consoleErrors, `${route.path} should not emit console.error`).toEqual([]);
      });
    }
  });
}
