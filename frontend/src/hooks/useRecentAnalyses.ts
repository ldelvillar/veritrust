import { useAuth } from '@clerk/nextjs';
import { useApiQuery } from '@/hooks/useApiQuery';
import {
  RECENT_HISTORY_PATH,
  type HistoryItem,
  type HistoryPayload,
} from '@/lib/historyQuery';

// Latest analyses for the menu, not polled but refreshed by deletions and indicator changes.
export function useRecentAnalyses(): HistoryItem[] {
  const { isSignedIn } = useAuth();
  const { data } = useApiQuery<HistoryPayload>(
    isSignedIn ? RECENT_HISTORY_PATH : null
  );
  return data?.items ?? [];
}
