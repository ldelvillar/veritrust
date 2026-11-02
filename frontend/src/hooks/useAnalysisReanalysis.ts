'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshHistory } from '@/lib/historyCache';
import type { paths } from '@/types/api';

type ReanalyzeAnalysisResponse =
  paths['/analysis/{analysis_id}/reanalyze']['post']['responses']['200']['content']['application/json'];

export function useAnalysisReanalysis() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const reanalyze = useCallback(
    async (analysisId: string): Promise<boolean> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<ReanalyzeAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}/reanalyze`,
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

  return { reanalyze, isReanalyzing: isPending, error, setError };
}
