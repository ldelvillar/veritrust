import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useAllAnalysesDeletion } from './useAllAnalysesDeletion';

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('@/hooks/usePendingAnalyses', () => ({
  refreshPendingAnalyses: vi.fn(),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn() };
});

const mockedFetch = vi.mocked(fetchJsonWithAuth);
const mockedRefresh = vi.mocked(refreshPendingAnalyses);

describe('useAllAnalysesDeletion', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
    mockedRefresh.mockReset();
  });

  it('refreshes the pending indicator after deleting every analysis', async () => {
    mockedFetch.mockResolvedValueOnce({ status: 'deleted', deleted_count: 3 });

    const { result } = renderHook(() => useAllAnalysesDeletion());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.removeAll();
    });

    expect(outcome).toBe(true);
    expect(mockedRefresh).toHaveBeenCalledTimes(1);
  });

  it('leaves the pending indicator alone when the delete fails', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('network down'));

    const { result } = renderHook(() => useAllAnalysesDeletion());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.removeAll();
    });

    expect(outcome).toBe(false);
    expect(mockedRefresh).not.toHaveBeenCalled();
  });
});
