'use client';

import Link from 'next/link';
import CheckIcon from '@/assets/Check';
import Spinner from '@/assets/Spinner';
import type { FinishedAnalysis } from '@/hooks/usePendingAnalyses';

interface PendingIndicatorProps {
  pendingCount: number;
  newestPendingId: string | null;
  finished: FinishedAnalysis | null;
  dismissFinished: () => void;
  collapsed?: boolean;
  onNavigate?: () => void;
}

export default function PendingIndicator({
  pendingCount,
  newestPendingId,
  finished,
  dismissFinished,
  collapsed,
  onNavigate,
}: PendingIndicatorProps) {
  if (pendingCount > 0) {
    const label =
      pendingCount === 1
        ? '1 análisis en curso'
        : `${pendingCount} análisis en curso`;
    // Un único análisis enlaza a su informe; varios, al historial filtrado.
    const href =
      pendingCount === 1 && newestPendingId
        ? `/app/analisis/${newestPendingId}`
        : '/app/historial?status=pending';

    if (collapsed) {
      return (
        <Link
          href={href}
          onClick={onNavigate}
          title={label}
          aria-label={label}
          className="mt-2 flex size-11 items-center justify-center self-center rounded-xl bg-primary-soft text-accent transition hover:bg-primary-soft-strong"
        >
          <Spinner className="size-4.75 animate-spin text-primary" />
        </Link>
      );
    }

    return (
      <Link
        href={href}
        onClick={onNavigate}
        className="mt-3 flex items-center gap-3.5 rounded-xl bg-primary-soft px-3.5 py-2.5 text-[14.5px] font-semibold text-accent transition hover:bg-primary-soft-strong"
      >
        <Spinner className="size-4.75 shrink-0 animate-spin text-primary" />
        <span className="leading-none">{label}</span>
      </Link>
    );
  }

  if (finished) {
    const href = `/app/analisis/${finished.analysisId}`;
    const handleClick = () => {
      dismissFinished();
      onNavigate?.();
    };

    if (collapsed) {
      return (
        <Link
          href={href}
          onClick={handleClick}
          title="Análisis finalizado"
          aria-label="Análisis finalizado: ver resultado"
          className="mt-2 flex size-11 items-center justify-center self-center rounded-xl bg-primary-soft text-accent transition hover:bg-primary-soft-strong"
        >
          <CheckIcon className="size-4.75 text-primary" />
        </Link>
      );
    }

    return (
      <Link
        href={href}
        onClick={handleClick}
        className="mt-3 flex items-center gap-3.5 rounded-xl bg-primary-soft px-3.5 py-2.5 text-[14.5px] font-semibold text-accent transition hover:bg-primary-soft-strong"
      >
        <CheckIcon className="size-4.75 shrink-0 text-primary" />
        <span className="flex flex-col gap-1">
          <span className="leading-none">Análisis finalizado</span>
          <span className="text-[11.5px] leading-none font-medium opacity-80">
            Ver resultado
          </span>
        </span>
      </Link>
    );
  }

  return null;
}
