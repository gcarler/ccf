import type { Page } from '@playwright/test';
import { installMockPlatformSession } from '../helpers/mockPlatformSession';

export const EVENT_ID = '11111111-1111-4111-8111-111111111111';
export const RESOURCES = [
  { id: '22222222-2222-4222-8222-222222222222', name: 'Sala de conferencias', resource_type: 'sala', capacity: 30, is_active: true },
  { id: '33333333-3333-4333-8333-333333333333', name: 'Proyector portátil', resource_type: 'equipo', capacity: 1, is_active: true },
];
export const RESERVATIONS = [{
  id: '44444444-4444-4444-8444-444444444444', event_id: EVENT_ID,
  resource_id: RESOURCES[0].id, starts_at: '2026-07-28T10:00:00.000Z', ends_at: '2026-07-28T12:00:00.000Z',
}];

export async function installOperationalMocks(page: Page) {
  await installMockPlatformSession(page, {
    role: 'admin', permissions: { 'agenda:read': 'allow', 'agenda:edit': 'allow' },
  });
  await page.route(`**/api/agenda/events/${EVENT_ID}`, (route) => route.fulfill({ json: {
    id: EVENT_ID, title: 'Reunión de equipo', start_at: '2026-07-28T10:00:00.000Z',
    end_at: '2026-07-28T12:00:00.000Z', is_all_day: false, location: 'Templo',
  } }));
  await page.route('**/api/agenda/resources', (route) => route.fulfill({ json: RESOURCES }));
  await page.route(`**/api/agenda/events/${EVENT_ID}/reservations`, (route) => route.fulfill({ json: RESERVATIONS }));
}
