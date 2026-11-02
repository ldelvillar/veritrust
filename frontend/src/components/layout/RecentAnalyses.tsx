'use client';

import Link from 'next/link';
import {
  getAnalysisTitle,
  getStatusKey,
  STATUS_LABEL,
  VERDICT_META,
} from '@/components/analysis-result/format';
import type { HistoryItem } from '@/lib/historyQuery';

// Short windows only fit this many without pushing the menu footer.
const COMPACT_LIMIT = 3;

function dotFor(item: HistoryItem): { className: string; label: string } {
  const statusKey = getStatusKey(item);
  if (statusKey)
    return {
      className:
        statusKey === 'pending' ? 'animate-pulse bg-primary' : 'bg-line-strong',
      label: STATUS_LABEL[statusKey],
    };
  const meta = VERDICT_META[item.verdict];
  return { className: meta.solid, label: meta.label };
}

interface RecentAnalysesProps {
  items: HistoryItem[];
  onNavigate?: () => void;
}

export default function RecentAnalyses({
  items,
  onNavigate,
}: RecentAnalysesProps) {
  if (items.length === 0) return null;

  return (
    <>
      <div className="flex items-center justify-between px-3 pt-6 pb-2 text-2xs font-bold tracking-[0.13em] text-faint uppercase">
        <span>Recientes</span>
        <Link
          href="/app/historial"
          onClick={onNavigate}
          className="font-semibold tracking-normal whitespace-nowrap text-accent normal-case transition hover:text-primary-strong"
        >
          Ver todo
        </Link>
      </div>
      <ul className="flex flex-col gap-0.5">
        {items.map((item, index) => {
          const title = getAnalysisTitle(item);
          const dot = dotFor(item);
          return (
            <li
              key={item.analysis_id}
              className={
                index >= COMPACT_LIMIT
                  ? '[@media(max-height:760px)]:hidden'
                  : undefined
              }
            >
              <Link
                href={`/app/analisis/${item.analysis_id}`}
                onClick={onNavigate}
                title={title}
                className="flex items-center gap-3 rounded-lg px-3.5 py-2 text-sm font-medium text-body transition hover:bg-surface"
              >
                <span
                  aria-hidden="true"
                  className={`size-2 shrink-0 rounded-full ${dot.className}`}
                />
                <span className="sr-only">{`${dot.label}:`}</span>{' '}
                <span className="min-w-0 truncate">{title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
