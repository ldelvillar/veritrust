'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import Result from '@/components/Result';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import type { paths } from '@/types/api';
import { fetchJsonWithAuth } from '@/lib/apiClient';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

export default function AnalisisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const [result, setResult] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const lastRequestKey = useRef<string | null>(null);

  const analysisId = params?.id ?? null;

  useEffect(() => {
    document.title = 'Resultado del análisis | VeriTrust';

    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Resultado del análisis, incluyendo veredicto global, confianza y explicación médica.'
      );
  }, [loading]);

  useEffect(() => {
    const requestKey = analysisId ?? 'create';
    if (lastRequestKey.current === requestKey) return;
    lastRequestKey.current = requestKey;

    setLoading(true);
    setError(null);
    setResult(null);

    const fetchData = async () => {
      if (!analysisId) {
        router.replace('/');
        return;
      }

      try {
        const data = await fetchJsonWithAuth<AnalysisDetail>(
          getToken,
          `/analysis/${analysisId}`,
          {
            method: 'GET',
            errorContextMessage: 'Error al obtener el análisis',
          }
        );
        if (!data) {
          throw new Error(
            'La respuesta del servidor no contiene un análisis válido.'
          );
        }

        setResult(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Ocurrió un error inesperado al cargar el análisis.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [analysisId, getToken, router]);

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
