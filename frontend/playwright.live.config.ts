import { existsSync } from 'node:fs';
import { join } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

import { AUTH_FILE } from './e2e/constants';

// Clerk's development keys come from frontend/.env, as in the mock-backed config.
const envFile = join(__dirname, '.env');
if (existsSync(envFile)) process.loadEnvFile(envFile);

// The compose stack's pipeline budget (ANALYSIS_JOB_TIMEOUT_SECONDS) bounds every wait.
const PIPELINE_BUDGET_MS = 15 * 60_000;

// Drives the real compose stack, which the verify skill starts, so there is no webServer here.
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  timeout: PIPELINE_BUDGET_MS + 60_000,
  expect: { timeout: PIPELINE_BUDGET_MS },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'live',
      testMatch: /\.live\.ts/,
      use: { ...devices['Desktop Chrome'], storageState: AUTH_FILE },
      dependencies: ['setup'],
    },
  ],
});
