'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

type DeleteAnalysisResponse =
  paths['/analysis/{analysis_id}']['delete']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAnalysisDeletion() {
  const { getToken } = useAuth();
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remove = useCallback(
    async (analysisId: string): Promise<boolean> => {
      setError(null);
      setIsDeleting(true);
      try {
        await fetchJsonWithAuth<DeleteAnalysisResponse>(
          getToken,
          `/analysis/${analysisId}`,
          { method: 'DELETE' }
        );
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return false;
      } finally {
        setIsDeleting(false);
      }
    },
    [getToken]
  );

  return { remove, isDeleting, error, setError };
}
