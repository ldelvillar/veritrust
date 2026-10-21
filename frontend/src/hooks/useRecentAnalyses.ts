import { useAuth } from '@clerk/nextjs';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { mutate } from 'swr';
import { useApiQuery } from '@/hooks/useApiQuery';
import { INITIAL_HISTORY_PATH } from '@/lib/historyQuery';
import type { paths } from '@/types/api';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
export type RecentAnalysis = HistoryPayload['items'][number];

const RECENT_LIMIT = 5;

// Refresca la lista del menú tras un borrado que no cambia de página.
export function refreshRecentAnalyses(): Promise<unknown> {
  return mutate(INITIAL_HISTORY_PATH);
}

// Últimos análisis del usuario para el menú; comparte clave con la primera página del historial.
export function useRecentAnalyses(pendingCount: number): RecentAnalysis[] {
  const { isSignedIn } = useAuth();
  const pathname = usePathname();
  const { data, refetch } = useApiQuery<HistoryPayload>(
    isSignedIn ? INITIAL_HISTORY_PATH : null
  );

  // Un análisis nuevo o recién terminado cambia la lista sin esperar a otra visita.
  useEffect(() => {
    if (isSignedIn) void refetch();
  }, [isSignedIn, pathname, pendingCount, refetch]);

  return data?.items.slice(0, RECENT_LIMIT) ?? [];
}
