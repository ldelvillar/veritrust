import { expect, test } from './fixtures';

test('deleting all activity empties the history and clears the pending indicator', async ({
  page,
}) => {
  await page.goto('/app/cuenta');
  const pendingIndicator = page.getByRole('link', {
    name: '1 análisis en curso',
  });
  await expect(pendingIndicator).toBeVisible();

  await page
    .getByRole('button', { name: /Eliminar toda mi actividad/ })
    .click();
  const dialog = page.getByRole('dialog', {
    name: '¿Eliminar toda tu actividad?',
  });
  await dialog
    .getByLabel('Escribe ELIMINAR para confirmar la eliminación total')
    .fill('ELIMINAR');
  await dialog.getByRole('button', { name: 'Eliminar todo' }).click();

  await expect(
    page.getByText('No tienes actividad que eliminar.')
  ).toBeVisible();
  await expect(pendingIndicator).toBeHidden();

  await page.goto('/app/historial');
  await expect(page.getByText('Aún no has analizado nada')).toBeVisible();
});
