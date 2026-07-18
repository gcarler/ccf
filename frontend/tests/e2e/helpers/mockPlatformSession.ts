import type { Page, Route } from '@playwright/test';

type MockPlatformSessionOptions = {
  role?: string;
  permissions?: Record<string, 'allow' | 'deny'>;
  accessToken?: string;
  refreshToken?: string;
};

export async function installMockPlatformSession(
  page: Page,
  {
    role = 'pastor',
    permissions = {
      'evangelism:read': 'allow',
      'evangelism:manage': 'allow',
    },
    accessToken = 'mock-e2e-token',
    refreshToken = 'mock-e2e-refresh',
  }: MockPlatformSessionOptions = {},
) {
  await page.addInitScript(
    ({ seededAccessToken, seededRefreshToken }) => {
      sessionStorage.setItem('ccf_token', seededAccessToken);
      sessionStorage.setItem('ccf_refresh_token', seededRefreshToken);
      localStorage.setItem('ccf_token', seededAccessToken);
      localStorage.setItem('ccf_refresh_token', seededRefreshToken);
    },
    {
      seededAccessToken: accessToken,
      seededRefreshToken: refreshToken,
    },
  );

  const authPayload = {
    auth_user_id: 'e2e-user',
    username: 'pastor.e2e',
    email: 'pastor.e2e@ccf.local',
    platform_role: role,
    is_verified: true,
    permissions,
  };

  const fulfillAuthMe = async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(authPayload),
    });
  };

  const fulfillRefresh = async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: accessToken,
        refresh_token: refreshToken,
      }),
    });
  };

  const fulfillLogout = async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  };

  await page.route('**/api/v3/auth/me**', fulfillAuthMe);
  await page.route('**/api/auth/v3/me**', fulfillAuthMe);
  await page.route('**/api/v3/auth/refresh**', fulfillRefresh);
  await page.route('**/api/auth/v3/refresh**', fulfillRefresh);
  await page.route('**/api/v3/auth/logout**', fulfillLogout);
  await page.route('**/api/auth/v3/logout**', fulfillLogout);
}
