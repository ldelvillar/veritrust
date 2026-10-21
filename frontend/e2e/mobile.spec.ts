import { E2E_USER_EMAIL } from './constants';
import { expect, test } from './fixtures';

test.use({ viewport: { width: 390, height: 844 } });

test('the mobile menu shows the navigation and the signed-in account', async ({
  page,
}) => {
  await page.goto('/app/analisis');
  await page.getByRole('button', { name: 'Abrir menú' }).click();

  // La barra lateral de escritorio sigue en el DOM, oculta; solo el drawer es un complementary visible.
  const drawer = page.getByRole('complementary');
  await expect(
    drawer.getByRole('link', { name: 'Análisis anteriores' })
  ).toBeVisible();
  await expect(drawer.getByText(E2E_USER_EMAIL)).toBeVisible();
});
