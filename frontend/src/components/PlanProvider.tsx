'use client';

import type { ReactNode } from 'react';

import { InitialPlanContext } from '@/hooks/usePlan';
import type { PlanResponse } from '@/lib/plan';

export default function PlanProvider({
  initialPlan,
  children,
}: {
  initialPlan: PlanResponse | null;
  children: ReactNode;
}) {
  return (
    <InitialPlanContext value={initialPlan}>{children}</InitialPlanContext>
  );
}
