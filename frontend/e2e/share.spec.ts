import { expect, test } from './fixtures';

test('a shared report opens for a visitor without an account', async ({
  page,
  browser,
}) => {
  await page.goto('/app/analisis/done-fake');
  await page.getByRole('button', { name: 'Compartir' }).click();
  const dialog = page.getByRole('dialog', { name: 'Compartir informe' });
  await dialog.getByRole('button', { name: 'Crear enlace público' }).click();
  const link = dialog.getByLabel('Enlace público');
  await expect(link).toHaveValue(/\/r\/.+/);
  const shareUrl = await link.inputValue();

  const visitor = await browser.newContext({
    storageState: { cookies: [], origins: [] },
  });
  const visitorPage = await visitor.newPage();
  await visitorPage.goto(shareUrl);

  await expect(
    visitorPage.getByRole('heading', { name: 'Contenido falso' })
  ).toBeVisible();
  // La vista pública no enlaza a /app/*, que exige cuenta.
  await expect(
    visitorPage.getByRole('link', { name: 'Analizar otro contenido' })
  ).toHaveCount(0);
  await visitor.close();
});

test.describe('on the Free plan', () => {
  test.use({ mockPlan: { plan: 'free', used: 0 } });

  test('sharing offers the upgrade instead of a public link', async ({
    page,
  }) => {
    await page.goto('/app/analisis/done-fake');
    await page.getByRole('button', { name: 'Compartir' }).click();
    const dialog = page.getByRole('dialog', { name: 'Compartir informe' });

    await expect(
      dialog.getByText('Los enlaces públicos son del plan Pro.')
    ).toBeVisible();
    await expect(
      dialog.getByRole('button', { name: 'Crear enlace público' })
    ).toHaveCount(0);
  });
});
