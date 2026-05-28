'use client';

import { useRouter } from 'next/navigation';
import WarningIcon from '@/assets/Warning';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function AnalisisError({ error, reset }: ErrorProps) {
  const router = useRouter();

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      <div className="flex w-full max-w-2xl flex-col items-center gap-5 rounded-2xl border border-red-100 bg-white p-8 text-center shadow-2xl shadow-red-100/50 md:p-12">
        <div className="flex size-16 items-center justify-center rounded-full bg-red-100 text-red-500">
          <WarningIcon className="size-8" />
        </div>
        <div>
          <h2 className="mb-2 text-2xl font-bold text-gray-800">
            No se pudo cargar el análisis
          </h2>
          <p className="text-base text-gray-600">
            {error.message || 'Error desconocido.'}
          </p>
        </div>
        <div className="mt-3 flex gap-3">
          <button
            onClick={reset}
            className="rounded-xl bg-red-50 px-6 py-3 font-semibold text-red-600 transition-colors hover:bg-red-100 focus:ring-4 focus:ring-red-100 focus:outline-none"
          >
            Reintentar
          </button>
          <button
            onClick={() => router.replace('/historial')}
            className="rounded-xl bg-slate-50 px-6 py-3 font-semibold text-slate-600 transition-colors hover:bg-slate-100 focus:ring-4 focus:ring-slate-100 focus:outline-none"
          >
            Volver al historial
          </button>
        </div>
      </div>
    </div>
  );
}
