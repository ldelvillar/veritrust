import { mutate } from 'swr';
import { PENDING_HISTORY_PATH } from '@/lib/historyQuery';

const keyStartsWith = (prefix: string) => (key: unknown) =>
  typeof key === 'string' && key.startsWith(prefix);

// Refresca el indicador; si su resumen cambia, usePendingAnalyses refresca los listados.
export function refreshPending(): Promise<unknown> {
  return mutate(PENDING_HISTORY_PATH);
}

// Refresca todo listado de /history en caché: el menú y la página abierta del historial.
export function refreshHistoryLists(): Promise<unknown> {
  return mutate(keyStartsWith('/history?'));
}

// Tras una acción propia: los listados se piden aparte por si el indicador no ve el cambio.
export function refreshHistory(): Promise<unknown> {
  return Promise.all([refreshPending(), refreshHistoryLists()]);
}
