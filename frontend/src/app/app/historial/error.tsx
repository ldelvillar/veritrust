'use client';

import Link from 'next/link';

import ArrowRightIcon from '@/assets/ArrowRight';
import RefreshIcon from '@/assets/Refresh';
import Warning from '@/assets/Warning';
import PageHeader from '@/components/PageHeader';

import HistoryStatePanel from './_components/HistoryStatePanel';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

const PRIMARY_BTN =
  'inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-[15px] font-bold text-white shadow-[0_6px_16px_rgba(99,86,230,.28)] transition hover:bg-accent focus:ring-4 focus:ring-primary/20 focus:outline-none';

const SOFT_BTN =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-line-strong bg-white px-6 py-3.5 text-[15px] font-bold text-body transition hover:border-primary hover:text-primary focus:ring-4 focus:ring-primary/15 focus:outline-none';

export default function HistorialError({ error, reset }: ErrorProps) {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6">
        <PageHeader
          title="Análisis anteriores"
          subtitle="Revisa, filtra y gestiona tus informes de credibilidad previos."
        />
      </div>

      <HistoryStatePanel
        variant="red"
        icon={<Warning className="size-9.5" />}
        eyebrow="Error de conexión"
        title="No se pudo cargar tu historial"
        lead={
          <>
            No hemos podido recuperar tus informes guardados en este momento.
            Tus análisis siguen <b className="font-bold text-body">a salvo</b>;
            solo es un problema temporal de conexión con el servidor.
          </>
        }
        actions={
          <>
            <button type="button" onClick={reset} className={PRIMARY_BTN}>
              <RefreshIcon className="size-4.5" aria-hidden />
              Reintentar
            </button>
            <Link href="/app/analisis" className={SOFT_BTN}>
              <ArrowRightIcon className="size-4.5" aria-hidden />
              Ir a nuevo análisis
            </Link>
          </>
        }
        footer={
          <div className="relative mt-8 inline-flex max-w-full items-center gap-2.5 rounded-[10px] border border-line bg-surface-subtle px-3.5 py-2.5 font-mono text-xs text-faint">
            <span
              className="size-1.75 shrink-0 rounded-full bg-[#e0556b]"
              aria-hidden
            />
            <span className="truncate">
              {error.message ||
                'No se pudo contactar con el servicio de historial'}
            </span>
          </div>
        }
      />
    </section>
  );
}
