import { test as base, expect } from '@playwright/test';

import { MOCK_API_URL } from './constants';

// Plan seeded in the mock, Pro by default with the whole app available.
export interface MockPlan {
  plan: 'free' | 'pro';
  used: number;
}

// Each test starts from the mock's seeded data, and since the state is shared it runs on a single worker.
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
