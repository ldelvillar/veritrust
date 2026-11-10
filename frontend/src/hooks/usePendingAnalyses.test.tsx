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

type PendingResponse = { count: number; newest_analysis_id: string | null };
type QueryOptions = { onSuccess?: (latest: PendingResponse) => void };

const refetch = vi.fn(async () => {});
let response: PendingResponse | null;
let queryOptions: QueryOptions;

// Simulate a successful poll, updating data and firing onSuccess as SWR would.
const emit = (
  rerender: () => void,
  count: number,
  newestId: string | null = null
) => {
  response = { count, newest_analysis_id: newestId };
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

  it('does not flag finished without a previous pending analysis', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 0);

    expect(result.current.finished).toBeNull();
  });

  it('clears the finished notice on dismiss', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, 'abc');
    emit(rerender, 0);

    act(() => result.current.dismissFinished());

    expect(result.current.finished).toBeNull();
  });

  it('auto-dismisses the finished notice after 20 seconds', () => {
    const { result, rerender } = renderHook(() => usePendingAnalyses());
    emit(rerender, 1, 'abc');
    emit(rerender, 0);
    expect(result.current.finished).not.toBeNull();

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(result.current.finished).toBeNull();
  });
});
