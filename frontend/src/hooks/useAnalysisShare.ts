'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import type { paths } from '@/types/api';

type ShareResponse =
  paths['/analysis/{analysis_id}/share']['post']['responses']['200']['content']['application/json'];
type UnshareResponse =
  paths['/analysis/{analysis_id}/share']['delete']['responses']['200']['content']['application/json'];

export function useAnalysisShare() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const createShare = useCallback(
    async (analysisId: string): Promise<string | null> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<ShareResponse>(
          getToken,
          `/analysis/${analysisId}/share`,
          { method: 'POST' }
        )
      );
      return data?.share_token ?? null;
    },
    [getToken, mutate]
  );

  const removeShare = useCallback(
    async (analysisId: string): Promise<boolean> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<UnshareResponse>(
          getToken,
          `/analysis/${analysisId}/share`,
          { method: 'DELETE' }
        )
      );
      return data !== null;
    },
    [getToken, mutate]
  );

  return { createShare, removeShare, isSharing: isPending, error, setError };
}
