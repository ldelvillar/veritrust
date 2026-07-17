import { StrictMode, type ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  refreshPendingAnalyses,
  usePendingAnalyses,
} from './usePendingAnalyses';

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ isSignedIn: true, getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn() };
});

let pathname = '/app/analisis';
vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
}));

import { fetchJsonWithAuth } from '@/lib/apiClient';
const mockedFetch = vi.mocked(fetchJsonWithAuth);

let serverCount = 0;
let serverItems: { analysis_id: string }[] = [];

// Caché SWR aislada por test; el dev server de Next corre en StrictMode.
const wrapper = ({ children }: { children: ReactNode }) => (
  <StrictMode>
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  </StrictMode>
);

describe('usePendingAnalyses (SWR real)', () => {
  beforeEach(() => {
    pathname = '/app/analisis';
    serverCount = 0;
    serverItems = [];
    mockedFetch.mockReset();
    mockedFetch.mockImplementation(async () => ({
      status: 'success',
      items: serverItems,
      count: serverCount,
    }));
  });

  it('poll alone picks up a second analysis without navigation', async () => {
    vi.useFakeTimers();
    try {
      serverCount = 1;
      serverItems = [{ analysis_id: 'aaa' }];
      const { result } = renderHook(() => usePendingAnalyses(), { wrapper });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(50);
      });
      expect(result.current.pendingCount).toBe(1);
      const callsAfterMount = mockedFetch.mock.calls.length;

      serverCount = 2;
      serverItems = [{ analysis_id: 'bbb' }];
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_100);
      });

      expect(mockedFetch.mock.calls.length).toBeGreaterThan(callsAfterMount);
      expect(result.current.pendingCount).toBe(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it('refreshPendingAnalyses updates the indicator without navigation or poll', async () => {
    serverCount = 1;
    serverItems = [{ analysis_id: 'aaa' }];
    // Sin proveedor propio: el mutate global de refreshPendingAnalyses opera sobre la caché por defecto.
    const { result } = renderHook(() => usePendingAnalyses(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <StrictMode>{children}</StrictMode>
      ),
    });
    await waitFor(() => expect(result.current.pendingCount).toBe(1));

    serverCount = 2;
    serverItems = [{ analysis_id: 'bbb' }];
    await act(async () => {
      await refreshPendingAnalyses();
    });

    await waitFor(() => expect(result.current.pendingCount).toBe(2));
    expect(result.current.newestPendingId).toBe('bbb');
  });

  it('full lifecycle: A pending, A done, then B and C pending', async () => {
    serverCount = 1;
    serverItems = [{ analysis_id: 'aaa' }];
    const { result, rerender } = renderHook(() => usePendingAnalyses(), {
      wrapper,
    });
    await waitFor(() => expect(result.current.pendingCount).toBe(1));

    // A termina: el sondeo devuelve 0 y el aviso de finalizado aparece.
    serverCount = 0;
    serverItems = [];
    pathname = '/app/historial';
    rerender();
    await waitFor(() => expect(result.current.pendingCount).toBe(0));
    expect(result.current.finished).toEqual({ analysisId: 'aaa' });

    // Se envía B.
    serverCount = 1;
    serverItems = [{ analysis_id: 'bbb' }];
    pathname = '/app/analisis/bbb';
    rerender();
    await waitFor(() => expect(result.current.pendingCount).toBe(1));
    expect(result.current.finished).toBeNull();

    // Se envía C con B aún en curso.
    serverCount = 2;
    serverItems = [{ analysis_id: 'ccc' }];
    pathname = '/app/analisis/ccc';
    rerender();
    await waitFor(() => expect(result.current.pendingCount).toBe(2));
    expect(result.current.newestPendingId).toBe('ccc');
  });
});
