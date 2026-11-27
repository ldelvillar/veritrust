import { expect, test } from '@playwright/test';

import { LIVE_RUN_WAIT_MS } from './constants';

// The headline of each of the four Verdicts, from getVerdictInfo.
const VERDICT_HEADLINE =
  /Contenido (verdadero|falso|parcialmente falso|dudoso)/;

test('a submitted claim runs through the real pipeline and opens its report', async ({
  page,
}) => {
  await page.goto('/app/analisis');
  await page
    .getByLabel('Pega el texto o la afirmación a verificar')
    .fill('El consumo diario de vitamina C previene el resfriado común.');
  await page.getByRole('button', { name: 'Analizar credibilidad' }).click();
  await expect(page).toHaveURL(/\/app\/analisis\/[0-9a-f-]{36}$/);

  const verdict = page.getByRole('heading', { name: VERDICT_HEADLINE });
  const failed = page.getByText('No se pudo completar el análisis');
  // Waits for whichever ending the Run reaches, so a failed Run ends the test at once.
  await expect(verdict.or(failed)).toBeVisible({ timeout: LIVE_RUN_WAIT_MS });
  await expect(failed).toBeHidden();
});
