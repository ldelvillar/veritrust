import { useAuth } from '@clerk/nextjs';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useApiQuery } from '@/hooks/useApiQuery';

import { refreshHistoryLists } from '@/lib/historyCache';
import { refreshPlan } from '@/lib/planCache';
import { PENDING_HISTORY_PATH } from '@/lib/historyQuery';
import type { paths } from '@/types/api';

type PendingSummary =
  paths['/history/pending']['get']['responses']['200']['content']['application/json'];

const FINISHED_DISMISS_MS = 20_000;

export interface FinishedAnalysis {
  analysisId: string;
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
  // Último resumen recibido; null hasta la primera respuesta para no refrescar al montar.
  const lastSummary = useRef<PendingSummary | null>(null);

  // Refresca los listados si cambia el resumen y detecta >0 → 0 para el aviso de "finalizado".
  const trackTransition = useCallback((latest: PendingSummary) => {
    setHasPending(latest.count > 0);
    const before = lastSummary.current;
    lastSummary.current = latest;
    // Un análisis empezó o terminó: los listados abiertos y el Usage lo reflejan en el mismo sondeo.
    if (
      before &&
      (before.count !== latest.count ||
        before.newest_analysis_id !== latest.newest_analysis_id)
    ) {
      void refreshHistoryLists();
      void refreshPlan();
    }
    const previous = lastSeen.current;
    lastSeen.current = {
      count: latest.count,
      analysisId: latest.newest_analysis_id ?? previous.analysisId,
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

  const { data, refetch } = useApiQuery<PendingSummary>(
    isSignedIn ? PENDING_HISTORY_PATH : null,
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
    newestPendingId: data?.newest_analysis_id ?? null,
    finished,
    dismissFinished,
  };
}
