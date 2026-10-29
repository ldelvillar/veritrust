import { expect, test } from './fixtures';

const ACTIVATION_TIMEOUT = { timeout: 15_000 } as const;

test.describe('on the Free plan', () => {
  test.use({ mockPlan: { plan: 'free', used: 4 } });

  test('the menu shows the plan and its usage, and the file tab is locked', async ({
    page,
  }) => {
    await page.goto('/app/analisis');

    // El análisis en curso sembrado reserva una unidad: 4 usados + 1 en curso.
    const menu = page.getByRole('complementary');
    await expect(menu.getByText('Gratis', { exact: true })).toBeVisible();
    await expect(menu.getByText('5 de 10 análisis este mes')).toBeVisible();

    await page.getByRole('tab', { name: /Archivo/ }).click();
    await expect(page.getByText('Analiza archivos con Pro')).toBeVisible();
    await expect(page.getByText(/Arrastra un archivo/)).toHaveCount(0);
  });

  test('subscribing goes through Checkout and waits for Pro to activate', async ({
    page,
  }) => {
    await page.goto('/app/cuenta');
    await page.getByRole('button', { name: 'Hazte Pro' }).click();

    const plan = page.getByRole('region', { name: 'Tu plan' });
    await expect(plan.getByText('Activando tu plan Pro…')).toBeVisible();
    // El resultado se quita de la URL: recargar no repite el aviso.
    await expect(page).toHaveURL(/\/app\/cuenta#plan$/);
    await expect(
      plan.getByText('¡Ya tienes el plan Pro! Gracias por suscribirte.')
    ).toBeVisible(ACTIVATION_TIMEOUT);
    await expect(
      plan.getByRole('button', { name: 'Gestionar suscripción' })
    ).toBeVisible();
  });

  test('the dashboard shows the upsell instead of the metrics', async ({
    page,
  }) => {
    await page.goto('/app/dashboard');

    await expect(
      page.getByRole('heading', { name: 'El dashboard es del plan Pro' })
    ).toBeVisible();
  });

  test('an analysis older than 30 days shows the upsell', async ({ page }) => {
    await page.goto('/app/analisis/done-old');

    await expect(
      page.getByRole('heading', { name: 'Este análisis tiene más de 30 días' })
    ).toBeVisible();
  });
});

test.describe('with the Free Allowance used up', () => {
  test.use({ mockPlan: { plan: 'free', used: 9 } });

  test('the analysis form blocks submitting', async ({ page }) => {
    await page.goto('/app/analisis');
    await page
      .getByLabel('Pega el texto o la afirmación a verificar')
      .fill('El consumo diario de vitamina C previene el resfriado común.');

    await expect(
      page.getByRole('button', { name: 'Analizar credibilidad' })
    ).toBeDisabled();
    await expect(
      page.getByRole('heading', { name: 'Has usado tus análisis de este mes' })
    ).toBeVisible();
  });
});

test.describe('on the Pro plan', () => {
  test('the account page manages the subscription in the portal', async ({
    page,
  }) => {
    await page.goto('/app/cuenta');
    const plan = page.getByRole('region', { name: 'Tu plan' });
    await expect(plan.getByText('Facturación mensual')).toBeVisible();

    await plan.getByRole('button', { name: 'Gestionar suscripción' }).click();
    await expect(page).toHaveURL(/\/app\/cuenta\?portal=mock/);
  });

  test('the dashboard is unlocked', async ({ page }) => {
    await page.goto('/app/dashboard');

    await expect(
      page.getByRole('heading', { name: 'Aún no hay nada que medir' })
    ).toBeVisible();
  });
});
