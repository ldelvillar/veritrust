import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/apiClient';
import { fetchJsonServer } from '@/lib/serverApi';
import AnalisisPage from './page';

vi.mock('@/lib/serverApi', () => ({ fetchJsonServer: vi.fn() }));
vi.mock('./AnalisisClient', () => ({ default: () => null }));
vi.mock('next/navigation', () => ({
  notFound: () => {
    throw new Error('NEXT_NOT_FOUND');
  },
}));

const params = Promise.resolve({ id: 'some-id' });

describe('AnalisisPage', () => {
  it.each([404, 400])(
    'renders not-found when the API answers %i',
    async status => {
      vi.mocked(fetchJsonServer).mockRejectedValue(
        new ApiError('x', null, status)
      );

      await expect(AnalisisPage({ params })).rejects.toThrow('NEXT_NOT_FOUND');
    }
  );

  it('leaves any other API error to the error boundary', async () => {
    const error = new ApiError('x', 'INTERNAL', 500);
    vi.mocked(fetchJsonServer).mockRejectedValue(error);

    await expect(AnalisisPage({ params })).rejects.toBe(error);
  });
});
