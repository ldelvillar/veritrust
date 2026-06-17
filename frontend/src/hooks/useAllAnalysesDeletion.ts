'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';

interface DeleteAllResponse {
  deleted_count?: number;
}

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useAllAnalysesDeletion() {
  const { getToken } = useAuth();
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const removeAll = useCallback(async (): Promise<boolean> => {
    setError(null);
    setIsDeleting(true);
    try {
      await fetchJsonWithAuth<DeleteAllResponse>(getToken, '/history', {
        method: 'DELETE',
        errorContextMessage: 'No se pudo eliminar tu actividad',
      });
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, [getToken]);

  return { removeAll, isDeleting, error, setError };
}
