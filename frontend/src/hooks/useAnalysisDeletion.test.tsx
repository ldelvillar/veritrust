import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { useAnalysisDeletion } from './useAnalysisDeletion';

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

describe('useAnalysisDeletion', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
    mockedRefresh.mockReset();
  });

  it('refreshes the pending indicator after deleting an analysis', async () => {
    mockedFetch.mockResolvedValueOnce({
      status: 'deleted',
      analysis_id: 'abc',
    });

    const { result } = renderHook(() => useAnalysisDeletion());

    await act(async () => {
      await result.current.remove('abc');
    });

    expect(mockedRefresh).toHaveBeenCalledTimes(1);
  });

  it('leaves the pending indicator alone when the delete fails', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('network down'));

    const { result } = renderHook(() => useAnalysisDeletion());

    await act(async () => {
      await result.current.remove('abc');
    });

    expect(mockedRefresh).not.toHaveBeenCalled();
  });

  it('returns true and issues a DELETE on success', async () => {
    mockedFetch.mockResolvedValueOnce({
      status: 'deleted',
      analysis_id: 'abc',
    });

    const { result } = renderHook(() => useAnalysisDeletion());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.remove('abc');
    });

    expect(outcome).toBe(true);
    expect(result.current.error).toBeNull();
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.any(Function),
      '/analysis/abc',
      { method: 'DELETE' }
    );
  });

  it('returns false and surfaces the ApiError message on failure', async () => {
    mockedFetch.mockRejectedValueOnce(
      new ApiError('Análisis no encontrado.', 'ANALYSIS_NOT_FOUND', 404)
    );

    const { result } = renderHook(() => useAnalysisDeletion());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.remove('missing');
    });

    expect(outcome).toBe(false);
    await waitFor(() =>
      expect(result.current.error).toBe('Análisis no encontrado.')
    );
  });

  it('returns false with a connection message for a non-ApiError throw', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('network down'));

    const { result } = renderHook(() => useAnalysisDeletion());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.remove('abc');
    });

    expect(outcome).toBe(false);
    await waitFor(() => expect(result.current.error).toMatch(/Sin conexión/));
  });
});
