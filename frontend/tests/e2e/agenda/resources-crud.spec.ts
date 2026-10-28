import { expect, test } from '@playwright/test';
import { EVENT_ID, installOperationalMocks } from './operational-fixtures';

test.describe('Resources read contract @agenda', () => {
  test.beforeEach(async ({ page }) => {
    await installOperationalMocks(page);
    await page.goto(`/plataforma/agenda/events/${EVENT_ID}`);
  });

  test('displays resource inventory on the owning Agenda detail', async ({ page }) => {
    const resources = page.getByRole('region', { name: 'Recursos disponibles', exact: true });
    await expect(resources.getByText('Sala de conferencias', { exact: true })).toBeVisible();
    await expect(resources.getByText('Proyector portátil', { exact: true })).toBeVisible();
    await expect(resources.getByRole('listitem')).toHaveCount(2);
  });

  test('shows canonical resource type and capacity', async ({ page }) => {
    const resources = page.getByRole('region', { name: 'Recursos disponibles', exact: true });
    await expect(resources.getByText('sala', { exact: true })).toBeVisible();
    await expect(resources.getByText('equipo', { exact: true })).toBeVisible();
    await expect(resources.getByText('Capacidad: 30', { exact: true })).toBeVisible();
    await expect(resources.getByText('Capacidad: 1', { exact: true })).toBeVisible();
  });
});
