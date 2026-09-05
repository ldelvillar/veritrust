'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
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
      // La fila vuelve a pending sin navegación: refrescamos el indicador global.
      void refreshPendingAnalyses();
      return true;
    },
    [getToken, mutate]
  );

  return { reanalyze, isReanalyzing: isPending, error, setError };
}
