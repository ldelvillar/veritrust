'use client';

import { useEffect, useRef, useState } from 'react';
import Arrow from '@/assets/Arrow';
import CheckIcon from '@/assets/Check';
import CrossIcon from '@/assets/Cross';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import { container } from './container';

const highlights = [
  {
    b: 'Puntuación explicada',
    p: '41/100 · «Falso»: mezcla un hecho real con una conclusión sin respaldo.',
  },
  {
    b: 'Cada afirmación, por separado',
    p: 'Verdadero, falso o dudoso: cada afirmación recibe su propio veredicto en el mismo texto.',
  },
  {
    b: 'Fuentes para defenderlo',
    p: 'Las revisiones de Cochrane y las fichas del NIH respaldan el veredicto.',
  },
];

const claims = [
  {
    tone: 'ok' as const,
    text: 'La vitamina C es un nutriente esencial para el sistema inmunitario.',
    verdict: 'Verdadero',
  },
  {
    tone: 'bad' as const,
    text: 'Su consumo diario previene por completo el resfriado común.',
    verdict: 'Falso',
  },
  {
    tone: 'warn' as const,
    text: 'Refuerza el sistema inmunitario «sin ningún riesgo».',
    verdict: 'Dudoso',
  },
];

export default function SampleReport() {
  const gridRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const node = gridRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    observer.observe(node);

    return () => observer.disconnect();
  }, []);

  return (
    <section id="ejemplo" className="py-24 max-md:py-18">
      <div
        ref={gridRef}
        className={`${container} grid items-center gap-12 md:grid-cols-[0.9fr_1.1fr]`}
      >
        <div className={isVisible ? 'animate-slide-in-left' : 'opacity-0'}>
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Un informe real
          </span>
          <h2 className="my-4 text-[28px] font-bold tracking-[-0.02em] text-ink md:text-[36px]">
            Mira cómo VeriTrust desmonta un bulo
          </h2>
          <p className="mb-5 text-base leading-relaxed text-muted">
            Analizamos una afirmación habitual: «la vitamina C en dosis altas
            previene por completo el resfriado». Esto es lo que devuelve el
            sistema.
          </p>
          <div className="mt-6 flex flex-col gap-3.5">
            {highlights.map(li => (
              <div key={li.b} className="flex items-start gap-3.25">
                <span className="grid size-7.5 shrink-0 place-items-center rounded-[9px] bg-[#def4ea] text-[#0e8e5b]">
                  <CheckIcon className="size-4" />
                </span>
                <div>
                  <b className="font-semibold text-ink">{li.b}</b>
                  <p className="mt-0.75 text-[13.5px] text-muted">{li.p}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-7.5">
            <Button href="/ejemplo" size="lg">
              Ver análisis completo <Arrow className="size-4 rotate-270" />
            </Button>
          </div>
        </div>

        <div
          className={`overflow-hidden rounded-[22px] border border-line bg-white shadow-[0_24px_60px_rgba(60,50,140,0.18)] ${isVisible ? 'animate-slide-in-right' : 'opacity-0'}`}
        >
          <div className="flex items-center gap-1.75 border-b border-line bg-surface-subtle px-4.5 py-3.5">
            <i className="size-2.75 rounded-full bg-[#f0a8b4]" />
            <i className="size-2.75 rounded-full bg-[#f3d49a]" />
            <i className="size-2.75 rounded-full bg-[#a8e0c4]" />
            <span className="ml-3 rounded-[7px] bg-[#efedfc] px-3 py-1.25 text-xs font-bold text-primary">
              Informe de credibilidad
            </span>
          </div>
          <div className="p-6">
            <div className="mb-5 flex items-center gap-4.5">
              <div className="flex size-30 shrink-0 flex-col items-center justify-center rounded-[20px] bg-[linear-gradient(150deg,var(--color-verdict-fake-g1),var(--color-verdict-fake-g2))] text-white shadow-[0_12px_26px_rgba(210,60,93,0.3)]">
                <b className="text-[40px] leading-none font-bold">41</b>
                <small className="text-[11px] opacity-85">/ 100</small>
              </div>
              <div>
                <span className="text-[11px] font-extrabold tracking-[0.06em] text-verdict-fake-ink uppercase">
                  Falso
                </span>
                <h4 className="my-1.5 text-[21px] font-semibold text-ink">
                  Credibilidad baja
                </h4>
                <p className="text-[13px] leading-snug text-muted">
                  Parte de un hecho real pero exagera sus efectos y contradice
                  el consenso clínico.
                </p>
              </div>
            </div>
            <div className="mt-1.5 mb-3 text-xs font-extrabold tracking-[0.06em] text-faint uppercase">
              Afirmaciones detectadas
            </div>
            {claims.map((claim, idx) => (
              <div
                key={claim.text}
                className={`flex gap-3 py-3.25 ${idx > 0 ? 'border-t border-line' : ''}`}
              >
                <span
                  className={`mt-px grid size-6 shrink-0 place-items-center rounded-[7px] ${
                    claim.tone === 'ok'
                      ? 'bg-verdict-real-soft text-verdict-real-ink'
                      : claim.tone === 'bad'
                        ? 'bg-verdict-fake-soft text-verdict-fake-ink'
                        : 'bg-verdict-uncertain-soft text-verdict-uncertain-ink'
                  }`}
                >
                  {claim.tone === 'ok' ? (
                    <CheckIcon className="size-3.25 stroke-[2.6]" />
                  ) : claim.tone === 'bad' ? (
                    <CrossIcon className="size-3.25" />
                  ) : (
                    <WarningIcon className="size-3.25" />
                  )}
                </span>
                <div>
                  <div className="text-[13.5px] leading-snug font-semibold text-body">
                    {claim.text}
                  </div>
                  <span
                    className={`mt-1 inline-block text-[10.5px] font-extrabold tracking-[0.04em] uppercase ${
                      claim.tone === 'ok'
                        ? 'text-verdict-real-ink'
                        : claim.tone === 'bad'
                          ? 'text-verdict-fake-ink'
                          : 'text-verdict-uncertain-ink'
                    }`}
                  >
                    {claim.verdict}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
