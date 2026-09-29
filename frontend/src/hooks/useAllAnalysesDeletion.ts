'use client';

import { useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

import { fetchJsonWithAuth } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import { refreshPendingAnalyses } from '@/hooks/usePendingAnalyses';
import type { components } from '@/types/api';

type DeleteAllResponse = components['schemas']['DeleteAllResponse'];

export function useAllAnalysesDeletion() {
  const { getToken } = useAuth();
  const { mutate, isPending, error, setError } = useApiMutation();

  const removeAll = useCallback(async (): Promise<boolean> => {
    const data = await mutate(() =>
      fetchJsonWithAuth<DeleteAllResponse>(getToken, '/history', {
        method: 'DELETE',
        errorContextMessage: 'No se pudo eliminar tu actividad',
      })
    );
    if (data === null) return false;
    // Borrar la actividad elimina también los análisis pendientes del indicador global.
    void refreshPendingAnalyses();
    return true;
  }, [getToken, mutate]);

  return { removeAll, isDeleting: isPending, error, setError };
}
