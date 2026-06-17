'use client';

import { useEffect } from 'react';
import WarningIcon from '@/assets/Warning';

export default function CuentaError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-md rounded-2xl border border-line bg-white p-8 text-center shadow-sm">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-red-100 text-red-600">
          <WarningIcon className="size-6" aria-hidden />
        </span>
        <h1 className="mt-5 text-xl font-black tracking-tight text-ink">
          No se pudo cargar tu cuenta
        </h1>
        <p className="mt-2 text-sm font-medium text-muted">
          {error.message || 'Ha ocurrido un error inesperado.'}
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-[0_6px_16px_rgba(99,86,230,.28)] transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none"
        >
          Reintentar
        </button>
      </div>
    </section>
  );
}
