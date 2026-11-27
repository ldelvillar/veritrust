import { defineConfig } from '@playwright/test';

import { LIVE_RUN_WAIT_MS } from './e2e/constants';
import base from './playwright.config';

const [setup, authenticated] = base.projects ?? [];

// Drives the real compose stack, which the verify skill starts, instead of the mock API and a fresh build.
export default defineConfig({
  ...base,
  webServer: undefined,
  retries: 0,
  timeout: LIVE_RUN_WAIT_MS + 60_000,
  use: { ...base.use, baseURL: 'http://localhost:3000' },
  projects: [
    setup,
    { ...authenticated, name: 'live', testMatch: /\.live\.ts/ },
  ],
});
