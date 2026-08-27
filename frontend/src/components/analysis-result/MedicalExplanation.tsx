'use client';

import { useState } from 'react';
import { MarkdownHooks } from 'react-markdown';
import CheckIcon from '@/assets/Check';
import ClipboardIcon from '@/assets/Clipboard';
import MedicalCross from '@/assets/MedicalCross';

type CopyState = 'idle' | 'copied' | 'error';

const COPY_LABEL: Record<CopyState, string> = {
  idle: 'Copiar',
  copied: 'Copiado',
  error: 'No se pudo copiar',
};

const COPY_STYLE: Record<CopyState, string> = {
  idle: 'border-line-strong bg-white text-body hover:border-primary hover:text-primary',
  copied: 'border-success-soft bg-success-soft text-success-ink',
  error: 'border-danger/30 bg-danger-soft text-danger-ink',
};

export default function MedicalExplanation({
  explanation,
}: {
  explanation: string;
}) {
  const [copyState, setCopyState] = useState<CopyState>('idle');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(explanation);
      setCopyState('copied');
    } catch {
      setCopyState('error');
    }
    setTimeout(() => setCopyState('idle'), 2000);
  };

  return (
    <div className="rounded-xl border border-line bg-white shadow-sm">
      <div className="flex items-center gap-3.5 rounded-t-xl border-b border-line bg-linear-to-b from-surface-subtle to-white px-6 py-5">
        <div className="relative grid size-12 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-emerald-600">
          <MedicalCross className="size-6" />
        </div>
        <div className="min-w-0">
          <h3 className="flex items-center gap-2.5 text-base font-bold text-ink">
            Experto en salud
          </h3>
          <p className="mt-0.5 text-[12.5px] text-muted">
            Contrasta cada afirmación con el consenso médico actual
          </p>
        </div>
      </div>

      <div className="px-6 py-5">
        <div className="pointer-events-none sticky top-20 z-10 mb-1 flex h-9 justify-end print:hidden">
          <button
            type="button"
            onClick={handleCopy}
            title="Copiar la explicación"
            className={`pointer-events-auto inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-bold shadow-sm transition focus:ring-2 focus:ring-primary/20 focus:outline-none ${COPY_STYLE[copyState]}`}
          >
            {copyState === 'copied' ? (
              <CheckIcon className="size-3.5 shrink-0" />
            ) : (
              <ClipboardIcon className="size-3.5 shrink-0" />
            )}
            <span aria-live="polite">{COPY_LABEL[copyState]}</span>
          </button>
        </div>

        <div className="prose max-w-none text-body prose-headings:text-ink prose-strong:text-ink">
          <MarkdownHooks>{explanation}</MarkdownHooks>
        </div>
      </div>
    </div>
  );
}
