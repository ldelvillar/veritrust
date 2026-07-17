import { useAuth } from '@clerk/nextjs';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { mutate } from 'swr';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { paths } from '@/types/api';

type HistoryResponse =
  paths['/history']['get']['responses']['200']['content']['application/json'];

// page_size=1 basta: count trae el total pendiente y items[0] el más reciente.
const PENDING_PATH = '/history?status=pending&page_size=1';
const FINISHED_DISMISS_MS = 20_000;

export interface FinishedAnalysis {
  analysisId: string;
}

// Refresca el indicador en cuanto una acción encola un análisis, sin esperar al sondeo.
export function refreshPendingAnalyses(): Promise<unknown> {
  return mutate(PENDING_PATH);
}

// Vigila los análisis 'pending' del usuario para el indicador global del menú.
export function usePendingAnalyses() {
  const { isSignedIn } = useAuth();
  const pathname = usePathname();
  const [finished, setFinished] = useState<FinishedAnalysis | null>(null);
  const [hasPending, setHasPending] = useState(false);
  const lastSeen = useRef<{ count: number; analysisId: string | null }>({
    count: 0,
    analysisId: null,
  });

  // Detecta la transición >0 → 0 para el aviso transitorio de "finalizado".
  const trackTransition = useCallback((latest: HistoryResponse) => {
    setHasPending(latest.count > 0);
    const previous = lastSeen.current;
    lastSeen.current = {
      count: latest.count,
      analysisId: latest.items[0]?.analysis_id ?? previous.analysisId,
    };
    if (latest.count > 0) {
      setFinished(null);
    } else if (previous.count > 0 && previous.analysisId) {
      setFinished({ analysisId: previous.analysisId });
    }
  }, []);

  // La identidad cambia con hasPending: obliga a SWR a rearmar el sondeo con la nueva cadencia.
  const refreshInterval = useCallback(
    () => (hasPending ? 10_000 : 60_000),
    [hasPending]
  );

  const { data, refetch } = useApiQuery<HistoryResponse>(
    isSignedIn ? PENDING_PATH : null,
    {
      refreshInterval,
      onSuccess: trackTransition,
    }
  );

  // Al navegar refrescamos: un análisis recién enviado aparece sin esperar al sondeo.
  useEffect(() => {
    void refetch();
  }, [pathname, refetch]);

  // El aviso de finalizado se retira solo pasados unos segundos.
  useEffect(() => {
    if (!finished) return;
    const timer = setTimeout(() => setFinished(null), FINISHED_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [finished]);

  const dismissFinished = useCallback(() => setFinished(null), []);

  return {
    // Un fallo del sondeo deja data en null: el indicador simplemente no se muestra.
    pendingCount: data?.count ?? 0,
    newestPendingId: data?.items[0]?.analysis_id ?? null,
    finished,
    dismissFinished,
  };
}
