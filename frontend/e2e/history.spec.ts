import { expect, test } from './fixtures';

test('a verdict card filters the history and keeps the filter in the URL', async ({
  page,
}) => {
  await page.goto('/app/historial');
  await page.getByRole('button', { name: /Falsos$/ }).click();

  await expect(page).toHaveURL(/verdict=fake/);
  const rows = page.getByRole('main').getByRole('listitem');
  await expect(rows).toHaveCount(1);
  await expect(rows).toContainText('vitamina C en dosis altas');
});

test.describe('on the Free plan', () => {
  test.use({ mockPlan: { plan: 'free', used: 0 } });

  test('the history shows the last 30 days with its tools locked', async ({
    page,
  }) => {
    await page.goto('/app/historial?verdict=fake');

    await expect(page.getByText(/Mostrando los últimos 30 días/)).toBeVisible();
    await expect(
      page.getByPlaceholder('Buscar por título o fuente…')
    ).toBeDisabled();
    await expect(page.getByRole('button', { name: /Falsos$/ })).toBeDisabled();
    // The filtered URL never reaches the API, so the default query is listed, without anything older than 30 days.
    const rows = page.getByRole('main').getByRole('listitem');
    await expect(rows).toHaveCount(5);
    await expect(rows.filter({ hasText: 'Caminar a diario' })).toHaveCount(0);
  });
});
