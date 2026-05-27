import type { ReactNode } from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiQuery } from './useApiQuery';

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn() };
});

const mockedFetch = vi.mocked(fetchJsonWithAuth);

// Fresh SWR cache per render so results don't leak between tests.
const wrapper = ({ children }: { children: ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

describe('useApiQuery', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it('returns data and a null error on success', async () => {
    mockedFetch.mockResolvedValueOnce({ status: 'ready' });

    const { result } = renderHook(
      () => useApiQuery<{ status: string }>('/healthz'),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual({ status: 'ready' });
    expect(result.current.error).toBeNull();
  });

  it('preserves the typed ApiError (code intact) when the request fails', async () => {
    mockedFetch.mockRejectedValueOnce(
      new ApiError('No disponible', 'SERVICE_UNAVAILABLE', 503)
    );

    const { result } = renderHook(() => useApiQuery('/dashboard/summary'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).code).toBe('SERVICE_UNAVAILABLE');
    expect(result.current.data).toBeNull();
  });

  it('wraps a non-Error throw in a generic Error', async () => {
    mockedFetch.mockRejectedValueOnce('plain string failure');

    const { result } = renderHook(() => useApiQuery('/history'), { wrapper });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Error desconocido.');
  });

  it('does not fetch when the path is null', async () => {
    const { result } = renderHook(() => useApiQuery(null), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockedFetch).not.toHaveBeenCalled();
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
