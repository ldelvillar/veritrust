'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function AnalisisError({ error, reset }: ErrorProps) {
  const router = useRouter();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      <div className="flex w-full max-w-2xl flex-col items-center gap-5 rounded-2xl border border-danger/20 bg-white p-8 text-center shadow-2xl shadow-danger-soft/50 md:p-12">
        <div className="flex size-16 items-center justify-center rounded-full bg-danger-soft text-danger-ink">
          <WarningIcon className="size-8" />
        </div>
        <div>
          <h2 className="mb-2 text-2xl font-bold text-ink">
            No se pudo cargar el análisis
          </h2>
          <p className="text-base text-body">
            No hemos podido cargar este análisis. Puede ser un problema temporal
            de conexión; inténtalo de nuevo.
          </p>
        </div>
        <div className="mt-3 flex gap-3">
          <Button onClick={reset} size="lg">
            Reintentar
          </Button>
          <Button
            variant="soft"
            size="lg"
            onClick={() => router.replace('/app/historial')}
          >
            Volver al historial
          </Button>
        </div>
      </div>
    </div>
  );
}
