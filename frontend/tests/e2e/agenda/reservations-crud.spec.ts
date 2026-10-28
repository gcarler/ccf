import { expect, test } from '@playwright/test';
import { EVENT_ID, installOperationalMocks } from './operational-fixtures';

test.describe('Reservations read contract @agenda', () => {
  test.beforeEach(async ({ page }) => {
    await installOperationalMocks(page);
    await page.goto(`/plataforma/agenda/events/${EVENT_ID}`);
  });

  test('displays the reserved resource on the owning Agenda detail', async ({ page }) => {
    const reservations = page.getByRole('region', { name: 'Reservas del evento', exact: true });
    await expect(reservations.getByText('Sala de conferencias', { exact: true })).toBeVisible();
    await expect(reservations.getByRole('listitem')).toHaveCount(1);
  });

  test('shows the reservation time range', async ({ page }) => {
    const reservations = page.getByRole('region', { name: 'Reservas del evento', exact: true });
    await expect(reservations.getByText('10:00', { exact: true })).toBeVisible();
    await expect(reservations.getByText('12:00', { exact: true })).toBeVisible();
  });
});
