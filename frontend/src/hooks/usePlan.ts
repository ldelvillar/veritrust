'use client';

import { createContext, useContext } from 'react';

import { useApiQuery } from '@/hooks/useApiQuery';
import { PLAN_PATH, type PlanResponse } from '@/lib/plan';

// Plan preloaded by the /app layout, null if the API did not answer on the server.
export const InitialPlanContext = createContext<PlanResponse | null>(null);

// The client's single source of the Plan, where the API decides what is allowed while it is null.
export function usePlan(
  options: {
    refreshInterval?: number | ((latest: PlanResponse | undefined) => number);
  } = {}
) {
  const initialPlan = useContext(InitialPlanContext);
  // With cached data the request is not repeated on mount, as the events that change the Plan refresh it.
  const { data } = useApiQuery<PlanResponse>(PLAN_PATH, {
    fallbackData: initialPlan ?? undefined,
    refreshInterval: options.refreshInterval,
    revalidateIfStale: false,
  });

  return {
    plan: data,
    limits: data?.limits ?? null,
    usage: data?.usage ?? null,
  };
}
