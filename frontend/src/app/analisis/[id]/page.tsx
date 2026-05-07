'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Result from '@/components/Result';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import type { paths } from '@/types/api';
import { useApiQuery } from '@/hooks/useApiQuery';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

export default function AnalisisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const analysisId = params?.id ?? null;

  useEffect(() => {
    if (!analysisId) router.replace('/');
  }, [analysisId, router]);

  useEffect(() => {
    document.title = 'Resultado del análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Resultado del análisis, incluyendo veredicto global, confianza y explicación médica.'
      );
  }, []);

  const path = analysisId ? `/analysis/${analysisId}` : null;
  const {
    data: result,
    isLoading: loading,
    error,
  } = useApiQuery<AnalysisDetail>(path);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      {loading && (
        <div className="flex flex-col items-center gap-4 text-gray-500">
          <Spinner className="size-10 animate-spin text-primary" />
          <p className="text-lg font-medium">Cargando análisis...</p>
        </div>
      )}

      {error && (
        <div className="flex w-full max-w-2xl flex-col items-center gap-5 rounded-2xl border border-red-100 bg-white p-8 text-center shadow-2xl shadow-red-100/50 md:p-12">
          <div className="flex size-16 items-center justify-center rounded-full bg-red-100 text-red-500">
            <WarningIcon className="size-8" />
          </div>
          <div>
            <h2 className="mb-2 text-2xl font-bold text-gray-800">
              No se pudo cargar el análisis
            </h2>
            <p className="text-base text-gray-600">{error}</p>
          </div>
          <button
            onClick={() => router.replace('/historial')}
            className="mt-3 rounded-xl bg-red-50 px-6 py-3 font-semibold text-red-600 transition-colors hover:bg-red-100 focus:ring-4 focus:ring-red-100 focus:outline-none"
          >
            Volver al historial
          </button>
        </div>
      )}

      {result && <Result result={result} />}
    </div>
  );
}
