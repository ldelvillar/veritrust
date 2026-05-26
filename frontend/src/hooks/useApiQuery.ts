import { useAuth } from '@clerk/nextjs';
import { useCallback } from 'react';
import useSWR from 'swr';
import { fetchJsonWithAuth } from '@/lib/apiClient';

export function useApiQuery<T>(path: string | null) {
  const { getToken } = useAuth();

  const { data, error, isLoading, mutate } = useSWR<T>(
    path,
    (key: string) => fetchJsonWithAuth<T>(getToken, key, { method: 'GET' })
  );

  const refetch = useCallback(async () => {
    await mutate();
  }, [mutate]);

  return {
    data: data ?? null,
    isLoading,
    error:
      error instanceof Error
        ? error.message
        : error
          ? 'Error desconocido.'
          : null,
    refetch,
  };
}
