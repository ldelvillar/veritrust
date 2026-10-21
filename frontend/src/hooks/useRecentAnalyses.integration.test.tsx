import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useApiQuery } from '@/hooks/useApiQuery';
import { refreshHistory } from '@/lib/historyCache';
import { RECENT_HISTORY_PATH } from '@/lib/historyQuery';
import { usePendingAnalyses } from './usePendingAnalyses';
import { useRecentAnalyses } from './useRecentAnalyses';

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ isSignedIn: true, getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn() };
});

vi.mock('next/navigation', () => ({
  usePathname: () => '/app/analisis',
}));

import { fetchJsonWithAuth } from '@/lib/apiClient';
const mockedFetch = vi.mocked(fetchJsonWithAuth);

const OTHER_PATH = '/dashboard/summary';
let pendingCount = 0;
let recentStatus: 'pending' | 'done' = 'done';

const callsFor = (path: string) =>
  mockedFetch.mock.calls.filter(([, key]) => key === path).length;

// Sin proveedor propio: refreshHistory usa el mutate global sobre la caché por defecto.
describe('recent analyses refresh (SWR real)', () => {
  beforeEach(() => {
    pendingCount = 0;
    recentStatus = 'done';
    mockedFetch.mockReset();
    mockedFetch.mockImplementation(async (_getToken, path) => {
      if (path === '/history/pending')
        return { count: pendingCount, newest_analysis_id: 'aaa' };
      return { items: [{ status: recentStatus }] };
    });
  });

  it('refreshHistory refetches every /history key and leaves the rest alone', async () => {
    renderHook(() => {
      usePendingAnalyses();
      useRecentAnalyses();
      useApiQuery(OTHER_PATH);
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    const pendingBefore = callsFor('/history/pending');
    const otherBefore = callsFor(OTHER_PATH);

    await act(async () => {
      await refreshHistory();
    });

    expect(callsFor(RECENT_HISTORY_PATH)).toBe(2);
    expect(callsFor('/history/pending')).toBeGreaterThan(pendingBefore);
    expect(callsFor(OTHER_PATH)).toBe(otherBefore);
  });

  it('polls the recents only while one of them is in progress', async () => {
    vi.useFakeTimers();
    try {
      recentStatus = 'pending';
      renderHook(() => useRecentAnalyses());
      await act(async () => {
        await refreshHistory();
      });
      const whilePending = callsFor(RECENT_HISTORY_PATH);

      recentStatus = 'done';
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000);
      });
      const afterFinish = callsFor(RECENT_HISTORY_PATH);
      expect(afterFinish).toBeGreaterThan(whilePending);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000);
      });
      expect(callsFor(RECENT_HISTORY_PATH)).toBe(afterFinish);
    } finally {
      vi.useRealTimers();
    }
  });
});
