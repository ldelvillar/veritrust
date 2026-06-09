'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

type RetryAnalysisResponse =
  paths['/analysis/{analysis_id}/retry']['post']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAnalysisRetry() {
  const { getToken } = useAuth();
  const [isRetrying, setIsRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retry = useCallback(
    async (analysisId: string): Promise<boolean> => {
      setError(null);
      setIsRetrying(true);
      try {
        await fetchJsonWithAuth<RetryAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}/retry`,
          { method: 'POST' }
        );
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return false;
      } finally {
        setIsRetrying(false);
      }
    },
    [getToken]
  );

  return { retry, isRetrying, error, setError };
}
