import { mutate } from 'swr';

// Refresca el indicador y todo listado de /history en caché tras crear o borrar análisis.
export function refreshHistory(): Promise<unknown> {
  return mutate(key => typeof key === 'string' && key.startsWith('/history'));
}
