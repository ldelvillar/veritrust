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
    // Sin seguir redirecciones: /app/* redirige al login de Clerk y eso cuenta como válido.
    const response = await request.get(href || '/', { maxRedirects: 0 });
    expect(response.status(), href).toBeLessThan(400);
  }
});

test('the demo request form confirms the request', async ({ page }) => {
  await page.goto('/demo');
  await page.getByLabel('Nombre').fill('Ana Pérez');
  await page.getByLabel('Email profesional').fill('ana@example.org');
  await page.getByLabel('Organización').fill('Diario de Salud');
  // El radio es sr-only y su etiqueta lo tapa: se marca pulsando el texto, como un usuario.
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
