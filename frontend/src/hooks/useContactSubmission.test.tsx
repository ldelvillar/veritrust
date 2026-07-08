import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, postJsonPublic } from '@/lib/apiClient';
import { useContactSubmission } from './useContactSubmission';

vi.mock('@/lib/apiClient', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/apiClient')>();
  return { ...actual, postJsonPublic: vi.fn() };
});

const mockedPost = vi.mocked(postJsonPublic);

const BODY = {
  type: 'contact' as const,
  name: 'Ana',
  email: 'ana@medio.es',
  subject: 'Consulta general',
  message: 'Hola',
};

describe('useContactSubmission', () => {
  beforeEach(() => {
    mockedPost.mockReset();
  });

  it('returns true and POSTs to /contact on success', async () => {
    mockedPost.mockResolvedValueOnce({ status: 'sent' });

    const { result } = renderHook(() => useContactSubmission());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.submit(BODY);
    });

    expect(outcome).toBe(true);
    expect(result.current.error).toBeNull();
    expect(mockedPost).toHaveBeenCalledWith('/contact', BODY);
  });

  it('returns false and surfaces the ApiError message on failure', async () => {
    mockedPost.mockRejectedValueOnce(
      new ApiError('No se pudo enviar tu mensaje.', 'CONTACT_SEND_FAILED', 500)
    );

    const { result } = renderHook(() => useContactSubmission());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.submit(BODY);
    });

    expect(outcome).toBe(false);
    await waitFor(() =>
      expect(result.current.error).toBe('No se pudo enviar tu mensaje.')
    );
  });

  it('returns false with a connection message for a non-ApiError throw', async () => {
    mockedPost.mockRejectedValueOnce(new Error('network down'));

    const { result } = renderHook(() => useContactSubmission());

    let outcome: boolean | undefined;
    await act(async () => {
      outcome = await result.current.submit(BODY);
    });

    expect(outcome).toBe(false);
    await waitFor(() => expect(result.current.error).toMatch(/Sin conexión/));
  });
});
