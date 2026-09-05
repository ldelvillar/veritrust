import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { useAnalysisSubmission } from './useAnalysisSubmission';

const push = vi.fn();

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ getToken: vi.fn(async () => 'jwt-123') }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/hooks/usePendingAnalyses', () => ({
  refreshPendingAnalyses: vi.fn(),
}));

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, fetchJsonWithAuth: vi.fn(), postFormWithAuth: vi.fn() };
});

const mockedFetch = vi.mocked(fetchJsonWithAuth);

const BODY = { source_type: 'text' as const, text: 'Un titular dudoso.' };

describe('useAnalysisSubmission', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
    push.mockReset();
  });

  it('navigates to the new report on success', async () => {
    mockedFetch.mockResolvedValueOnce({
      status: 'pending',
      analysis_id: 'abc',
    });

    const { result } = renderHook(() => useAnalysisSubmission());

    await act(async () => {
      await result.current.submit(BODY);
    });

    expect(push).toHaveBeenCalledWith('/app/analisis/abc');
    expect(result.current.error).toBeNull();
  });

  it('reports the missing id instead of navigating to an undefined report', async () => {
    mockedFetch.mockResolvedValueOnce({ status: 'pending' });

    const { result } = renderHook(() => useAnalysisSubmission());

    await act(async () => {
      await result.current.submit(BODY);
    });

    expect(push).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(result.current.error).toBe(
        'No se generó un ID de análisis válido.'
      )
    );
  });

  it('keeps the ApiError message distinct from the missing-id message', async () => {
    mockedFetch.mockRejectedValueOnce(
      new ApiError('Has superado el límite diario.', 'RATE_LIMITED', 429)
    );

    const { result } = renderHook(() => useAnalysisSubmission());

    await act(async () => {
      await result.current.submit(BODY);
    });

    expect(push).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(result.current.error).toBe('Has superado el límite diario.')
    );
  });
});
