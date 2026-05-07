import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useState } from 'react';
import { fetchJsonWithAuth } from '@/lib/apiClient';

export function useApiQuery<T>(path: string | null) {
  const { getToken } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(path !== null);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (path === null) return;
    setIsLoading(true);
    setError(null);
    try {
      setData(await fetchJsonWithAuth<T>(getToken, path, { method: 'GET' }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [getToken, path]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}
