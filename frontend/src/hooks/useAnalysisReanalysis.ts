'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import type { paths } from '@/types/api';

type ReanalyzeAnalysisResponse =
  paths['/analysis/{analysis_id}/reanalyze']['post']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAnalysisReanalysis() {
  const { getToken } = useAuth();
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reanalyze = useCallback(
    async (analysisId: string): Promise<boolean> => {
      setError(null);
      setIsReanalyzing(true);
      try {
        await fetchJsonWithAuth<ReanalyzeAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}/reanalyze`,
          { method: 'POST' }
        );
        // La fila vuelve a pending sin navegación: refrescamos el indicador global.
        void refreshPendingAnalyses();
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return false;
      } finally {
        setIsReanalyzing(false);
      }
    },
    [getToken]
  );

  return { reanalyze, isReanalyzing, error, setError };
}
