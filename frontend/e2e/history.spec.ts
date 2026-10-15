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
