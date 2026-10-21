import { useAuth } from '@clerk/nextjs';
import { useApiQuery } from '@/hooks/useApiQuery';
import {
  INITIAL_HISTORY_PATH,
  type HistoryItem,
  type HistoryPayload,
} from '@/lib/historyQuery';

// Últimos análisis para el menú; comparte clave con la primera página del historial y su refresco.
export function useRecentAnalyses(): HistoryItem[] {
  const { isSignedIn } = useAuth();
  const { data } = useApiQuery<HistoryPayload>(
    isSignedIn ? INITIAL_HISTORY_PATH : null,
    {
      // Mientras haya análisis en curso, refrescamos para que pasen a hecho/fallido solos.
      refreshInterval: latest =>
        latest?.items.some(item => item.status === 'pending') ? 10_000 : 0,
    }
  );
  return data?.items ?? [];
}
