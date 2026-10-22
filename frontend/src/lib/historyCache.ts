import { mutate } from 'swr';
import { PENDING_HISTORY_PATH } from '@/lib/historyQuery';

const keyStartsWith = (prefix: string) => (key: unknown) =>
  typeof key === 'string' && key.startsWith(prefix);

// Refresca el indicador; si su resumen cambia, usePendingAnalyses refresca los listados.
export function refreshPending(): Promise<unknown> {
  return mutate(PENDING_HISTORY_PATH);
}

let lastListsRefresh: Promise<unknown> | null = null;

// Refresca todo listado de /history en caché: el menú y la página abierta del historial.
export function refreshHistoryLists(): Promise<unknown> {
  lastListsRefresh = mutate(keyStartsWith('/history?'));
  return lastListsRefresh;
}

// Tras una acción propia: si el indicador no vio el cambio, los listados se piden aquí.
export async function refreshHistory(): Promise<unknown> {
  const before = lastListsRefresh;
  await refreshPending();
  return lastListsRefresh !== before ? lastListsRefresh : refreshHistoryLists();
}
