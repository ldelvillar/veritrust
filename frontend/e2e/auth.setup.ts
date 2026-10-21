import { clerk, clerkSetup } from '@clerk/testing/playwright';
import { expect, test as setup } from '@playwright/test';

import { AUTH_FILE, E2E_USER_EMAIL } from './constants';

// Crea el usuario de prueba en la instancia de desarrollo de Clerk si aún no existe.
async function ensureUser(email: string): Promise<void> {
  const api = `${process.env.CLERK_API_URL ?? 'https://api.clerk.com'}/v1/users`;
  const headers = {
    Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}`,
    'Content-Type': 'application/json',
  };
  const found = await fetch(
    `${api}?email_address=${encodeURIComponent(email)}`,
    { headers }
  );
  if (!found.ok) throw new Error(`Clerk user lookup: ${await found.text()}`);
  if (((await found.json()) as unknown[]).length > 0) return;

  const created = await fetch(api, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      email_address: [email],
      first_name: 'E2E',
      last_name: 'VeriTrust',
      skip_password_requirement: true,
    }),
  });
  if (!created.ok)
    throw new Error(`Clerk user create: ${await created.text()}`);
}

setup('sign in the e2e user', async ({ page }) => {
  await clerkSetup();
  await ensureUser(E2E_USER_EMAIL);

  await page.goto('/');
  await clerk.signIn({ page, emailAddress: E2E_USER_EMAIL });
  await page.goto('/app/historial');
  await expect(
    page.getByRole('heading', { name: 'Análisis anteriores' })
  ).toBeVisible();

  await page.context().storageState({ path: AUTH_FILE });
});
