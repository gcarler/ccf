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
  /** Optional patterns for console.error messages that are acceptable for this route. */
  allowedConsolePatterns?: readonly RegExp[];
};

type AuthenticatedModuleSmokeOptions = {
  suiteName: string;
  tag: string;
  routes: readonly SmokeRoute[];
  /** Optional extra hooks to run in beforeEach, after auth session is installed. */
  onBeforeEach?: Array<(page: import('@playwright/test').Page) => Promise<void>>;
};

export function defineAuthenticatedModuleRouteSmoke({
  suiteName,
  tag,
  routes,
  onBeforeEach,
}: AuthenticatedModuleSmokeOptions) {
  test.describe(suiteName, () => {
    requirePlatformAuthE2E();
    test.setTimeout(60_000);

    test.beforeAll(async ({ request }) => {
      await preloadPlatformAccessTokens(request);
    });

    test.beforeEach(async ({ page }) => {
      await installPlatformAuthSession(page);
      if (onBeforeEach) {
        for (const hook of onBeforeEach) {
          await hook(page);
        }
      }
    });

    for (const route of routes) {
      test(`@auth ${tag} ${route.id} loads without runtime regressions`, async ({ page }) => {
        const runtime = installRuntimeGuards(page, getPlatformApiBaseUrl());

        await waitForStableRoute(page, route.path);
        await expect(page.locator('body')).toContainText(route.expectedText, { timeout: 15_000 });

        expect(runtime.assetErrors, `${route.path} should not emit _next/static 4xx/5xx`).toEqual([]);
        expect(runtime.apiErrors, `${route.path} should not emit API 4xx/5xx`).toEqual([]);
        expect(runtime.pageErrors, `${route.path} should not emit page errors`).toEqual([]);

        // Filter console errors against allowed patterns (e.g., non-critical timeouts)
        const allowed = route.allowedConsolePatterns || [];
        const filteredErrors = runtime.consoleErrors.filter(
          (err) => !allowed.some((pattern) => pattern.test(err)),
        );
        expect(filteredErrors, `${route.path} should not emit console.error`).toEqual([]);
      });
    }
  });
}
