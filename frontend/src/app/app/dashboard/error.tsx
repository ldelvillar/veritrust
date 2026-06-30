'use client';

import Warning from '@/assets/Warning';
import Button from '@/components/Button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorProps) {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mx-auto w-full max-w-3xl rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-left">
        <div className="flex items-start gap-3">
          <Warning className="mt-0.5 size-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-bold text-red-700">
              No se pudo cargar el dashboard
            </p>
            <p className="mt-1 text-sm font-medium text-red-600">
              {error.message || 'Error desconocido.'}
            </p>
            <Button onClick={reset} className="mt-4">
              Reintentar
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
