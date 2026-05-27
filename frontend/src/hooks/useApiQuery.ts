import { useAuth } from '@clerk/nextjs';
import { useCallback } from 'react';
import useSWR from 'swr';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';

export function useApiQuery<T>(path: string | null) {
  const { getToken } = useAuth();

  const { data, error, isLoading, mutate } = useSWR<T>(
    path,
    (key: string) => fetchJsonWithAuth<T>(getToken, key, { method: 'GET' })
  );

  const refetch = useCallback(async () => {
    await mutate();
  }, [mutate]);

  const normalizedError: ApiError | Error | null =
    error instanceof Error ? error : error ? new Error('Error desconocido.') : null;

  return {
    data: data ?? null,
    isLoading,
    error: normalizedError,
    refetch,
  };
}
