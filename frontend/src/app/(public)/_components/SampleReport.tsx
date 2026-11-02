'use client';

import { useEffect, useRef, useState } from 'react';
import Arrow from '@/assets/Arrow';
import CheckIcon from '@/assets/Check';
import CrossIcon from '@/assets/Cross';
import PublicButton from '@/components/PublicButton';
import { container } from './container';

const highlights = [
  {
    b: 'Puntuación explicada',
    p: '29/100 · «Falso»: las fuentes recuperadas contradicen las dos afirmaciones del texto.',
  },
  {
    b: 'Cada afirmación, por separado',
    p: 'Verdadero, falso o dudoso: cada afirmación recibe su propio veredicto en el mismo texto.',
  },
  {
    b: 'Fuentes para defenderlo',
    p: 'Cuatro artículos científicos, cada uno enlazado a la afirmación que evalúa y con su postura.',
  },
];

// The two claims of the real Analysis /ejemplo shows.
const claims = [
  'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
  'El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo.',
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
          <span className="text-sm font-extrabold tracking-[0.12em] text-primary uppercase">
            Un informe real
          </span>
          <h2 className="my-4 font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md">
            Mira cómo VeriTrust desmonta un bulo
          </h2>
          <p className="mb-5 text-base leading-relaxed text-muted">
            Analizamos un bulo habitual: «la vitamina C en dosis altas previene
            por completo el resfriado y refuerza el sistema inmunitario sin
            ningún riesgo». Esto es lo que devolvió el sistema.
          </p>
          <div className="mt-6 flex flex-col gap-3.5">
            {highlights.map(li => (
              <div key={li.b} className="flex items-start gap-3.25">
                <span className="grid size-7.5 shrink-0 place-items-center rounded-lg bg-verdict-real-soft text-verdict-real-ink">
                  <CheckIcon className="size-4" />
                </span>
                <div>
                  <b className="font-semibold text-ink">{li.b}</b>
                  <p className="mt-0.75 text-sm text-muted">{li.p}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-7.5">
            <PublicButton href="/ejemplo" size="lg">
              Ver análisis completo <Arrow className="size-4 rotate-270" />
            </PublicButton>
          </div>
        </div>

        <div
          className={`overflow-hidden rounded-2xl border border-line bg-white shadow-[0_24px_60px_rgba(18,33,31,0.16)] ${isVisible ? 'animate-slide-in-right' : 'opacity-0'}`}
        >
          <div className="flex items-center gap-1.75 border-b border-line bg-surface-subtle px-4.5 py-3.5">
            <i className="size-2.75 rounded-full bg-verdict-fake-soft" />
            <i className="size-2.75 rounded-full bg-verdict-uncertain-soft" />
            <i className="size-2.75 rounded-full bg-verdict-real-soft" />
            <span className="ml-3 rounded-lg bg-primary-soft px-3 py-1.25 text-xs font-bold text-primary">
              Informe de credibilidad
            </span>
          </div>
          <div className="p-6">
            <div className="mb-5 flex items-center gap-4.5">
              <div className="flex size-30 shrink-0 flex-col items-center justify-center rounded-2xl bg-[linear-gradient(150deg,var(--color-verdict-fake-g1),var(--color-verdict-fake-g2))] text-white shadow-[0_12px_26px_rgba(210,60,93,0.3)]">
                <b className="text-4xl leading-none font-bold">29</b>
                <small className="text-2xs opacity-85">/ 100</small>
              </div>
              <div>
                <span className="text-2xs font-extrabold tracking-[0.06em] text-verdict-fake-ink uppercase">
                  Falso
                </span>
                <h4 className="my-1.5 text-2xl font-semibold text-ink">
                  Credibilidad baja
                </h4>
                <p className="text-sm leading-snug text-muted">
                  Las fuentes recuperadas contradicen las dos afirmaciones.
                </p>
              </div>
            </div>
            <div className="mt-1.5 mb-3 text-xs font-extrabold tracking-[0.06em] text-faint uppercase">
              Afirmaciones detectadas
            </div>
            {claims.map((claim, idx) => (
              <div
                key={claim}
                className={`flex gap-3 py-3.25 ${idx > 0 ? 'border-t border-line' : ''}`}
              >
                <span className="mt-px grid size-6 shrink-0 place-items-center rounded-lg bg-verdict-fake-soft text-verdict-fake-ink">
                  <CrossIcon className="size-3.25" />
                </span>
                <div>
                  <div className="text-sm leading-snug font-semibold text-body">
                    {claim}
                  </div>
                  <span className="mt-1 inline-block text-2xs font-extrabold tracking-[0.04em] text-verdict-fake-ink uppercase">
                    Falso
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
