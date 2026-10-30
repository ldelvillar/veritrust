'use client';

import Button from '@/components/Button';
import { PLAN_LABEL } from '@/config/plans';
import { usePlan } from '@/hooks/usePlan';
import {
  UPGRADE_HREF,
  formatCount,
  formatPlanDate,
  usedThisMonth,
} from '@/lib/plan';

// Por debajo de esta fracción del Allowance el medidor avisa de que quedan pocos.
const LOW_REMAINING_RATIO = 0.2;

export default function PlanMeter({ onNavigate }: { onNavigate?: () => void }) {
  const { plan, limits, usage } = usePlan();
  if (!plan || !limits || !usage) return null;

  const allowance = limits.analyses_per_month;
  const used = usedThisMonth(limits, usage);
  const isFree = plan.plan === 'free';
  const isLow = usage.remaining <= allowance * LOW_REMAINING_RATIO;
  const percent = Math.min(100, Math.round((used / allowance) * 100));

  return (
    <div className="mb-3.5 rounded-2xl border border-line bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-muted">Tu plan</span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-2xs font-extrabold tracking-wide uppercase ${
            isFree ? 'bg-white text-body' : 'bg-primary text-white'
          }`}
        >
          {PLAN_LABEL[plan.plan]}
        </span>
      </div>
      <div title={`Se renuevan el ${formatPlanDate(usage.resets_at)}`}>
        <p className="mt-2.5 text-sm font-semibold text-body">
          {formatCount(used)} de {formatCount(allowance)} análisis este mes
        </p>
        <div
          role="progressbar"
          aria-label="Análisis usados este mes"
          aria-valuemin={0}
          aria-valuemax={allowance}
          aria-valuenow={used}
          className="mt-2 h-1.5 overflow-hidden rounded-full bg-line"
        >
          <div
            className={`h-full rounded-full ${isLow ? 'bg-warning' : 'bg-primary'}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>
      {isFree && (
        <Button
          href={UPGRADE_HREF}
          onClick={onNavigate}
          className="mt-3.5 w-full"
        >
          Hazte Pro
        </Button>
      )}
    </div>
  );
}
