'use client';

import { createContext, useContext } from 'react';

import { useApiQuery } from '@/hooks/useApiQuery';
import { PLAN_PATH, type PlanResponse } from '@/lib/plan';

// Plan precargado por el layout de /app; null si la API no respondió en el servidor.
export const InitialPlanContext = createContext<PlanResponse | null>(null);

// Única fuente del Plan en el cliente; mientras sea null, la API decide qué se permite.
export function usePlan(
  options: {
    refreshInterval?: number | ((latest: PlanResponse | undefined) => number);
  } = {}
) {
  const initialPlan = useContext(InitialPlanContext);
  // Con datos en caché no se repite la petición al montar: la refrescan los eventos que cambian el Plan.
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
