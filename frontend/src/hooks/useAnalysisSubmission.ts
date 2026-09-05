'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth, postFormWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import type { components, paths } from '@/types/api';

type AnalysisRequest = components['schemas']['AnalysisRequest'];
type CreateAnalysisResponse =
  paths['/analysis']['post']['responses']['200']['content']['application/json'];

const NO_ID_ERROR = 'No se generó un ID de análisis válido.';

export function useAnalysisSubmission() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const startAnalysis = useCallback(
    async (request: () => Promise<CreateAnalysisResponse>) => {
      const data = await mutate(request);
      if (!data) return;
      if (!data.analysis_id) {
        setError(NO_ID_ERROR);
        return;
      }
      void refreshPendingAnalyses();
      router.push(`/app/analisis/${data.analysis_id}`);
    },
    [mutate, router, setError]
  );

  const submit = useCallback(
    (body: AnalysisRequest) =>
      startAnalysis(() =>
        fetchJsonWithAuth<CreateAnalysisResponse>(getToken, '/analysis', {
          method: 'POST',
          body,
        })
      ),
    [getToken, startAnalysis]
  );

  const submitFile = useCallback(
    (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return startAnalysis(() =>
        postFormWithAuth<CreateAnalysisResponse>(
          getToken,
          '/analysis/file',
          formData
        )
      );
    },
    [getToken, startAnalysis]
  );

  return { submit, submitFile, isLoading: isPending, error, setError };
}
