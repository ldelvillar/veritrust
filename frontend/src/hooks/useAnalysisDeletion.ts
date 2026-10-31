'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshHistory } from '@/lib/historyCache';
import type { paths } from '@/types/api';

type DeleteAnalysisResponse =
  paths['/analysis/{analysis_id}']['delete']['responses']['200']['content']['application/json'];

export function useAnalysisDeletion() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const remove = useCallback(
    async (analysisId: string): Promise<boolean> => {
      // The refresh runs inside the mutation, so the dialog stays busy until the row disappears.
      const data = await mutate(async () => {
        const deleted = await fetchJsonWithAuth<DeleteAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}`,
          { method: 'DELETE' }
        );
        await refreshHistory();
        return deleted;
      });
      return data !== null;
    },
    [getToken, mutate]
  );

  return { remove, isDeleting: isPending, error, setError };
}
