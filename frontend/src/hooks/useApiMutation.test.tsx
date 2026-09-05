import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/apiClient';
import { useApiMutation } from './useApiMutation';

describe('useApiMutation', () => {
  it('returns the response and leaves no error on success', async () => {
    const { result } = renderHook(() => useApiMutation());

    let data: { status: string } | null | undefined;
    await act(async () => {
      data = await result.current.mutate(async () => ({ status: 'ok' }));
    });

    expect(data).toEqual({ status: 'ok' });
    expect(result.current.error).toBeNull();
    expect(result.current.isPending).toBe(false);
  });

  it('returns null and surfaces the ApiError message', async () => {
    const { result } = renderHook(() => useApiMutation());

    let data: unknown;
    await act(async () => {
      data = await result.current.mutate(async () => {
        throw new ApiError(
          'Análisis no encontrado.',
          'ANALYSIS_NOT_FOUND',
          404
        );
      });
    });

    expect(data).toBeNull();
    await waitFor(() =>
      expect(result.current.error).toBe('Análisis no encontrado.')
    );
  });

  it('returns null with a connection message for a non-ApiError throw', async () => {
    const { result } = renderHook(() => useApiMutation());

    let data: unknown;
    await act(async () => {
      data = await result.current.mutate(async () => {
        throw new Error('network down');
      });
    });

    expect(data).toBeNull();
    await waitFor(() => expect(result.current.error).toMatch(/Sin conexión/));
  });

  it('flags the request as pending while it is in flight', async () => {
    const { result } = renderHook(() => useApiMutation());

    let resolve: (value: { status: string }) => void = () => {};
    const pending = new Promise<{ status: string }>(res => {
      resolve = res;
    });

    let call: Promise<unknown>;
    act(() => {
      call = result.current.mutate(() => pending);
    });

    await waitFor(() => expect(result.current.isPending).toBe(true));

    await act(async () => {
      resolve({ status: 'ok' });
      await call;
    });

    expect(result.current.isPending).toBe(false);
  });

  it('clears a previous error when a new request starts', async () => {
    const { result } = renderHook(() => useApiMutation());

    await act(async () => {
      await result.current.mutate(async () => {
        throw new Error('network down');
      });
    });
    await waitFor(() => expect(result.current.error).not.toBeNull());

    await act(async () => {
      await result.current.mutate(async () => ({ status: 'ok' }));
    });

    expect(result.current.error).toBeNull();
  });

  it('keeps the same mutate reference across renders', () => {
    const { result, rerender } = renderHook(() => useApiMutation());
    const first = result.current.mutate;

    rerender();

    expect(result.current.mutate).toBe(first);
  });
});
