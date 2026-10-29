import { mutate } from 'swr';

import { ApiError } from '@/lib/apiClient';
import { PLAN_PATH, isPlanError } from '@/lib/plan';

// Refresca el Plan en caché: tras empezar o terminar un análisis, o si la API lo contradice.
export function refreshPlan(): Promise<unknown> {
  return mutate(PLAN_PATH);
}

// Un rechazo por el Plan delata que el que pinta la UI está desactualizado.
export function refreshPlanOnPlanError(err: unknown): void {
  if (err instanceof ApiError && isPlanError(err.code)) void refreshPlan();
}
