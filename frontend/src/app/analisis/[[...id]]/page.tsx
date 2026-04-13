'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import {
  ERROR_CONNECTION,
  ERROR_INTERNAL,
  ERROR_MEMORY_LIMIT,
  ERROR_NO_MEDICAL_CLAIMS,
} from '@/messages';
import Result from '@/components/Result';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import { AnalysisDetail, SourceType } from '@/types';
import { CONFIG } from '@/config';

interface CreateAnalysisResponse {
  analysis_id?: string | null;
  label: string;
  confidence: string | number;
  explanation: string;
}

interface ResultData {
  label: string;
  confidence: string | number;
  explanation: string;
}

const isSourceType = (value: string | null): value is SourceType => {
  return value === 'text' || value === 'file' || value === 'url';
};

export default function AnalisisPage() {
  const params = useParams<{ id?: string[] | string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const analysisId = useMemo(() => {
    const raw = params?.id;
    if (Array.isArray(raw)) return raw[0] ?? null;
    return typeof raw === 'string' ? raw : null;
  }, [params]);

  const isDetailMode = Boolean(analysisId);

  const [result, setResult] = useState<ResultData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const lastRequestKey = useRef<string | null>(null);

  useEffect(() => {
    if (loading) {
      document.title = isDetailMode
        ? 'Cargando análisis | VeriTrust'
        : 'Analizando el texto | VeriTrust';
    } else {
      document.title = 'Resultado del análisis | VeriTrust';
    }

    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        isDetailMode
          ? 'Resultado de un análisis previamente generado, incluyendo puntuación y explicación médica.'
          : 'Resultados detallados del análisis del texto médico, incluyendo veredicto global, confianza y explicación.'
      );
  }, [loading, isDetailMode]);

  useEffect(() => {
    const requestKey = analysisId ?? 'create';
    if (lastRequestKey.current === requestKey) return;
    lastRequestKey.current = requestKey;

    setLoading(true);
    setError(null);
    setResult(null);

    const fetchData = async () => {
      if (analysisId) {
        try {
          const token = await getToken({ template: 'veritrust-api' });
          if (!token) {
            throw new Error('No se pudo obtener el token de autenticación.');
          }

          const response = await fetch(
            `${CONFIG.API_URL}/analisis/${analysisId}`,
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

        return;
      }

      const text = sessionStorage.getItem('analisis_text');
      const url = sessionStorage.getItem('analisis_url');
      const storedSourceType = sessionStorage.getItem('analisis_source_type');

      if (!text && !url) {
        router.replace('/');
        setLoading(false);
        return;
      }

      const sourceType: SourceType = isSourceType(storedSourceType)
        ? storedSourceType
        : url
          ? 'url'
          : 'text';

      const requestBody =
        sourceType === 'url' && url
          ? { url, source_type: 'url' as const }
          : {
              text: text ?? '',
              source_type: sourceType === 'file' ? 'file' : 'text',
            };

      sessionStorage.removeItem('analisis_text');
      sessionStorage.removeItem('analisis_url');
      sessionStorage.removeItem('analisis_source_type');

      try {
        const token = await getToken({ template: 'veritrust-api' });

        const response = await fetch(`${CONFIG.API_URL}/analisis`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            typeof errorData.detail === 'string'
              ? errorData.detail
              : Array.isArray(errorData.detail)
                ? errorData.detail[0].msg
                : `Status ${response.status}: Error al conectar con el servidor`;
          throw new Error(errorMessage);
        }

        const data = (await response.json()) as CreateAnalysisResponse;

        if (typeof data.analysis_id === 'string' && data.analysis_id) {
          router.replace(`/analisis/${data.analysis_id}`);
          return;
        }

        setResult({
          label: data.label,
          confidence: data.confidence,
          explanation: data.explanation,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        if (
          ![
            ERROR_CONNECTION,
            ERROR_MEMORY_LIMIT,
            ERROR_INTERNAL,
            ERROR_NO_MEDICAL_CLAIMS,
          ].includes(message)
        ) {
          setError(ERROR_INTERNAL);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(ERROR_INTERNAL);
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
          <p className="text-lg font-medium">
            {isDetailMode ? 'Cargando análisis...' : 'Analizando el texto...'}
          </p>
        </div>
      )}

      {error && (
        <div className="flex w-full max-w-2xl flex-col items-center gap-5 rounded-2xl border border-red-100 bg-white p-8 text-center shadow-2xl shadow-red-100/50 md:p-12">
          <div className="flex size-16 items-center justify-center rounded-full bg-red-100 text-red-500">
            <WarningIcon className="size-8" />
          </div>
          <div>
            <h2 className="mb-2 text-2xl font-bold text-gray-800">
              {isDetailMode
                ? 'No se pudo cargar el análisis'
                : 'Ups, ha ocurrido un error'}
            </h2>
            <p className="text-base text-gray-600">{error}</p>
          </div>
          <button
            onClick={() => router.replace(isDetailMode ? '/historial' : '/')}
            className="mt-3 rounded-xl bg-red-50 px-6 py-3 font-semibold text-red-600 transition-colors hover:bg-red-100 focus:ring-4 focus:ring-red-100 focus:outline-none"
          >
            {isDetailMode ? 'Volver al historial' : 'Volver al inicio'}
          </button>
        </div>
      )}

      {result && <Result result={result} />}
    </div>
  );
}
