import { expect, test } from './fixtures';

test.use({ storageState: { cookies: [], origins: [] } });

test('every internal link on the landing page leads to a page that exists', async ({
  page,
  request,
}) => {
  await page.goto('/');
  const hrefs = await page
    .locator('a[href^="/"]')
    .evaluateAll(links => [
      ...new Set(links.map(link => link.getAttribute('href')!.split('#')[0])),
    ]);

  expect(hrefs.length).toBeGreaterThan(0);
  for (const href of hrefs) {
    // Without following redirects, since /app/* redirects to Clerk's login and that counts as valid.
    const response = await request.get(href || '/', { maxRedirects: 0 });
    expect(response.status(), href).toBeLessThan(400);
  }
});

test('the header sign-in button opens our sign-in page, which links to sign-up', async ({
  page,
}) => {
  await page.goto('/');
  await page
    .getByRole('navigation', { name: 'Principal' })
    .getByRole('button', { name: 'Iniciar sesión' })
    .click();

  await expect(page).toHaveURL(/\/iniciar-sesion/);
  await expect(
    page.getByRole('heading', { name: /Iniciar sesión/ })
  ).toBeVisible();

  await page.getByRole('link', { name: 'Regístrate' }).click();
  await expect(page).toHaveURL(/\/registro/);
  await expect(
    page.getByRole('heading', { name: /Crea tu cuenta/ })
  ).toBeVisible();
});

test('a protected page sends a signed-out visitor to our sign-in page', async ({
  page,
}) => {
  await page.goto('/app/historial');
  await expect(page).toHaveURL(/\/iniciar-sesion/);
});

test('the demo request form confirms the request', async ({ page }) => {
  await page.goto('/demo');
  await page.getByLabel('Nombre').fill('Ana Pérez');
  await page.getByLabel('Email profesional').fill('ana@example.org');
  await page.getByLabel('Organización').fill('Diario de Salud');
  // The radio is sr-only and its label covers it, so it is checked by clicking the text, like a user.
  await page
    .getByRole('radiogroup', { name: 'Tipo de equipo' })
    .getByText('Salud pública')
    .click();
  await expect(
    page.getByRole('radio', { name: 'Salud pública' })
  ).toBeChecked();
  await page
    .getByRole('checkbox', { name: /Acepto que VeriTrust trate mis datos/ })
    .check();
  await page.getByRole('button', { name: 'Solicitar demo' }).click();

  await expect(
    page.getByRole('heading', { name: '¡Solicitud recibida!' })
  ).toBeVisible();
});
