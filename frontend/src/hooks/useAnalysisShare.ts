'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

type ShareResponse =
  paths['/analysis/{analysis_id}/share']['post']['responses']['200']['content']['application/json'];
type UnshareResponse =
  paths['/analysis/{analysis_id}/share']['delete']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAnalysisShare() {
  const { getToken } = useAuth();
  const [isSharing, setIsSharing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createShare = useCallback(
    async (analysisId: string): Promise<string | null> => {
      setError(null);
      setIsSharing(true);
      try {
        const data = await fetchJsonWithAuth<ShareResponse>(
          getToken,
          `/analysis/${analysisId}/share`,
          { method: 'POST' }
        );
        return data.share_token;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return null;
      } finally {
        setIsSharing(false);
      }
    },
    [getToken]
  );

  const removeShare = useCallback(
    async (analysisId: string): Promise<boolean> => {
      setError(null);
      setIsSharing(true);
      try {
        await fetchJsonWithAuth<UnshareResponse>(
          getToken,
          `/analysis/${analysisId}/share`,
          { method: 'DELETE' }
        );
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return false;
      } finally {
        setIsSharing(false);
      }
    },
    [getToken]
  );

  return { createShare, removeShare, isSharing, error, setError };
}
