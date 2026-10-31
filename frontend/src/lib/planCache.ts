import { mutate } from 'swr';

import { ApiError } from '@/lib/apiClient';
import { PLAN_PATH, isPlanError } from '@/lib/plan';

// Refresh the cached Plan after an Analysis starts or ends, or when the API contradicts it.
export function refreshPlan(): Promise<unknown> {
  return mutate(PLAN_PATH);
}

// A Plan refusal reveals that the one the UI shows is stale.
export function refreshPlanOnPlanError(err: unknown): void {
  if (err instanceof ApiError && isPlanError(err.code)) void refreshPlan();
}
