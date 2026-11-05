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

test('a Pro user sees the MCP server address and the setup steps', async ({
  page,
}) => {
  await page.goto('/app/cuenta');
  const card = page.getByRole('region', { name: 'Conecta tu asistente de IA' });

  await expect(card.getByText(/\/mcp$/).first()).toBeVisible();
  await card.getByText('Claude Code', { exact: true }).click();
  await expect(card.getByText('claude mcp add --transport http')).toBeVisible();
  await expect(card.getByText('verify_claim')).toBeVisible();
});

test.describe('on the Free plan', () => {
  test.use({ mockPlan: { plan: 'free', used: 0 } });

  test('a Free user is offered the Pro plan instead of the MCP setup', async ({
    page,
  }) => {
    await page.goto('/app/cuenta');
    const card = page.getByRole('region', {
      name: 'Conecta tu asistente de IA',
    });

    await expect(card.getByText(/función del plan Pro/)).toBeVisible();
    await expect(card.getByText('verify_claim')).toBeHidden();
    await card.getByRole('link', { name: 'Ver el plan Pro' }).click();
    await expect(page).toHaveURL(/#plan$/);
  });

  test('exporting my data downloads every analysis, hidden ones included', async ({
    page,
  }) => {
    await page.goto('/app/cuenta');
    const download = page.waitForEvent('download');
    await page
      .getByRole('button', { name: 'Exportar todos mis datos' })
      .click();

    const file = await download;
    expect(file.suggestedFilename()).toBe('veritrust-mis-datos.csv');
    const csv = await (await file.createReadStream()).toArray();
    expect(Buffer.concat(csv).toString('utf8')).toContain('done-old');
  });
});
