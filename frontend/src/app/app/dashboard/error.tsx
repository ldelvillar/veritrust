'use client';

import { useEffect } from 'react';
import ArrowRightIcon from '@/assets/ArrowRight';
import RefreshIcon from '@/assets/Refresh';
import Warning from '@/assets/Warning';
import Button from '@/components/Button';
import PageHeader from '@/components/PageHeader';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 px-4 py-8 md:px-6 lg:py-10">
      <PageHeader
        eyebrow="Panorama general"
        title="Dashboard"
        subtitle="Actividad, credibilidad y riesgos detectados en los últimos días."
      />

      <div className="relative overflow-hidden rounded-3xl border border-line bg-white px-10 py-20 text-center shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] max-md:px-6 max-md:py-15">
        {/* Dot grid background */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(color-mix(in srgb, var(--color-danger) 10%, transparent) 1.1px, transparent 1.1px)',
            backgroundSize: '22px 22px',
            maskImage:
              'radial-gradient(ellipse 60% 60% at 50% 38%, #000 0%, transparent 72%)',
            WebkitMaskImage:
              'radial-gradient(ellipse 60% 60% at 50% 38%, #000 0%, transparent 72%)',
          }}
        />

        <div className="relative z-1 flex flex-col items-center">
          {/* Icon */}
          <div className="mb-6.5 grid size-21 place-items-center rounded-3xl bg-[linear-gradient(155deg,var(--color-danger-g1),var(--color-danger-g2))] text-white shadow-[0_14px_30px_var(--tw-shadow-color)] shadow-danger-g2/30">
            <Warning className="size-9.5" />
          </div>

          <p className="mb-3.5 text-[11px] font-extrabold tracking-[0.14em] text-danger-ink uppercase">
            Error al cargar las métricas
          </p>
          <h2 className="mb-3 text-[clamp(22px,2.6vw,27px)] leading-tight font-bold tracking-[-0.025em] text-balance text-ink">
            No se pudo cargar tu dashboard
          </h2>
          <p className="mx-auto mb-7.5 max-w-120 text-[15.5px] leading-relaxed font-medium text-pretty text-muted">
            No hemos podido calcular tus métricas de actividad en este momento.
            Tus análisis siguen <b className="font-bold text-body">a salvo</b>;
            solo es un problema temporal de conexión con el servidor.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={reset} size="lg">
              <RefreshIcon className="size-4.5" aria-hidden />
              Reintentar
            </Button>
            <Button href="/app/historial" variant="soft" size="lg">
              <ArrowRightIcon className="size-4.5" aria-hidden />
              Ir al historial
            </Button>
          </div>

          <div className="relative mt-8 inline-flex max-w-full items-center gap-2.5 rounded-[10px] border border-line bg-surface-subtle px-3.5 py-2.5 font-mono text-xs text-faint">
            <span
              className="size-1.75 shrink-0 rounded-full bg-danger"
              aria-hidden
            />
            <span className="truncate">
              No se pudo contactar con el servicio de métricas
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
