import { useAuth } from '@clerk/nextjs';
import { useCallback, useState } from 'react';
import { useApiQuery } from '@/hooks/useApiQuery';
import {
  RECENT_HISTORY_PATH,
  type HistoryItem,
  type HistoryPayload,
} from '@/lib/historyQuery';

// Últimos análisis para el menú; refreshHistory los refresca tras crear o borrar.
export function useRecentAnalyses(): HistoryItem[] {
  const { isSignedIn } = useAuth();
  const [hasPending, setHasPending] = useState(false);

  // Identidad estable salvo al cambiar hasPending: un render del menú no debe reiniciar el sondeo.
  const refreshInterval = useCallback(
    () => (hasPending ? 10_000 : 0),
    [hasPending]
  );

  const { data } = useApiQuery<HistoryPayload>(
    isSignedIn ? RECENT_HISTORY_PATH : null,
    {
      refreshInterval,
      onSuccess: latest =>
        setHasPending(latest.items.some(item => item.status === 'pending')),
    }
  );
  return data?.items ?? [];
}
