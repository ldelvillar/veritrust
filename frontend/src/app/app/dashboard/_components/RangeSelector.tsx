'use client';

import CalendarIcon from '@/assets/Calendar';

export type DashboardRange = '7d' | '14d' | '30d' | '90d';

export const RANGE_DAYS: Record<DashboardRange, number> = {
  '7d': 7,
  '14d': 14,
  '30d': 30,
  '90d': 90,
};

const RANGES = Object.keys(RANGE_DAYS) as DashboardRange[];

export default function RangeSelector({
  value,
  onChange,
}: {
  value: DashboardRange;
  onChange: (range: DashboardRange) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Rango de fechas"
      className="flex w-full items-center gap-0.75 rounded-xl border border-line bg-surface p-1 sm:w-auto sm:pl-2.75"
    >
      <CalendarIcon
        className="mr-1 size-4 shrink-0 text-faint max-sm:hidden"
        aria-hidden
      />
      {RANGES.map(range => {
        const isActive = value === range;
        return (
          <button
            key={range}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(range)}
            className={`h-9 rounded-lg px-3.5 text-sm font-semibold transition focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:outline-none max-sm:flex-1 max-sm:px-2 sm:min-w-10.5 ${
              isActive
                ? 'bg-white text-primary shadow-[0_1px_2px_rgba(18,33,31,.05),0_4px_14px_rgba(18,33,31,.04)]'
                : 'text-muted hover:text-body'
            }`}
          >
            {range}
          </button>
        );
      })}
    </div>
  );
}
