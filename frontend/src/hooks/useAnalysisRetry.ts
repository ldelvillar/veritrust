'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshPending } from '@/lib/historyCache';
import type { paths } from '@/types/api';

type RetryAnalysisResponse =
  paths['/analysis/{analysis_id}/retry']['post']['responses']['200']['content']['application/json'];

export function useAnalysisRetry() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const retry = useCallback(
    async (analysisId: string): Promise<boolean> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<RetryAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}/retry`,
          { method: 'POST' }
        )
      );
      if (!data) return false;
      // La fila vuelve a pending sin navegación: el indicador cambia y arrastra a los listados.
      void refreshPending();
      return true;
    },
    [getToken, mutate]
  );

  return { retry, isRetrying: isPending, error, setError };
}
