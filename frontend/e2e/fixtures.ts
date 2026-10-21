import { test as base, expect } from '@playwright/test';

import { MOCK_API_URL } from './constants';

// Cada prueba parte de los datos sembrados del mock; como el estado es compartido, se corre con un solo worker.
export const test = base.extend<{ resetMockApi: void }>({
  resetMockApi: [
    async ({ request }, use) => {
      const response = await request.post(`${MOCK_API_URL}/__reset`);
      expect(response.ok()).toBe(true);
      await use();
    },
    { auto: true },
  ],
});

export { expect };
