'use client';

import { useId, useState } from 'react';
import BookIcon from '@/assets/Book';
import Chevron from '@/assets/Chevron';
import SourceRow from './SourceRow';
import { getClaimStyle, normalizeFraction } from './format';
import type { ClaimType, SourceType } from './types';

export default function ClaimRow({
  claim,
  sources,
  showEvidence,
}: {
  claim: ClaimType;
  sources: SourceType[];
  showEvidence: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const style = getClaimStyle(claim.verdict);
  const ClaimIcon = style.Icon;
  const confidencePct = Math.round(normalizeFraction(claim.confidence) * 100);
  const sourceCount = sources.length;

  return (
    <div className="flex gap-3 border-t border-slate-100 py-4 first:border-t-0 first:pt-0.5 print:break-inside-avoid">
      <div
        className={`grid size-7 shrink-0 place-items-center rounded-lg ${style.tile}`}
      >
        <ClaimIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug font-bold text-slate-900">
          {claim.text}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2.5">
          <span
            className={`rounded-md px-2 py-1 text-[10.5px] font-bold tracking-wide uppercase ${style.pill}`}
          >
            {style.text}
          </span>
          <span className="text-[11.5px] font-semibold text-slate-400">
            {confidencePct}% de confianza
          </span>
        </div>

        {showEvidence &&
          (sourceCount > 0 ? (
            <>
              <button
                type="button"
                onClick={() => setOpen(value => !value)}
                aria-expanded={open}
                aria-controls={panelId}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none print:hidden"
              >
                <BookIcon className="size-3.5" />
                {open ? 'Ocultar' : 'Ver'} {sourceCount}{' '}
                {sourceCount === 1 ? 'fuente' : 'fuentes'}
                <Chevron
                  className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
                  aria-hidden
                />
              </button>
              {/* Siempre en el DOM y colapsado con clases, para que el PDF
                  (print:block) muestre toda la evidencia aunque esté oculta. */}
              <ul
                id={panelId}
                aria-label="Fuentes que respaldan esta afirmación"
                className={`mt-2.5 rounded-xl border border-slate-100 bg-slate-50/70 px-3.5 ${
                  open ? 'block' : 'hidden print:block'
                }`}
              >
                {sources.map((source, index) => (
                  <SourceRow key={`${source.url}-${index}`} source={source} />
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-3 flex items-center gap-2 text-[12px] font-medium text-slate-400">
              <BookIcon className="size-3.5 shrink-0" />
              Sin evidencia directa en Europe PMC para esta afirmación.
            </p>
          ))}
      </div>
    </div>
  );
}
