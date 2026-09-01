'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';

const EXPORT_FILENAME = 'historial-veritrust.csv';

const EXPORT_FALLBACK_ERROR =
  'No se pudo exportar el historial. Inténtalo de nuevo.';

export function useHistoryExport(path: string) {
  const { getToken } = useAuth();
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runExport = useCallback(async () => {
    setError(null);
    setIsExporting(true);
    try {
      const blob = await fetchBlobWithAuth(getToken, path);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = EXPORT_FILENAME;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : EXPORT_FALLBACK_ERROR);
    } finally {
      setIsExporting(false);
    }
  }, [getToken, path]);

  return { runExport, isExporting, error };
}
