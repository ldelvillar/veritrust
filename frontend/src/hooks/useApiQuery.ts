import { useAuth } from '@clerk/nextjs';
import { useCallback } from 'react';
import useSWR, { useSWRConfig } from 'swr';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';

interface UseApiQueryOptions<T> {
  fallbackData?: T;
  refreshInterval?: number | ((latestData: T | undefined) => number);
  onSuccess?: (latestData: T) => void;
}

export function useApiQuery<T>(
  path: string | null,
  options: UseApiQueryOptions<T> = {}
) {
  const { getToken } = useAuth();
  const { cache } = useSWRConfig();

  // Server data is fresh, but a cached copy outranks it in SWR: only skip the refetch when none exists.
  const skipMountRefetch =
    options.fallbackData !== undefined &&
    path !== null &&
    cache.get(path)?.data === undefined;

  const { data, error, isLoading, mutate } = useSWR<T>(
    path,
    (key: string) => fetchJsonWithAuth<T>(getToken, key, { method: 'GET' }),
    {
      fallbackData: options.fallbackData,
      revalidateOnMount: skipMountRefetch ? false : undefined,
      refreshInterval: options.refreshInterval,
      ...(options.onSuccess ? { onSuccess: options.onSuccess } : {}),
    }
  );

  const refetch = useCallback(async () => {
    await mutate();
  }, [mutate]);

  const normalizedError: ApiError | Error | null =
    error instanceof Error
      ? error
      : error
        ? new Error('Error desconocido.')
        : null;

  return {
    data: data ?? null,
    isLoading,
    error: normalizedError,
    refetch,
  };
}
