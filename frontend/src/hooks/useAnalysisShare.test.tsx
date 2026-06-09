import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { useAnalysisShare } from './useAnalysisShare';

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn() };
});

const mockedFetch = vi.mocked(fetchJsonWithAuth);

describe('useAnalysisShare', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it('returns the token and POSTs to the share endpoint on create', async () => {
    mockedFetch.mockResolvedValueOnce({
      status: 'shared',
      share_token: 'tok_abc',
    });

    const { result } = renderHook(() => useAnalysisShare());

    let token: string | null | undefined;
    await act(async () => {
      token = await result.current.createShare('abc');
    });

    expect(token).toBe('tok_abc');
    expect(result.current.error).toBeNull();
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.any(Function),
      '/analysis/abc/share',
      { method: 'POST' }
    );
  });

  it('returns null and surfaces the ApiError message when create fails', async () => {
    mockedFetch.mockRejectedValueOnce(
      new ApiError(
        'Solo se pueden compartir los análisis completados.',
        'ANALYSIS_NOT_SHAREABLE',
        409
      )
    );

    const { result } = renderHook(() => useAnalysisShare());

    let token: string | null | undefined;
    await act(async () => {
      token = await result.current.createShare('abc');
    });

    expect(token).toBeNull();
    await waitFor(() =>
      expect(result.current.error).toMatch(/Solo se pueden compartir/)
    );
  });

  it('returns true and issues a DELETE on remove', async () => {
    mockedFetch.mockResolvedValueOnce({
      status: 'unshared',
      analysis_id: 'abc',
    });

    const { result } = renderHook(() => useAnalysisShare());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.removeShare('abc');
    });

    expect(outcome).toBe(true);
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.any(Function),
      '/analysis/abc/share',
      { method: 'DELETE' }
    );
  });

  it('returns false with a connection message for a non-ApiError throw', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('network down'));

    const { result } = renderHook(() => useAnalysisShare());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.removeShare('abc');
    });

    expect(outcome).toBe(false);
    await waitFor(() => expect(result.current.error).toMatch(/Sin conexión/));
  });
});
