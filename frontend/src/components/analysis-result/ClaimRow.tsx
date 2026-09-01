'use client';

import { useId, useState } from 'react';
import BookIcon from '@/assets/Book';
import Chevron from '@/assets/Chevron';
import SourceRow from './SourceRow';
import { getClaimStyle, STANCE_SUMMARY_META } from './format';
import { stanceForClaim, summarizeStances } from '@/lib/evidence';
import type { ClaimType, SourceType } from './types';

export default function ClaimRow({
  claim,
  claimIndex,
  sources,
  showEvidence,
}: {
  claim: ClaimType;
  claimIndex: number;
  sources: SourceType[];
  showEvidence: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const style = getClaimStyle(claim.verdict);
  const ClaimIcon = style.Icon;
  const confidencePct = Math.round(claim.confidence * 100);
  const sourceCount = sources.length;
  const stances = summarizeStances(claimIndex, sources);
  const stanceItems = STANCE_SUMMARY_META.map(meta => ({
    ...meta,
    count: stances[meta.key],
  })).filter(item => item.count > 0);

  return (
    <div className="flex gap-3 border-t border-line py-4 first:border-t-0 first:pt-0.5 print:break-inside-avoid">
      <div
        className={`grid size-7 shrink-0 place-items-center rounded-lg ${style.tile}`}
      >
        <ClaimIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug font-bold text-ink">{claim.text}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2.5">
          <span
            className={`rounded-md px-2 py-1 text-[10.5px] font-bold tracking-wide uppercase ${style.pill}`}
          >
            {style.text}
          </span>
          <span className="text-[11.5px] font-semibold text-faint">
            {confidencePct}% de confianza
          </span>
        </div>

        {showEvidence &&
          (sourceCount > 0 ? (
            <>
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                <button
                  type="button"
                  onClick={() => setOpen(value => !value)}
                  aria-expanded={open}
                  aria-controls={panelId}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none print:hidden"
                >
                  <BookIcon className="size-3.5" />
                  {open ? 'Ocultar' : 'Ver'} {sourceCount}{' '}
                  {sourceCount === 1 ? 'fuente' : 'fuentes'}
                  <Chevron
                    className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
                    aria-hidden
                  />
                </button>
                {stanceItems.length > 0 && (
                  <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] font-semibold text-faint">
                    {stanceItems.map(item => (
                      <span
                        key={item.key}
                        className="inline-flex items-center gap-1.5"
                      >
                        <span
                          className={`size-1.5 rounded-full ${item.dot}`}
                          aria-hidden
                        />
                        {item.count} {item.label}
                      </span>
                    ))}
                  </span>
                )}
              </div>
              {/* Siempre en el DOM y colapsado con clases, para que el PDF
                  (print:block) muestre toda la evidencia aunque esté oculta. */}
              <ul
                id={panelId}
                aria-label="Fuentes que respaldan esta afirmación"
                className={`mt-2.5 rounded-xl border border-line bg-surface-subtle/70 px-3.5 ${
                  open ? 'block' : 'hidden print:block'
                }`}
              >
                {sources.map((source, index) => (
                  <SourceRow
                    key={`${source.url}-${index}`}
                    source={source}
                    stance={stanceForClaim(source, claimIndex)}
                  />
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-3 flex items-center gap-2 text-[12px] font-medium text-faint">
              <BookIcon className="size-3.5 shrink-0" />
              Sin evidencia directa en nuestras fuentes para esta afirmación.
            </p>
          ))}
      </div>
    </div>
  );
}
