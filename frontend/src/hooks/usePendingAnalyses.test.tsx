import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePendingAnalyses } from './usePendingAnalyses';

const { useApiQueryMock } = vi.hoisted(() => ({ useApiQueryMock: vi.fn() }));

vi.mock('@/hooks/useApiQuery', () => ({
  useApiQuery: useApiQueryMock,
}));

let isSignedIn: boolean;
vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ isSignedIn }),
}));

let pathname: string;
vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
}));

type PendingResponse = { count: number; items: { analysis_id: string }[] };
type QueryOptions = { onSuccess?: (latest: PendingResponse) => void };

const refetch = vi.fn(async () => {});
let response: PendingResponse | null;
let queryOptions: QueryOptions;

// Simula un sondeo exitoso: actualiza data y dispara onSuccess como haría SWR.
const emit = (rerender: () => void, count: number, ids: string[] = []) => {
  response = { count, items: ids.map(id => ({ analysis_id: id })) };
  act(() => queryOptions.onSuccess?.(response!));
  rerender();
};

describe('usePendingAnalyses', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    isSignedIn = true;
    pathname = '/app/dashboard';
    response = null;
    queryOptions = {};
    refetch.mockClear();
    useApiQueryMock.mockReset();
    useApiQueryMock.mockImplementation(
      (_path: string | null, options: QueryOptions) => {
        queryOptions = options;
        return { data: response, isLoading: false, error: null, refetch };
      }
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('disables the query while signed out', () => {
    isSignedIn = false;
    renderHook(() => usePendingAnalyses());

    expect(useApiQueryMock).toHaveBeenCalledWith(null, expect.any(Object));
  });

  it('exposes the pending count and the newest pending id', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 2, ['abc']);

    expect(useApiQueryMock).toHaveBeenCalledWith(
      '/history?status=pending&page_size=1',
      expect.any(Object)
    );
    expect(result.current.pendingCount).toBe(2);
    expect(result.current.newestPendingId).toBe('abc');
    expect(result.current.finished).toBeNull();
  });

  it('refetches when the route changes', () => {
    const { rerender } = renderHook(() => usePendingAnalyses());
    const initialCalls = refetch.mock.calls.length;

    pathname = '/app/historial';
    rerender();

    expect(refetch.mock.calls.length).toBe(initialCalls + 1);
  });

  it('flags the analysis as finished when pending drops to zero', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, ['abc']);
    expect(result.current.finished).toBeNull();

    emit(rerender, 0);

    expect(result.current.pendingCount).toBe(0);
    expect(result.current.finished).toEqual({ analysisId: 'abc' });
  });

  it('does not flag finished without a previous pending analysis', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 0);

    expect(result.current.finished).toBeNull();
  });

  it('clears the finished notice on dismiss', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, ['abc']);
    emit(rerender, 0);

    act(() => result.current.dismissFinished());

    expect(result.current.finished).toBeNull();
  });

  it('clears the finished notice when a new analysis starts', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, ['abc']);
    emit(rerender, 0);

    emit(rerender, 1, ['def']);

    expect(result.current.finished).toBeNull();
    expect(result.current.pendingCount).toBe(1);
  });

  it('auto-dismisses the finished notice after 20 seconds', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, ['abc']);
    emit(rerender, 0);
    expect(result.current.finished).not.toBeNull();

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(result.current.finished).toBeNull();
  });
});
