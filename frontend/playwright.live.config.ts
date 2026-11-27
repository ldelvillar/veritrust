import { defineConfig } from '@playwright/test';

import { LIVE_RUN_WAIT_MS } from './e2e/constants';
import base from './playwright.config';

function baseProject(name: string) {
  const project = base.projects?.find(candidate => candidate.name === name);
  if (!project)
    throw new Error(`playwright.config.ts has no '${name}' project`);
  return project;
}

// Drives the real compose stack, which the verify skill starts, instead of the mock API and a fresh build.
export default defineConfig({
  ...base,
  webServer: undefined,
  retries: 0,
  timeout: LIVE_RUN_WAIT_MS + 60_000,
  // The real Clerk, API and database answer slower than the mock, most of all right after the stack starts.
  expect: { timeout: 30_000 },
  use: { ...base.use, baseURL: 'http://localhost:3000' },
  projects: [
    baseProject('setup'),
    { ...baseProject('chromium'), name: 'live', testMatch: /\.live\.ts/ },
  ],
});
