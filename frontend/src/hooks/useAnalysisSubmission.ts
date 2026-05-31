'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import type { components, paths } from '@/types/api';

type AnalysisRequest = components['schemas']['AnalysisRequest'];
type CreateAnalysisResponse =
  paths['/analysis']['post']['responses']['200']['content']['application/json'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
const NO_ID_ERROR = 'No se generó un ID de análisis válido.';

export function useAnalysisSubmission() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (body: AnalysisRequest) => {
      setError(null);
      setIsLoading(true);
      try {
        const data = await fetchJsonWithAuth<CreateAnalysisResponse>(
          getToken,
          '/analysis',
          { method: 'POST', body }
        );

        if (!data.analysis_id) {
          throw new Error(NO_ID_ERROR);
        }

        router.push(`/app/analisis/${data.analysis_id}`);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError(CONNECTION_ERROR);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [getToken, router]
  );

  return { submit, isLoading, error, setError };
}
