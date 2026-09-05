'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import type { paths } from '@/types/api';

type FeedbackRequest = NonNullable<
  paths['/analysis/{analysis_id}/feedback']['post']['requestBody']
>['content']['application/json'];
type FeedbackResponse =
  paths['/analysis/{analysis_id}/feedback']['post']['responses']['200']['content']['application/json'];

export function useAnalysisFeedback() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const submitFeedback = useCallback(
    async (analysisId: string, body: FeedbackRequest): Promise<boolean> => {
      const data = await mutate(() =>
        fetchJsonWithAuth<FeedbackResponse>(
          getToken,
          `/analysis/${analysisId}/feedback`,
          { method: 'POST', body }
        )
      );
      return data !== null;
    },
    [getToken, mutate]
  );

  return { submitFeedback, isSubmitting: isPending, error, setError };
}
