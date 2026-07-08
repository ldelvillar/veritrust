'use client';

import { useEffect } from 'react';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';

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
          Ha ocurrido un problema temporal al cargar tu cuenta. Inténtalo de
          nuevo.
        </p>
        <Button onClick={reset} className="mt-6">
          Reintentar
        </Button>
      </div>
    </section>
  );
}
