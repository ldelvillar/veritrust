'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import Result from '@/components/Result';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import { AnalysisDetail } from '@/types';
import { CONFIG } from '@/config';

interface ResultData {
  label: string;
  confidence: string | number;
  explanation: string;
}

export default function AnalisisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const [result, setResult] = useState<ResultData | null>(null);
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
        const token = await getToken({ template: 'veritrust-api' });
        if (!token) {
          throw new Error('No se pudo obtener el token de autenticación.');
        }

        const response = await fetch(
          `${CONFIG.API_URL}/analysis/${analysisId}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            typeof errorData.detail === 'string'
              ? errorData.detail
              : Array.isArray(errorData.detail)
                ? errorData.detail[0].msg
                : `Status ${response.status}: Error al obtener el análisis`;
          throw new Error(errorMessage);
        }

        const data = (await response.json()) as { item?: AnalysisDetail };
        if (!data?.item) {
          throw new Error(
            'La respuesta del servidor no contiene un análisis válido.'
          );
        }

        setResult({
          label: data.item.label,
          confidence: data.item.confidence,
          explanation: data.item.explanation,
        });
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
