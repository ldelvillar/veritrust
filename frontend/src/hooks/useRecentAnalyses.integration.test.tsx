import { act, renderHook, waitFor } from '@testing-library/react';
import { mutate } from 'swr';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useApiQuery } from '@/hooks/useApiQuery';
import {
  refreshHistory,
  refreshHistoryLists,
  refreshPending,
} from '@/lib/historyCache';
import { PENDING_HISTORY_PATH, RECENT_HISTORY_PATH } from '@/lib/historyQuery';
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
let newestId: string | null = null;

const callsFor = (path: string) =>
  mockedFetch.mock.calls.filter(([, key]) => key === path).length;

// Los helpers usan el mutate global, así que cada test arranca con la caché por defecto vacía.
describe('history lists refresh (SWR real)', () => {
  beforeEach(async () => {
    // Sin hooks montados, mutate sin datos solo borra las peticiones deduplicadas del test anterior.
    await mutate(() => true);
    await mutate(() => true, undefined, { revalidate: false });
    pendingCount = 0;
    newestId = null;
    mockedFetch.mockReset();
    mockedFetch.mockImplementation(async (_getToken, path) =>
      path === PENDING_HISTORY_PATH
        ? { count: pendingCount, newest_analysis_id: newestId }
        : { items: [] }
    );
  });

  it('refreshHistoryLists refetches the lists and leaves other keys alone', async () => {
    renderHook(() => {
      usePendingAnalyses();
      useRecentAnalyses();
      useApiQuery(OTHER_PATH);
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    const pendingBefore = callsFor(PENDING_HISTORY_PATH);
    const otherBefore = callsFor(OTHER_PATH);

    await act(async () => {
      await refreshHistoryLists();
    });

    expect(callsFor(RECENT_HISTORY_PATH)).toBe(2);
    expect(callsFor(PENDING_HISTORY_PATH)).toBe(pendingBefore);
    expect(callsFor(OTHER_PATH)).toBe(otherBefore);
  });

  it('a change in the pending summary refreshes the lists once', async () => {
    const { result } = renderHook(() => {
      useRecentAnalyses();
      return usePendingAnalyses();
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    await waitFor(() =>
      expect(callsFor(PENDING_HISTORY_PATH)).toBeGreaterThan(0)
    );

    pendingCount = 1;
    newestId = 'aaa';
    await act(async () => {
      await refreshPending();
    });

    await waitFor(() => expect(result.current.pendingCount).toBe(1));
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(2));
    // Margen para que un segundo refresco, si lo hubiera, llegue a contarse.
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });
    expect(callsFor(RECENT_HISTORY_PATH)).toBe(2);
  });

  it('an own action that changes the pending summary fetches the lists once', async () => {
    renderHook(() => {
      useRecentAnalyses();
      usePendingAnalyses();
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    await waitFor(() =>
      expect(callsFor(PENDING_HISTORY_PATH)).toBeGreaterThan(0)
    );

    pendingCount = 1;
    newestId = 'aaa';
    await act(async () => {
      await refreshHistory();
    });
    // Margen para que el refresco que dispara el indicador, si lo hubiera, llegue a contarse.
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    expect(callsFor(RECENT_HISTORY_PATH)).toBe(2);
  });

  it('an own action the pending summary misses still refreshes the lists', async () => {
    renderHook(() => {
      useRecentAnalyses();
      usePendingAnalyses();
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    await waitFor(() =>
      expect(callsFor(PENDING_HISTORY_PATH)).toBeGreaterThan(0)
    );

    await act(async () => {
      await refreshHistory();
    });

    expect(callsFor(RECENT_HISTORY_PATH)).toBe(2);
  });

  it('an unchanged pending summary leaves the lists alone', async () => {
    renderHook(() => {
      useRecentAnalyses();
      usePendingAnalyses();
    });
    await waitFor(() => expect(callsFor(RECENT_HISTORY_PATH)).toBe(1));
    await waitFor(() =>
      expect(callsFor(PENDING_HISTORY_PATH)).toBeGreaterThan(0)
    );

    await act(async () => {
      await refreshPending();
    });

    expect(callsFor(RECENT_HISTORY_PATH)).toBe(1);
  });
});
