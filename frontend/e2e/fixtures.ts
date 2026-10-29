import { test as base, expect } from '@playwright/test';

import { MOCK_API_URL } from './constants';

// Plan sembrado en el mock; por defecto Pro, con toda la app disponible.
export interface MockPlan {
  plan: 'free' | 'pro';
  used: number;
}

// Cada prueba parte de los datos sembrados del mock; como el estado es compartido, se corre con un solo worker.
export const test = base.extend<{ mockPlan: MockPlan; resetMockApi: void }>({
  mockPlan: [{ plan: 'pro', used: 0 }, { option: true }],
  resetMockApi: [
    async ({ request, mockPlan }, use) => {
      const query = new URLSearchParams({
        plan: mockPlan.plan,
        used: String(mockPlan.used),
      });
      const response = await request.post(`${MOCK_API_URL}/__reset?${query}`);
      expect(response.ok()).toBe(true);
      await use();
    },
    { auto: true },
  ],
});

export { expect };
