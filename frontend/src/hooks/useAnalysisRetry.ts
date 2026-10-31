'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshHistory } from '@/lib/historyCache';
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
      // The row returns to pending without navigation, so refresh the indicator and the lists.
      void refreshHistory();
      return true;
    },
    [getToken, mutate]
  );

  return { retry, isRetrying: isPending, error, setError };
}
