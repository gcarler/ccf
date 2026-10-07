import { expect, test } from '@playwright/test';

const projectId = '00000000-0000-4000-8000-000000000071';
const taskId = '00000000-0000-4000-8000-000000000072';
const notificationId = '00000000-0000-4000-8000-000000000073';

test('Projects mention notification opens its project task and marks itself read', async ({ page }) => {
  const mutations: string[] = [];
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;

    if (request.method() !== 'GET') {
      mutations.push(`${request.method()} ${pathname}`);
      if (request.method() === 'PATCH' && pathname === `/api/messaging/notifications/${notificationId}`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: notificationId,
            persona_id: '00000000-0000-4000-8000-000000000074',
            title: 'Te mencionaron en un comentario',
            content: 'Revisemos esto',
            target_url: `/plataforma/projects/${projectId}?task=${taskId}`,
            is_read: true,
            created_at: '2026-10-05T10:00:00Z',
          }),
        });
        return;
      }
      await route.fulfill({ status: 405, body: 'Unexpected mutating request in read-only E2E' });
      return;
    }

    let body: unknown = [];
    if (pathname.endsWith('/v3/auth/me')) {
      body = {
        auth_user_id: 'comment-mention-e2e-user',
        username: 'comment.mention.e2e',
        email: 'comment.mention.e2e@ccf.local',
        platform_role: 'GESTOR',
        is_verified: true,
        permissions: { 'projects:read': 'allow', 'messaging:read': 'allow' },
      };
    } else if (pathname === '/api/messaging/notifications') {
      body = [{
        id: notificationId,
        persona_id: '00000000-0000-4000-8000-000000000074',
        title: 'Te mencionaron en un comentario',
        content: 'Revisemos esto',
        target_url: `/plataforma/projects/${projectId}?task=${taskId}`,
        is_read: false,
        created_at: '2026-10-05T10:00:00Z',
      }];
    } else if (pathname === `/api/projects/${projectId}`) {
      body = {
        id: projectId,
        title: 'Proyecto de mención',
        status: 'active',
        tasks: [{ id: taskId, project_id: projectId, title: 'Tarea abierta desde la mención', status: 'todo' }],
        milestones: [],
      };
    } else if (pathname.endsWith('/workspace/config')) {
      body = {};
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('ccf_token', 'comment-mention-e2e-token');
    sessionStorage.setItem('ccf_refresh_token', 'comment-mention-e2e-refresh');
  });

  await page.goto('/plataforma/inbox', { waitUntil: 'domcontentloaded' });
  const notification = page.getByRole('button').filter({ hasText: 'Te mencionaron en un comentario' });
  await expect(notification).toBeVisible();
  await notification.click();

  await expect(page).toHaveURL(`/plataforma/projects/${projectId}?task=${taskId}`);
  await expect(page.getByText('Tarea abierta desde la mención')).toBeVisible();
  expect(mutations).toEqual([`PATCH /api/messaging/notifications/${notificationId}`]);
});
