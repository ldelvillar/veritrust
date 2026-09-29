'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import type { paths } from '@/types/api';

type DeleteAnalysisResponse =
  paths['/analysis/{analysis_id}']['delete']['responses']['200']['content']['application/json'];

export function useAnalysisDeletion() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const remove = useCallback(
    async (analysisId: string): Promise<boolean> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<DeleteAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}`,
          { method: 'DELETE' }
        )
      );
      if (data === null) return false;
      // Borrar un análisis pendiente cambia el recuento del indicador global.
      void refreshPendingAnalyses();
      return true;
    },
    [getToken, mutate]
  );

  return { remove, isDeleting: isPending, error, setError };
}
