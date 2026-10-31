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

// Watch the user's 'pending' analyses for the menu's global indicator.
export function usePendingAnalyses() {
  const { isSignedIn } = useAuth();
  const pathname = usePathname();
  const [finished, setFinished] = useState<FinishedAnalysis | null>(null);
  const [hasPending, setHasPending] = useState(false);
  const lastSeen = useRef<{ count: number; analysisId: string | null }>({
    count: 0,
    analysisId: null,
  });
  // Last summary received, null until the first response so mounting does not refresh.
  const lastSummary = useRef<PendingSummary | null>(null);

  // Refresh the lists if the summary changes and detect >0 to 0 for the "finished" notice.
  const trackTransition = useCallback((latest: PendingSummary) => {
    setHasPending(latest.count > 0);
    const before = lastSummary.current;
    lastSummary.current = latest;
    // An Analysis started or finished, so the open lists and the Usage reflect it in the same poll.
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

  // The identity changes with hasPending, forcing SWR to rearm the poll at the new cadence.
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

  // Refresh on navigation, so a just submitted Analysis appears without waiting for the poll.
  useEffect(() => {
    void refetch();
  }, [pathname, refetch]);

  // The finished notice clears itself after a few seconds.
  useEffect(() => {
    if (!finished) return;
    const timer = setTimeout(() => setFinished(null), FINISHED_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [finished]);

  const dismissFinished = useCallback(() => setFinished(null), []);

  return {
    // A poll failure leaves data null and the indicator simply does not show.
    pendingCount: data?.count ?? 0,
    newestPendingId: data?.newest_analysis_id ?? null,
    finished,
    dismissFinished,
  };
}
