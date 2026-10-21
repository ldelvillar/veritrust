import { expect, test } from './fixtures';

// El mock termina cada análisis encolado como falso a los pocos segundos.
const FINISHED_VERDICT = { name: 'Contenido falso' } as const;
const PIPELINE_TIMEOUT = { timeout: 15_000 } as const;

test('a submitted text opens its report, which shows the verdict once the pipeline finishes', async ({
  page,
}) => {
  await page.goto('/app/analisis');
  await page
    .getByLabel('Pega el texto o la afirmación a verificar')
    .fill('El consumo diario de vitamina C previene el resfriado común.');
  await page.getByRole('button', { name: 'Analizar credibilidad' }).click();

  await expect(page).toHaveURL(/\/app\/analisis\/[0-9a-f-]{36}$/);
  await expect(
    page.getByText('El informe aparecerá aquí en cuanto termine el análisis')
  ).toBeVisible();
  const recent = page
    .getByRole('complementary')
    .getByRole('link', { name: /El consumo diario de vitamina C/ });
  await expect(recent).toContainText('En curso');
  await expect(page.getByRole('heading', FINISHED_VERDICT)).toBeVisible(
    PIPELINE_TIMEOUT
  );
  // El menú no sondea: el fin del análisis le llega por el indicador de pendientes.
  await expect(recent).toContainText('Falso', PIPELINE_TIMEOUT);
});

test('a failed analysis can be retried until it finishes', async ({ page }) => {
  await page.goto('/app/analisis/failed-connection');
  await page.getByRole('button', { name: 'Reintentar análisis' }).click();

  await expect(
    page.getByText('El informe aparecerá aquí en cuanto termine el análisis')
  ).toBeVisible();
  await expect(page.getByRole('heading', FINISHED_VERDICT)).toBeVisible(
    PIPELINE_TIMEOUT
  );
});

test('an unknown analysis id shows the not-found page', async ({ page }) => {
  await page.goto('/app/analisis/does-not-exist');

  await expect(
    page.getByRole('heading', {
      name: 'No hay nada que analizar en esta dirección',
    })
  ).toBeVisible();
});
