import { E2E_USER_EMAIL } from './constants';
import { expect, test } from './fixtures';

test.use({ viewport: { width: 390, height: 844 } });

test('the mobile menu shows the navigation and the signed-in account', async ({
  page,
}) => {
  await page.goto('/app/analisis');
  await page.getByRole('button', { name: 'Abrir menú' }).click();

  // The desktop sidebar stays in the DOM, hidden, so only the drawer is a visible complementary.
  const drawer = page.getByRole('complementary');
  await expect(
    drawer.getByRole('link', { name: 'Análisis anteriores' })
  ).toBeVisible();
  await expect(drawer.getByText(E2E_USER_EMAIL)).toBeVisible();
  await drawer.getByRole('link', { name: 'Datos personales' }).click();
  await expect(page).toHaveURL(/\/app\/cuenta$/);
});

test('the mobile logo and the app index open a new analysis', async ({
  page,
}) => {
  await page.goto('/app/historial');
  await page.getByRole('link', { name: 'VeriTrust' }).click();
  await expect(page).toHaveURL(/\/app\/analisis$/);

  await page.goto('/app');
  await expect(page).toHaveURL(/\/app\/analisis$/);
});
