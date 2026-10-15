import { existsSync } from 'node:fs';
import { join } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

import {
  AUTH_FILE,
  MOCK_API_PORT,
  MOCK_API_URL,
  WEB_PORT,
  WEB_URL,
} from './e2e/constants';

// Las claves de Clerk de desarrollo salen de frontend/.env en local y de los secretos en CI.
const envFile = join(__dirname, '.env');
if (existsSync(envFile)) process.loadEnvFile(envFile);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: WEB_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: AUTH_FILE },
      dependencies: ['setup'],
    },
  ],
  webServer: [
    {
      command: 'node e2e/mock-api.mts',
      url: `${MOCK_API_URL}/config`,
      env: { MOCK_API_PORT: String(MOCK_API_PORT), WEB_ORIGIN: WEB_URL },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `pnpm build && pnpm start --port ${WEB_PORT}`,
      url: `${WEB_URL}/robots.txt`,
      env: {
        NEXT_PUBLIC_API_URL: MOCK_API_URL,
        INTERNAL_API_URL: MOCK_API_URL,
      },
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
