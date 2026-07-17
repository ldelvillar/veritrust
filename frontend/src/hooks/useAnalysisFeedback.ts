'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

type FeedbackRequest = NonNullable<
  paths['/analysis/{analysis_id}/feedback']['post']['requestBody']
>['content']['application/json'];
type FeedbackResponse =
  paths['/analysis/{analysis_id}/feedback']['post']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAnalysisFeedback() {
  const { getToken } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFeedback = useCallback(
    async (analysisId: string, body: FeedbackRequest): Promise<boolean> => {
      setError(null);
      setIsSubmitting(true);
      try {
        await fetchJsonWithAuth<FeedbackResponse>(
          getToken,
          `/analysis/${analysisId}/feedback`,
          { method: 'POST', body }
        );
        return true;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    [getToken]
  );

  return { submitFeedback, isSubmitting, error, setError };
}
