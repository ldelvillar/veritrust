import { useAuth } from '@clerk/nextjs';
import { useApiQuery } from '@/hooks/useApiQuery';
import {
  RECENT_HISTORY_PATH,
  type HistoryItem,
  type HistoryPayload,
} from '@/lib/historyQuery';

// Últimos análisis para el menú; los refrescan refreshHistory y el sondeo de pendientes.
export function useRecentAnalyses(): HistoryItem[] {
  const { isSignedIn } = useAuth();
  const { data } = useApiQuery<HistoryPayload>(
    isSignedIn ? RECENT_HISTORY_PATH : null
  );
  return data?.items ?? [];
}
